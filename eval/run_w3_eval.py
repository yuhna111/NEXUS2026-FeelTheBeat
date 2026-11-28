"""Week 3 evaluation runner (TV3): score TV2's C0–C4 outputs with bootstrap CI and McNemar tests.

Scores all Week 3 benchmark subsets (`pilot_80_v0.3`, `pilot_30_vinh`, `tv1_v0.3`, `tv3_v0.3`,
and combined `benchmark_v0.3` 308 questions) for both `gemini-flash` and `qwen-7b` across C0–C4.

Reads prediction JSONLs from `--outputs-dir` (default: `outputs`), or optionally from a git ref
via `--git-ref <ref>`.

Outputs CSV summaries, McNemar + Holm-Bonferroni tables, Qwen 3-run stability check, and a
draft markdown report for the 05/12 midterm milestone under `--out-dir` (default: `results/w3_eval`).

Usage:
    python -m eval.run_w3_eval
    python -m eval.run_w3_eval --outputs-dir outputs
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from eval.metrics import (
    DEFAULT_ENTITY_MAPS,
    LABELS,
    answer_match,
    auto_label,
    bootstrap_ci,
    evaluate,
    holm_bonferroni,
    load_predictions,
    load_vocab,
    mcnemar_exact,
    paired_bootstrap,
    ratio,
    _to_clause_id,
)
from eval.qa_schema import recall_gold_ids

ROOT = Path(__file__).resolve().parents[1]
N_BOOT = 1000
SEED = 0


def _load_bench(path: Path, prefix: str | None = None) -> dict[str, dict[str, Any]]:
    recs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["id"]: r for r in recs if not prefix or r["id"].startswith(prefix)}


def _extract_git_outputs(git_ref: str, dest: Path) -> Path:
    subpaths = ["outputs/pilot_80_v0.3", "outputs/tv1_v0.3", "outputs/tv3_v0.3"]
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", git_ref, *subpaths],
        text=True,
        cwd=ROOT,
    ).splitlines()
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(["git", "show", f"{git_ref}:{rel}"], cwd=ROOT))
    return dest / "outputs"


def _load_preds_many(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        if p.exists():
            out.extend(load_predictions(p))
    return out


STALE_OUTPUTS: set[tuple[str, str, str]] = set()
# Câu đổi nghĩa sau khi đã chạy (TV1 sửa 28/11/2026): đầu ra cũ trả lời câu khác, bỏ cho tới khi TV2 chạy lại.
# Các câu chỉ sửa câu chữ (A-0084, A-0101, B-0029, B-0039...) giữ nguyên đầu ra cũ.
OUTDATED_QIDS = {"C-0012", "F-0002"}


def _drop_outdated(preds: list[dict[str, Any]], bench: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Bỏ đầu ra sinh cho câu hỏi đã sửa sau khi chạy (prompt không chứa câu hỏi hiện tại).

    Ví dụ F-0002, C-0012 đổi câu hỏi ngày 28/11/2026 sau kiểm chéo của TV1: đầu ra cũ trả lời câu khác,
    nên không chấm cho tới khi TV2 chạy lại.
    """
    keep = []
    for p in preds:
        q = bench.get(p["question_id"])
        if p["question_id"] in OUTDATED_QIDS and q is not None and p.get("prompt") and q["question"] not in p["prompt"]:
            STALE_OUTPUTS.add((p["question_id"], p.get("model_id", "?"), p.get("config", "?")))
            continue
        keep.append(p)
    return keep


def _recall_with_ci(
    preds: list[dict[str, Any]], bench: dict[str, dict[str, Any]], k: int, n_boot: int, seed: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    hits: list[bool] = []
    rrs: list[float] = []
    for p in preds:
        qid = p["question_id"]
        if qid not in bench or p.get("config") in ("C0", "C5"):
            continue
        gold = recall_gold_ids(bench[qid])
        if not gold:
            continue
        ranked = [_to_clause_id(c) for c in p.get("context_ids", [])]
        hits.append(bool(gold & set(ranked[:k])))
        rr = 0.0
        for rank, cid in enumerate(ranked[:k], start=1):
            if cid in gold:
                rr = 1.0 / rank
                break
        rrs.append(rr)
    rec = ratio(hits, n_boot=n_boot, seed=seed).as_dict()
    mrr_dict = {
        "value": sum(rrs) / len(rrs) if rrs else None,
        "n": len(rrs),
        "ci95": list(bootstrap_ci(rrs, n_boot=n_boot, seed=seed)) if rrs else None,
    }
    return rec, mrr_dict


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def _score_preds(
    preds: list[dict[str, Any]],
    base_preds: list[dict[str, Any]] | None,
    bench: dict[str, dict[str, Any]],
    vocab: set[str],
    dataset_name: str,
    model: str,
    config: str,
    run_name: str = "run1",
    k: int = 5,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rep = evaluate(
        preds,
        bench,
        baseline=base_preds if (base_preds and config != "C0") else None,
        k=k,
        vocab=vocab,
        n_boot=n_boot,
        seed=seed,
    )
    rec_ci, mrr_ci = _recall_with_ci(preds, bench, k=k, n_boot=n_boot, seed=seed)

    known = [p for p in preds if p["question_id"] in bench]
    all_stale_flags = [auto_label(p["output"], bench[p["question_id"]], vocab) == "STALE" for p in known]
    sr_lb = ratio(all_stale_flags, n_boot=n_boot, seed=seed).as_dict()

    kor_dict = rep.get("KOR", {"num": 0, "den": 0, "value": None, "ci95": None})
    if kor_dict.get("den"):
        kor_flags = [True] * kor_dict["num"] + [False] * (kor_dict["den"] - kor_dict["num"])
        kor_dict = ratio(kor_flags, n_boot=n_boot, seed=seed).as_dict()
    pber_dict = rep["PBER"]
    if pber_dict.get("den"):
        pber_flags = [True] * pber_dict["num"] + [False] * (pber_dict["den"] - pber_dict["num"])
        pber_dict = ratio(pber_flags, n_boot=n_boot, seed=seed).as_dict()

    lc = rep["label_counts"]
    row = {
        "dataset": dataset_name,
        "model": model,
        "config": config,
        "run": run_name,
        "n_scored": rep["n_scored"],
        "n_auto_labeled": rep["n_scored"] - len(rep["pending_judge"]),
        "n_needs_judge": len(rep["pending_judge"]),
        "n_correct": lc.get("CORRECT_CURRENT", 0),
        "n_stale": lc.get("STALE", 0),
        "n_blended": lc.get("BLENDED", 0),
        "n_other_error": lc.get("OTHER_ERROR", 0),
        "n_abstain": lc.get("ABSTAIN", 0),
        "SR_auto": rep["SR"]["value"],
        "SR_auto_num": rep["SR"]["num"],
        "SR_auto_den": rep["SR"]["den"],
        "SR_auto_ci_lo": rep["SR"]["ci95"][0] if rep["SR"]["ci95"] else None,
        "SR_auto_ci_hi": rep["SR"]["ci95"][1] if rep["SR"]["ci95"] else None,
        "SR_plus_auto": rep["SR_plus"]["value"],
        "SR_lower_bound_all": sr_lb["value"],
        "SR_lb_ci_lo": sr_lb["ci95"][0] if sr_lb["ci95"] else None,
        "SR_lb_ci_hi": sr_lb["ci95"][1] if sr_lb["ci95"] else None,
        "AbstainRate_auto": rep["AbstainRate"]["value"],
        "EM": rep["EM"]["value"],
        "EM_num": rep["EM"]["num"],
        "EM_den": rep["EM"]["den"],
        "EM_ci_lo": rep["EM"]["ci95"][0] if rep["EM"]["ci95"] else None,
        "EM_ci_hi": rep["EM"]["ci95"][1] if rep["EM"]["ci95"] else None,
        "F1_set": rep["F1_set"]["mean"],
        "F1_set_n": rep["F1_set"]["n"],
        "OverRejection": rep["OverRejection"]["value"],
        "OverRejection_den": rep["OverRejection"]["den"],
        "Recall_at_5": rec_ci["value"],
        "Recall_at_5_num": rec_ci["num"],
        "Recall_at_5_den": rec_ci["den"],
        "Recall_at_5_ci_lo": rec_ci["ci95"][0] if rec_ci["ci95"] else None,
        "Recall_at_5_ci_hi": rec_ci["ci95"][1] if rec_ci["ci95"] else None,
        "MRR_at_5": mrr_ci["value"],
        "MRR_at_5_ci_lo": mrr_ci["ci95"][0] if mrr_ci["ci95"] else None,
        "MRR_at_5_ci_hi": mrr_ci["ci95"][1] if mrr_ci["ci95"] else None,
        "KOR": kor_dict.get("value"),
        "KOR_num": kor_dict.get("num"),
        "KOR_den": kor_dict.get("den"),
        "KOR_ci_lo": kor_dict["ci95"][0] if kor_dict["ci95"] else None,
        "KOR_ci_hi": kor_dict["ci95"][1] if kor_dict["ci95"] else None,
        "PBER": pber_dict.get("value"),
        "PBER_num": pber_dict.get("num"),
        "PBER_den": pber_dict.get("den"),
        "PBER_ci_lo": pber_dict["ci95"][0] if pber_dict["ci95"] else None,
        "PBER_ci_hi": pber_dict["ci95"][1] if pber_dict["ci95"] else None,
    }
    return row, rep


def _paired_mcnemar_preds(
    dataset_name: str,
    model: str,
    cfg_a: str,
    preds_a: list[dict[str, Any]],
    cfg_b: str,
    preds_b: list[dict[str, Any]],
    bench: dict[str, dict[str, Any]],
    vocab: set[str],
    k: int = 5,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    pa = {p["question_id"]: p for p in preds_a if p["question_id"] in bench}
    pb = {p["question_id"]: p for p in preds_b if p["question_id"] in bench}
    shared = sorted(set(pa) & set(pb))
    out: list[dict[str, Any]] = []

    def add_test(metric: str, flags_a: list[bool], flags_b: list[bool]) -> None:
        n = len(flags_a)
        b = sum(x and not y for x, y in zip(flags_a, flags_b))
        c = sum((not x) and y for x, y in zip(flags_a, flags_b))
        p_mc = mcnemar_exact(b, c)
        pb_res = paired_bootstrap([float(y) for y in flags_b], [float(x) for x in flags_a], n_boot=n_boot, seed=seed)
        rate_a = sum(flags_a) / n if n else None
        rate_b = sum(flags_b) / n if n else None
        out.append({
            "dataset": dataset_name,
            "model": model,
            "comparison": f"{cfg_a}_vs_{cfg_b}",
            "metric": metric,
            "n_paired": n,
            "rate_a": rate_a,
            "rate_b": rate_b,
            "diff_b_minus_a": (rate_b - rate_a) if (rate_a is not None and rate_b is not None) else None,
            "diff_ci_lo": pb_res["ci_lo"] if pb_res else None,
            "diff_ci_hi": pb_res["ci_hi"] if pb_res else None,
            "discordant_a1_b0": b,
            "discordant_a0_b1": c,
            "p_mcnemar_exact": p_mc,
            "p_holm": None,
        })

    stale_all_a = [auto_label(pa[q]["output"], bench[q], vocab) == "STALE" for q in shared]
    stale_all_b = [auto_label(pb[q]["output"], bench[q], vocab) == "STALE" for q in shared]
    add_test("SR_lower_bound_all", stale_all_a, stale_all_b)

    la = {q: auto_label(pa[q]["output"], bench[q], vocab) for q in shared}
    lb = {q: auto_label(pb[q]["output"], bench[q], vocab) for q in shared}
    both_lab = [q for q in shared if la[q] in LABELS and lb[q] in LABELS]
    add_test(
        "SR_auto_paired",
        [la[q] == "STALE" for q in both_lab],
        [lb[q] == "STALE" for q in both_lab],
    )

    ma = {q: answer_match(pa[q]["output"], bench[q], vocab) for q in shared}
    mb = {q: answer_match(pb[q]["output"], bench[q], vocab) for q in shared}
    both_em = [q for q in shared if ma[q] is not None and mb[q] is not None]
    if both_em:
        add_test("EM_paired", [bool(ma[q]) for q in both_em], [bool(mb[q]) for q in both_em])

    if cfg_a not in ("C0", "C5") and cfg_b not in ("C0", "C5"):
        ret_a, ret_b = [], []
        for q in shared:
            g = recall_gold_ids(bench[q])
            if not g:
                continue
            ra = {_to_clause_id(cid) for cid in pa[q].get("context_ids", [])[:k]}
            rb = {_to_clause_id(cid) for cid in pb[q].get("context_ids", [])[:k]}
            ret_a.append(bool(g & ra))
            ret_b.append(bool(g & rb))
        if ret_a:
            add_test("Recall_at_5", ret_a, ret_b)

    return out


def _apply_holm(rows: list[dict[str, Any]]) -> None:
    families: dict[tuple[str, str], list[int]] = {}
    for idx, r in enumerate(rows):
        families.setdefault((r["dataset"], r["metric"]), []).append(idx)
    for idxs in families.values():
        pvals = [rows[i]["p_mcnemar_exact"] for i in idxs]
        adj = holm_bonferroni(pvals)
        for i, p_adj in zip(idxs, adj):
            rows[i]["p_holm"] = p_adj


def _qwen_stability(outputs_dir: Path, bench: dict[str, dict[str, Any]], vocab: set[str]) -> list[dict[str, Any]]:
    rows = []
    for cfg in ("C0", "C2", "C3", "C4"):
        p1 = {p["question_id"]: p["output"] for p in load_predictions(outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.jsonl")}
        p2 = {p["question_id"]: p["output"] for p in load_predictions(outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.run2.jsonl")}
        p3 = {p["question_id"]: p["output"] for p in load_predictions(outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.run3.jsonl")}
        qids = sorted(set(p1) & set(p2) & set(p3) & set(bench))
        l1 = [auto_label(p1[q], bench[q], vocab) for q in qids]
        l2 = [auto_label(p2[q], bench[q], vocab) for q in qids]
        l3 = [auto_label(p3[q], bench[q], vocab) for q in qids]
        rows.append({
            "config": cfg,
            "n": len(qids),
            "exact_match_run1_run2": sum(p1[q] == p2[q] for q in qids),
            "exact_match_run1_run3": sum(p1[q] == p3[q] for q in qids),
            "exact_match_all3": sum(p1[q] == p2[q] == p3[q] for q in qids),
            "auto_label_same_all3": sum(a == b == c for a, b, c in zip(l1, l2, l3)),
            "sr_lb_run1": sum(x == "STALE" for x in l1) / len(qids),
            "sr_lb_run2": sum(x == "STALE" for x in l2) / len(qids),
            "sr_lb_run3": sum(x == "STALE" for x in l3) / len(qids),
        })
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _write_markdown_report(
    out_path: Path,
    bench308_rows: list[dict[str, Any]],
    tv1_rows: list[dict[str, Any]],
    tv3_rows: list[dict[str, Any]],
    pilot_rows: list[dict[str, Any]],
    pilot30_rows: list[dict[str, Any]],
    mcnemar_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
    source_note: str,
) -> None:
    def fmt_ci(val: float | None, lo: float | None, hi: float | None, num: int | None = None, den: int | None = None) -> str:
        if val is None or (den is not None and den == 0):
            return "—"
        core = f"{val:.1%}"
        if num is not None and den is not None:
            core += f" ({num}/{den})"
        if lo is not None and hi is not None:
            core += f" [{lo:.1%}–{hi:.1%}]"
        return core

    def fmt_mrr(val: float | None, lo: float | None, hi: float | None) -> str:
        if val is None:
            return "—"
        return f"{val:.3f} [{lo:.3f}–{hi:.3f}]" if (lo is not None and hi is not None) else f"{val:.3f}"

    def table_from_summary(rows: list[dict[str, Any]]) -> list[str]:
        lines = [
            "| Mô hình | Cấu hình | Đã gắn nhãn luật (chờ judge) | SR (trên tập luật) [CI 95%] | SR cận dưới (toàn bộ) [CI 95%] | EM [CI 95%] | Abstain | Recall@5 [CI 95%] | MRR@5 [CI 95%] | KOR | PBER |",
            "|---|---|---:|---|---|---|---|---|---:|---|---|",
        ]
        for r in rows:
            abstain = f"{r['n_abstain']}/{r['n_scored']} ({r['n_abstain']/r['n_scored']:.1%})"
            lines.append(
                f"| {r['model']} | **{r['config']}** | {r['n_auto_labeled']}/{r['n_scored']} ({r['n_needs_judge']}) "
                f"| {fmt_ci(r['SR_auto'], r['SR_auto_ci_lo'], r['SR_auto_ci_hi'], r['SR_auto_num'], r['SR_auto_den'])} "
                f"| {fmt_ci(r['SR_lower_bound_all'], r['SR_lb_ci_lo'], r['SR_lb_ci_hi'], r['n_stale'], r['n_scored'])} "
                f"| {fmt_ci(r['EM'], r['EM_ci_lo'], r['EM_ci_hi'], r['EM_num'], r['EM_den'])} "
                f"| {abstain} "
                f"| {fmt_ci(r['Recall_at_5'], r['Recall_at_5_ci_lo'], r['Recall_at_5_ci_hi'], r['Recall_at_5_num'], r['Recall_at_5_den'])} "
                f"| {fmt_mrr(r['MRR_at_5'], r['MRR_at_5_ci_lo'], r['MRR_at_5_ci_hi'])} "
                f"| {fmt_ci(r['KOR'], r['KOR_ci_lo'], r['KOR_ci_hi'], r['KOR_num'], r['KOR_den'])} "
                f"| {fmt_ci(r['PBER'], r['PBER_ci_lo'], r['PBER_ci_hi'], r['PBER_num'], r['PBER_den'])} |"
            )
        return lines

    def find_row(rows: list[dict[str, Any]], model: str, cfg: str) -> dict[str, Any]:
        return next(r for r in rows if r["model"] == model and r["config"] == cfg)

    def find_mc(dataset: str, model: str, comp: str, metric: str) -> dict[str, Any]:
        return next(
            r for r in mcnemar_rows
            if r["dataset"] == dataset and r["model"] == model and r["comparison"] == comp and r["metric"] == metric
        )

    tv1_g_c0, tv1_g_c4 = find_row(tv1_rows, "gemini-flash", "C0"), find_row(tv1_rows, "gemini-flash", "C4")
    tv1_q_c0, tv1_q_c4 = find_row(tv1_rows, "qwen-7b", "C0"), find_row(tv1_rows, "qwen-7b", "C4")
    tv1_mc_r5 = find_mc("tv1_v0.3", "qwen-7b", "C2_vs_C3", "Recall_at_5")
    b308_g_c0, b308_g_c3, b308_g_c4 = (
        find_row(bench308_rows, "gemini-flash", "C0"),
        find_row(bench308_rows, "gemini-flash", "C3"),
        find_row(bench308_rows, "gemini-flash", "C4"),
    )
    b308_q_c0, b308_q_c3, b308_q_c4 = (
        find_row(bench308_rows, "qwen-7b", "C0"),
        find_row(bench308_rows, "qwen-7b", "C3"),
        find_row(bench308_rows, "qwen-7b", "C4"),
    )
    b308_mc_g_sr = find_mc("benchmark_v0.3", "gemini-flash", "C0_vs_C4", "SR_lower_bound_all")
    b308_mc_q_sr = find_mc("benchmark_v0.3", "qwen-7b", "C0_vs_C4", "SR_lower_bound_all")
    b308_mc_r5 = find_mc("benchmark_v0.3", "qwen-7b", "C2_vs_C3", "Recall_at_5")

    lines = [
        "# Bảng số liệu nháp Tuần 3 (cập nhật 28/11/2026) — Chấm điểm C0–C4 trên đủ 308 câu v0.3",
        "",
        f"- **Ngày cập nhật:** 28/11/2026 · **Nguồn đầu ra:** {source_note}",
        "- **Bộ chấm:** `eval/metrics.py` (`auto_label`, bootstrap 1.000 lần, seed = 0, kiểm định McNemar hai phía chính xác + hiệu chỉnh Holm–Bonferroni theo `eval/metrics_spec.md` §6).",
        "- **Điểm mới so với bản nháp 27/11:**",
        "  1. Chấm lại `tv1_v0.3.jsonl` (168 câu) sau khi TV1 bổ sung `obsolete_entities` cho 73 câu và sửa 15 câu (`verified = true`): ở C0, số câu bắt được `STALE` tăng gần gấp đôi (`37 → 71` ở Gemini, `37 → 69` ở Qwen).",
        "  2. Bổ sung đầy đủ **Gemini C2–C4 trên 168 câu `tv1_v0.3`** và **cả Gemini lẫn Qwen C0–C4 trên 60 câu `tv3_v0.3`** (nhóm C, D, F).",
        "  3. Bổ sung bảng tổng hợp toàn bộ **`benchmark_v0.3.jsonl` (308 câu)** cho cả hai mô hình.",
        "  4. Sau kiểm chéo của TV1 (28/11, `docs/tv1_review_tv3_v03.md`): 12 câu nhóm F chấm theo `yes_no` thay vì `premise_rejection` (bộ nhận diện cũ không nhận câu bác tin đồn \"Không đúng\", làm 12/12 đáp án vàng bị chấm `OTHER_ERROR`); sửa 5 câu C/F; bỏ alias tên cũ ở C-0013..C-0017 và \"63\" ở D-0001. Đầu ra cũ của C-0012 và F-0002 (đổi nghĩa câu hỏi) không được chấm cho tới khi TV2 chạy lại.",
        "- **Lưu ý phương pháp luận (quy tắc báo cáo):**",
        "  1. Trong 308 câu `benchmark_v0.3.jsonl`, 168 câu `tv1_v0.3` đã đặt `verified = true` (TV1 + TV3 kiểm chéo 28/11); 60 câu `tv3_v0.3` TV1 đã kiểm chéo 28/11: 55 câu `verified = true`, 5 câu TV1 sửa nội dung chờ TV3 xem lại và 80 câu `pilot_80_v0.3` vẫn giữ nhãn pilot (`verified = false`). Riêng 15 câu TV1 vừa sửa văn phong/địa danh trên `tv1_v0.3`, TV2 sẽ chạy lại ở đầu Tuần 4 (153/168 câu giữ nguyên nguyên văn).",
        "  2. Bộ chấm luật tự động (`auto_label`) chưa qua LLM-as-a-Judge nên chưa sinh nhãn `BLENDED` (`SR⁺ = SR`) và còn một tỷ lệ câu `NEEDS_JUDGE`. Do đó bảng luôn báo song song **SR trên tập con luật chấm được** và **SR cận dưới trên toàn bộ mẫu** (coi `NEEDS_JUDGE` là không lỗi thời, tránh sai lệch chọn mẫu).",
        "  3. Hiện có **2 mô hình** (`gemini-3.5-flash-lite` và `Qwen2.5-7B-Instruct-AWQ`, temperature 0); chưa có key OpenAI/Anthropic.",
        "",
        "---",
        "",
        "## 1. Tổng hợp toàn bộ `benchmark_v0.3` (n = 308; 287 câu có khoản vàng cho Recall@5)",
        "",
        *table_from_summary(bench308_rows),
        "",
        "---",
        "",
        "## 2. Bộ `tv1_v0.3` — Đã `verified = true` & đủ `obsolete_entities` (n = 168; 168/168 có khoản vàng)",
        "",
        *table_from_summary(tv1_rows),
        "",
        "---",
        "",
        "## 3. Bộ `tv3_v0.3` — Nhóm C, D, F (n = 60; 58/60 có khoản vàng; TV1 đã kiểm chéo, 55/60 `verified`)",
        "",
        *table_from_summary(tv3_rows),
        "",
        "---",
        "",
        "## 4. Bộ `pilot_80_v0.3` (n = 80; 61/80 có khoản vàng)",
        "",
        *table_from_summary(pilot_rows),
        "",
        "### 4.1. Tách riêng 30 câu pilot TV3 (`P-V-*`, chỉ báo tỷ lệ/số câu tham khảo theo `metrics_spec.md` §6)",
        "",
        *table_from_summary(pilot30_rows),
        "",
        "---",
        "",
        "## 5. Kiểm định McNemar chính xác (C0 vs RAG và C2 vs C3) + hiệu chỉnh Holm–Bonferroni",
        "",
        "| Tập dữ liệu | Mô hình | So sánh | Độ đo | n ghép cặp | Tỷ lệ A | Tỷ lệ B | Chênh lệch (B − A) [CI 95%] | A=1, B=0 | A=0, B=1 | p (McNemar) | p (Holm) |",
        "|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]

    for r in mcnemar_rows:
        diff_s = (
            f"{r['diff_b_minus_a']:+.1%} [{r['diff_ci_lo']:+.1%}, {r['diff_ci_hi']:+.1%}]"
            if r["diff_b_minus_a"] is not None and r["diff_ci_lo"] is not None
            else "—"
        )
        sig = "**" if (r["p_holm"] is not None and r["p_holm"] < 0.05) else ""
        lines.append(
            f"| {r['dataset']} | {r['model']} | {r['comparison']} | `{r['metric']}` | {r['n_paired']} "
            f"| {_pct(r['rate_a'])} | {_pct(r['rate_b'])} | {diff_s} "
            f"| {r['discordant_a1_b0']} | {r['discordant_a0_b1']} "
            f"| {r['p_mcnemar_exact']:.4g} | {sig}{r['p_holm']:.4g}{sig} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 6. Kiểm tra độ ổn định 3 lần chạy của Qwen 2.5 7B (`pilot_80_v0.3`, temperature = 0)",
        "",
        "| Cấu hình | n | Trùng văn bản lần 1–2 | Trùng văn bản lần 1–3 | Trùng cả 3 lần | Cùng nhãn tự động cả 3 lần | SR cận dưới (L1 / L2 / L3) |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in stability_rows:
        lines.append(
            f"| **{s['config']}** | {s['n']} | {s['exact_match_run1_run2']}/{s['n']} "
            f"| {s['exact_match_run1_run3']}/{s['n']} | {s['exact_match_all3']}/{s['n']} "
            f"| {s['auto_label_same_all3']}/{s['n']} "
            f"| {s['sr_lb_run1']:.1%} / {s['sr_lb_run2']:.1%} / {s['sr_lb_run3']:.1%} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 7. Nhận xét chính rút ra cho báo cáo tiến độ 05/12",
        "",
        f"1. **Cập nhật `obsolete_entities` trên `tv1_v0.3` (168 câu `verified = true`) làm lộ rõ mức lỗi thời thật ở C0:**",
        f"   - SR (trên tập luật) ở C0 tăng lên **{tv1_g_c0['SR_auto']:.1%} ({tv1_g_c0['SR_auto_num']}/{tv1_g_c0['SR_auto_den']})** ở Gemini và **{tv1_q_c0['SR_auto']:.1%} ({tv1_q_c0['SR_auto_num']}/{tv1_q_c0['SR_auto_den']})** ở Qwen 7B (SR cận dưới toàn bộ 168 câu tăng gần gấp đôi: từ 22,0% lên **{tv1_g_c0['SR_lower_bound_all']:.1%}** ở Gemini và **{tv1_q_c0['SR_lower_bound_all']:.1%}** ở Qwen).",
        f"   - Khi dùng RAG đầy đủ (`C4`), SR (trên tập luật) trên 168 câu `tv1_v0.3` rơi mạnh xuống còn **{tv1_g_c4['SR_auto']:.1%} ({tv1_g_c4['SR_auto_num']}/{tv1_g_c4['SR_auto_den']})** ở Gemini và **{tv1_q_c4['SR_auto']:.1%} ({tv1_q_c4['SR_auto_num']}/{tv1_q_c4['SR_auto_den']})** ở Qwen; `EM` tăng vọt từ **{tv1_g_c0['EM']:.1%} → {tv1_g_c4['EM']:.1%}** (Gemini) và **{tv1_q_c0['EM']:.1%} → {tv1_q_c4['EM']:.1%}** (Qwen).",
        f"2. **Trên toàn bộ `benchmark_v0.3` (n = 308), RAG giảm mạnh lỗi thời và tăng mạnh EM ở cả hai mô hình (RQ2):**",
        f"   - **Gemini 3.5 Flash-Lite:** SR cận dưới giảm từ **{b308_g_c0['SR_lower_bound_all']:.1%} ({b308_g_c0['n_stale']}/308)** ở C0 xuống **{b308_g_c4['SR_lower_bound_all']:.1%} ({b308_g_c4['n_stale']}/308)** ở C4 (McNemar p_Holm = {b308_mc_g_sr['p_holm']:.3g}); EM tăng từ **{b308_g_c0['EM']:.1%} → {b308_g_c4['EM']:.1%}**; PBER ở C4 chỉ **{b308_g_c4['PBER']:.1%} ({b308_g_c4['PBER_num']}/{b308_g_c4['PBER_den']})**.",
        f"   - **Qwen 2.5 7B:** SR cận dưới giảm từ **{b308_q_c0['SR_lower_bound_all']:.1%} ({b308_q_c0['n_stale']}/308)** ở C0 xuống **{b308_q_c4['SR_lower_bound_all']:.1%} ({b308_q_c4['n_stale']}/308)** ở C4 (McNemar p_Holm = {b308_mc_q_sr['p_holm']:.3g}); EM tăng từ **{b308_q_c0['EM']:.1%} → {b308_q_c4['EM']:.1%}**; PBER ở C4 chỉ **{b308_q_c4['PBER']:.1%} ({b308_q_c4['PBER_num']}/{b308_q_c4['PBER_den']})**.",
        f"3. **Hybrid + Reranker (`C3`) vượt trội Dense (`C2`) có ý nghĩa thống kê rất mạnh (RQ2):**",
        f"   - Trên `benchmark_v0.3` (287 câu có khoản vàng), Recall@5 tăng từ **{b308_mc_r5['rate_a']:.1%}** (C2) lên **{b308_mc_r5['rate_b']:.1%}** (C3, **{b308_mc_r5['diff_b_minus_a']:+.1%}**, {b308_mc_r5['discordant_a0_b1']} câu cải thiện vs {b308_mc_r5['discordant_a1_b0']} câu giảm, McNemar p_Holm = {b308_mc_r5['p_holm']:.3g}), chủ yếu nhờ mức cải thiện **+19,6 điểm %** trên 168 câu chi tiết cấp xã/huyện của `tv1_v0.3` (McNemar p_Holm = {tv1_mc_r5['p_holm']:.3g}).",
        f"4. **Hiệu ứng prompt thời gian (`C4`) và độ ổn định (temperature = 0):**",
        f"   - `C4` giữ nguyên tập ngữ cảnh của `C3` nhưng kéo `SR` về mức thấp nhất và nâng `EM` nhờ chủ động từ chối (`Abstain`) khi không có bằng chứng trong kho (chủ yếu rơi vào 19 câu ngoài kho của `pilot_80` và 2 câu tin đồn ngoài kho của `tv3_v0.3`).",
        f"   - Qwen 7B ở temperature = 0 trùng nhãn tự động 79–80/80 câu cả 3 lần chạy; đo phương sai thực tế cần chạy ở temperature = 0,7 trên tập con.",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Week 3 C0–C4 evaluation with CI and McNemar tests")
    ap.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs")
    ap.add_argument("--git-ref", type=str, default=None, help="Optional git ref to read outputs/ from")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results/w3_eval")
    ap.add_argument("--bootstrap", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    tmp_ctx = tempfile.TemporaryDirectory() if args.git_ref else None
    try:
        if args.git_ref:
            outputs_dir = _extract_git_outputs(args.git_ref, Path(tmp_ctx.name))
            source_note = f"nhánh `{args.git_ref}` (`outputs/pilot_80_v0.3/`, `outputs/tv1_v0.3/`, `outputs/tv3_v0.3/`)"
        else:
            outputs_dir = args.outputs_dir
            source_note = f"thư mục `outputs/` (`pilot_80_v0.3`, `tv1_v0.3`, `tv3_v0.3`)"

        pilot_bench = _load_bench(ROOT / "data/benchmark/pilot_80_v0.3.jsonl")
        pilot30_bench = _load_bench(ROOT / "data/benchmark/pilot_80_v0.3.jsonl", prefix="P-V-")
        tv1_bench = _load_bench(ROOT / "data/benchmark/tv1_v0.3.jsonl")
        tv3_bench = _load_bench(ROOT / "data/benchmark/tv3_v0.3.jsonl")
        bench308_path = ROOT / "data/benchmark/benchmark_v0.3.jsonl"
        bench308 = _load_bench(bench308_path) if bench308_path.exists() else {**pilot_bench, **tv1_bench, **tv3_bench}

        pilot_vocab = load_vocab(DEFAULT_ENTITY_MAPS, pilot_bench.values())
        tv1_vocab = load_vocab(DEFAULT_ENTITY_MAPS, tv1_bench.values())
        tv3_vocab = load_vocab(DEFAULT_ENTITY_MAPS, tv3_bench.values())
        all_vocab = load_vocab(DEFAULT_ENTITY_MAPS, bench308.values())

        pilot_rows, pilot30_rows, tv1_rows, tv3_rows, bench308_rows, mcnemar_rows = [], [], [], [], [], []

        def eval_dataset(
            ds_name: str,
            subdirs: list[str],
            bench: dict[str, dict[str, Any]],
            vocab: set[str],
            target_rows: list[dict[str, Any]],
            also_sub: tuple[str, dict[str, dict[str, Any]], list[dict[str, Any]]] | None = None,
            run_mcnemar: bool = True,
        ) -> None:
            for model in ("gemini-flash", "qwen-7b"):
                preds_by_cfg: dict[str, list[dict[str, Any]]] = {}
                for cfg in ("C0", "C2", "C3", "C4"):
                    paths = [outputs_dir / sd / cfg / f"{model}.jsonl" for sd in subdirs]
                    if all(p.exists() for p in paths):
                        preds_by_cfg[cfg] = _drop_outdated(_load_preds_many(paths), bench)
                base_preds = preds_by_cfg.get("C0")
                for cfg in ("C0", "C2", "C3", "C4"):
                    if cfg not in preds_by_cfg:
                        continue
                    row, _ = _score_preds(preds_by_cfg[cfg], base_preds, bench, vocab, ds_name, model, cfg, n_boot=args.bootstrap, seed=args.seed)
                    target_rows.append(row)
                    if also_sub is not None:
                        sub_name, sub_bench, sub_rows = also_sub
                        srow, _ = _score_preds(preds_by_cfg[cfg], base_preds, sub_bench, vocab, sub_name, model, cfg, n_boot=args.bootstrap, seed=args.seed)
                        sub_rows.append(srow)
                    if run_mcnemar and cfg != "C0" and base_preds is not None:
                        mcnemar_rows.extend(_paired_mcnemar_preds(ds_name, model, "C0", base_preds, cfg, preds_by_cfg[cfg], bench, vocab, n_boot=args.bootstrap, seed=args.seed))
                if run_mcnemar and "C2" in preds_by_cfg and "C3" in preds_by_cfg:
                    mcnemar_rows.extend(_paired_mcnemar_preds(ds_name, model, "C2", preds_by_cfg["C2"], "C3", preds_by_cfg["C3"], bench, vocab, n_boot=args.bootstrap, seed=args.seed))
                if run_mcnemar and "C3" in preds_by_cfg and "C4" in preds_by_cfg:
                    mcnemar_rows.extend(_paired_mcnemar_preds(ds_name, model, "C3", preds_by_cfg["C3"], "C4", preds_by_cfg["C4"], bench, vocab, n_boot=args.bootstrap, seed=args.seed))

        eval_dataset("pilot_80_v0.3", ["pilot_80_v0.3"], pilot_bench, pilot_vocab, pilot_rows, also_sub=("pilot_30_vinh", pilot30_bench, pilot30_rows))
        eval_dataset("tv1_v0.3", ["tv1_v0.3"], tv1_bench, tv1_vocab, tv1_rows)
        eval_dataset("tv3_v0.3", ["tv3_v0.3"], tv3_bench, tv3_vocab, tv3_rows)
        eval_dataset("benchmark_v0.3", ["pilot_80_v0.3", "tv1_v0.3", "tv3_v0.3"], bench308, all_vocab, bench308_rows)

        if STALE_OUTPUTS:
            qids = sorted({q for q, _, _ in STALE_OUTPUTS})
            print(f"Bỏ {len(STALE_OUTPUTS)} đầu ra của câu đã đổi nội dung, chờ chạy lại: {', '.join(qids)}")
        _apply_holm(mcnemar_rows)
        stability_rows = _qwen_stability(outputs_dir, pilot_bench, pilot_vocab)

        _write_csv(args.out_dir / "summary_benchmark_v03_308.csv", bench308_rows)
        _write_csv(args.out_dir / "summary_tv1_168.csv", tv1_rows)
        _write_csv(args.out_dir / "summary_tv3_60.csv", tv3_rows)
        _write_csv(args.out_dir / "summary_pilot_80.csv", pilot_rows + pilot30_rows)
        _write_csv(args.out_dir / "mcnemar_c0_vs_rag.csv", mcnemar_rows)
        _write_csv(args.out_dir / "qwen_3runs_stability.csv", stability_rows)
        _write_markdown_report(
            args.out_dir / "w3_eval_report_draft.md",
            bench308_rows,
            tv1_rows,
            tv3_rows,
            pilot_rows,
            pilot30_rows,
            mcnemar_rows,
            stability_rows,
            source_note,
        )
        print(f"Wrote updated Week 3 evaluation tables (308 questions) -> {args.out_dir}")
        return 0
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
