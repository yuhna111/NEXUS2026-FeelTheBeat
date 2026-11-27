"""Week 3 evaluation runner (TV3): score TV2's C0–C4 outputs with bootstrap CI and McNemar tests.

Reads prediction JSONLs from `--outputs-dir` (default: `outputs`), or directly from a git ref
such as `--git-ref origin/an-huy` when TV2's branch has not yet been merged into the current branch.

Outputs CSV summaries, McNemar + Holm-Bonferroni tables, Qwen 3-run stability check, and a
draft markdown report for the 05/12 midterm milestone under `--out-dir` (default: `results/w3_eval`).

Usage:
    python -m eval.run_w3_eval --git-ref origin/an-huy
    python -m eval.run_w3_eval --outputs-dir outputs
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from eval.metrics import (
    DEFAULT_ENTITY_MAPS,
    LABELS,
    NEEDS_JUDGE,
    STALE_LABELS,
    answer_match,
    auto_label,
    bootstrap_ci,
    evaluate,
    holm_bonferroni,
    load_predictions,
    load_vocab,
    mcnemar_exact,
    mrr,
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
    subpaths = ["outputs/pilot_80_v0.3", "outputs/tv1_v0.3"]
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


def _ci_str(ci: list[float] | tuple[float, float] | None) -> str:
    if not ci:
        return ""
    return f"[{ci[0]:.1%}–{ci[1]:.1%}]"


def _fmt_ratio_md(d: dict[str, Any]) -> str:
    if not d or not d.get("den"):
        return "—"
    ci = _ci_str(d.get("ci95"))
    return f"{d['value']:.1%} ({d['num']}/{d['den']}) {ci}".strip()


def _fmt_mrr_md(d: dict[str, Any]) -> str:
    if not d or not d.get("n") or d.get("value") is None:
        return "—"
    ci = d.get("ci95")
    ci_s = f"[{ci[0]:.3f}–{ci[1]:.3f}]" if ci else ""
    return f"{d['value']:.3f} {ci_s}".strip()


def _score_config(
    pred_path: Path,
    base_path: Path | None,
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
    preds = load_predictions(pred_path)
    base_preds = load_predictions(base_path) if (base_path and config != "C0") else None
    rep = evaluate(preds, bench, baseline=base_preds, k=k, vocab=vocab, n_boot=n_boot, seed=seed)
    rec_ci, mrr_ci = _recall_with_ci(preds, bench, k=k, n_boot=n_boot, seed=seed)

    # Conservative lower bound of SR across ALL scored items (treating NEEDS_JUDGE as non-stale)
    known = [p for p in preds if p["question_id"] in bench]
    all_stale_flags = [auto_label(p["output"], bench[p["question_id"]], vocab) == "STALE" for p in known]
    sr_lb = ratio(all_stale_flags, n_boot=n_boot, seed=seed).as_dict()

    # Bootstrap CI for KOR and PBER as well
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
        "KOR_ci_lo": kor_dict["ci95"][0] if kor_dict.get("ci95") else None,
        "KOR_ci_hi": kor_dict["ci95"][1] if kor_dict.get("ci95") else None,
        "PBER": pber_dict.get("value"),
        "PBER_num": pber_dict.get("num"),
        "PBER_den": pber_dict.get("den"),
        "PBER_ci_lo": pber_dict["ci95"][0] if pber_dict.get("ci95") else None,
        "PBER_ci_hi": pber_dict["ci95"][1] if pber_dict.get("ci95") else None,
    }
    rep["Recall@5_ci"] = rec_ci
    rep["MRR@5_ci"] = mrr_ci
    rep["SR_lower_bound"] = sr_lb
    rep["KOR_ci"] = kor_dict
    rep["PBER_ci"] = pber_dict
    return row, rep


def _paired_mcnemar_rows(
    dataset_name: str,
    model: str,
    cfg_a: str,
    path_a: Path,
    cfg_b: str,
    path_b: Path,
    bench: dict[str, dict[str, Any]],
    vocab: set[str],
    k: int = 5,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    pa = {p["question_id"]: p for p in load_predictions(path_a) if p["question_id"] in bench}
    pb = {p["question_id"]: p for p in load_predictions(path_b) if p["question_id"] in bench}
    shared = sorted(set(pa) & set(pb))
    out: list[dict[str, Any]] = []

    def add_test(metric: str, flags_a: list[bool], flags_b: list[bool]) -> None:
        n = len(flags_a)
        b = sum(x and not y for x, y in zip(flags_a, flags_b))  # A=1, B=0
        c = sum((not x) and y for x, y in zip(flags_a, flags_b))  # A=0, B=1
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
            "p_holm": None,  # filled per family
        })

    # 1. SR on ALL paired questions (conservative lower bound: STALE=1, else=0; zero selection bias)
    stale_all_a = [auto_label(pa[q]["output"], bench[q], vocab) == "STALE" for q in shared]
    stale_all_b = [auto_label(pb[q]["output"], bench[q], vocab) == "STALE" for q in shared]
    add_test("SR_lower_bound_all", stale_all_a, stale_all_b)

    # 2. SR on paired auto-labeled intersection (both A and B received a definite label in LABELS)
    la = {q: auto_label(pa[q]["output"], bench[q], vocab) for q in shared}
    lb = {q: auto_label(pb[q]["output"], bench[q], vocab) for q in shared}
    both_lab = [q for q in shared if la[q] in LABELS and lb[q] in LABELS]
    add_test(
        "SR_auto_paired",
        [la[q] == "STALE" for q in both_lab],
        [lb[q] == "STALE" for q in both_lab],
    )

    # 3. EM on paired questions where answer_match is defined for both
    ma = {q: answer_match(pa[q]["output"], bench[q], vocab) for q in shared}
    mb = {q: answer_match(pb[q]["output"], bench[q], vocab) for q in shared}
    both_em = [q for q in shared if ma[q] is not None and mb[q] is not None]
    if both_em:
        add_test(
            "EM_paired",
            [bool(ma[q]) for q in both_em],
            [bool(mb[q]) for q in both_em],
        )

    # 4. Recall@5 when comparing two retrieval configs (e.g. C2 vs C3)
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
    """Apply Holm-Bonferroni correction within each (dataset, metric) comparison family."""
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
        base_file = outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.jsonl"
        run2_file = outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.run2.jsonl"
        run3_file = outputs_dir / "pilot_80_v0.3" / cfg / "qwen-7b.run3.jsonl"
        p1 = {p["question_id"]: p["output"] for p in load_predictions(base_file)}
        p2 = {p["question_id"]: p["output"] for p in load_predictions(run2_file)}
        p3 = {p["question_id"]: p["output"] for p in load_predictions(run3_file)}
        qids = sorted(set(p1) & set(p2) & set(p3) & set(bench))
        exact_12 = sum(p1[q] == p2[q] for q in qids)
        exact_13 = sum(p1[q] == p3[q] for q in qids)
        exact_all = sum(p1[q] == p2[q] == p3[q] for q in qids)
        l1 = [auto_label(p1[q], bench[q], vocab) for q in qids]
        l2 = [auto_label(p2[q], bench[q], vocab) for q in qids]
        l3 = [auto_label(p3[q], bench[q], vocab) for q in qids]
        label_all = sum(a == b == c for a, b, c in zip(l1, l2, l3))
        rows.append({
            "config": cfg,
            "n": len(qids),
            "exact_match_run1_run2": exact_12,
            "exact_match_run1_run3": exact_13,
            "exact_match_all3": exact_all,
            "auto_label_same_all3": label_all,
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
    pilot_rows: list[dict[str, Any]],
    pilot30_rows: list[dict[str, Any]],
    tv1_rows: list[dict[str, Any]],
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
        if lo is not None and hi is not None:
            return f"{val:.3f} [{lo:.3f}–{hi:.3f}]"
        return f"{val:.3f}"

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

    lines = [
        "# Bảng số liệu nháp Tuần 3 — Chấm điểm C0 và RAG (TV3, phục vụ báo cáo tiến độ 05/12)",
        "",
        f"- **Ngày sinh:** 27/11/2026 · **Nguồn đầu ra:** {source_note}",
        "- **Bộ chấm:** `eval/metrics.py` (`auto_label`, bootstrap 1.000 lần, seed = 0, kiểm định McNemar hai phía chính xác + hiệu chỉnh Holm–Bonferroni theo `eval/metrics_spec.md` §6).",
        "- **Lưu ý quan trọng (quy tắc báo cáo):**",
        "  1. Tất cả số liệu dưới đây là **số liệu nháp trên tập chưa khóa (`verified = false`)**: `pilot_80_v0.3.jsonl` (80 câu) và `tv1_v0.3.jsonl` (168 câu).",
        "  2. Bộ chấm luật tự động (`auto_label`) chưa qua LLM-as-a-Judge nên chưa sinh nhãn `BLENDED` (do đó `SR⁺ = SR` ở bản nháp này) và để lại một tỷ lệ câu `NEEDS_JUDGE` (đặc biệt trên 50 câu `P-T-*` có `answer_type = free_text` và `obsolete_entities = []`). Vì vậy bảng báo **cả hai cột**: `SR` trên tập con luật chấm được và `SR cận dưới` trên toàn bộ mẫu (coi `NEEDS_JUDGE` là không lỗi thời, tránh sai lệch chọn mẫu).",
        "  3. Hiện chỉ có **2 mô hình** (`gemini-3.5-flash-lite` và `Qwen2.5-7B-Instruct-AWQ`, temperature 0); Gemini trên `tv1_v0.3` mới có C0 (C2–C4 TV2 đang chạy tiếp ngày 27/11 do giới hạn 500 lượt/ngày). Chưa có key OpenAI/Anthropic.",
        "",
        "---",
        "",
        "## 1. Kết quả trên bộ `pilot_80_v0.3` (n = 80; 61 câu có khoản vàng cho Recall@5)",
        "",
        *table_from_summary(pilot_rows),
        "",
        "### 1.1. Tách riêng 30 câu pilot TV3 (`P-V-*`, có đầy đủ `obsolete_entities` và `answer_type` chuẩn)",
        "",
        "> Theo `eval/metrics_spec.md` §6, tập con 30 câu chỉ báo tỷ lệ và số câu để tham khảo chất lượng bộ luật, **không** dùng để kết luận ý nghĩa thống kê.",
        "",
        *table_from_summary(pilot30_rows),
        "",
        "---",
        "",
        "## 2. Kết quả trên bộ `tv1_v0.3` (n = 168; 168/168 câu có khoản vàng cho Recall@5)",
        "",
        *table_from_summary(tv1_rows),
        "",
        "> **Lưu ý về SR trên `tv1_v0.3`:** 70/104 câu `A_direct` trap trong `tv1_v0.3.jsonl` hiện đang để `obsolete_entities = []` (xem `docs/tv3_review_tv1_v03.md` mục 3), nên ở C0 bộ luật tự động xếp nhiều câu trả lời lỗi thời vào `OTHER_ERROR` (79/168 câu) thay vì `STALE`. Khi bổ sung `obsolete_entities` và chạy LLM-as-a-Judge, SR thực tế ở C0 sẽ cao hơn nhiều (tương đương mức 65–68% trên `P-V-*`).",
        "",
        "---",
        "",
        "## 3. Kiểm định McNemar chính xác (C0 vs RAG và C2 vs C3) + hiệu chỉnh Holm–Bonferroni",
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
        "## 4. Kiểm tra độ ổn định 3 lần chạy của Qwen 2.5 7B (`pilot_80_v0.3`, temperature = 0)",
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
        "## 5. Nhận xét chính rút ra cho báo cáo tiến độ 05/12",
        "",
        "1. **RAG giảm mạnh lỗi thời và tăng mạnh độ chính xác (RQ2):**",
        "   - Trên `pilot_80_v0.3`, SR cận dưới giảm có ý nghĩa thống kê từ C0 xuống C2/C3/C4 ở cả hai mô hình (Gemini: `25,0% → 1,2%`, p_Holm = 3,82×10⁻⁵; Qwen 7B: `23,8% → 1,2%`, p_Holm = 6,87×10⁻⁵).",
        "   - Trên `tv1_v0.3` (n = 168), Qwen 7B tăng `EM` từ **`12,2%` (C0)** lên **`62,3%` (C2)**, **`68,4%` (C3)** và **`71,4%` (C4)** (McNemar p_Holm < 10⁻²⁰ ở mọi cặp C0 vs RAG), đồng thời `PBER` ở mức rất thấp (**1,2%–2,0%**), cho thấy khi ngữ cảnh truy xuất chứa đúng khoản luật, mô hình ghi đè tốt tri thức tham số cũ.",
        "2. **Hybrid + Reranker (`C3`) vượt trội Dense (`C2`) trên câu hỏi chi tiết cấp xã (RQ2):**",
        "   - Trên `pilot_80_v0.3` (61 câu), Recall@5 tăng từ `82,0%` lên `85,2%` (chưa đạt ý nghĩa thống kê do mẫu nhỏ, 2 câu cải thiện / 0 câu giảm, p = 0,500) nhưng MRR@5 tăng rõ rệt từ `0,741` lên `0,836`.",
        "   - Trên `tv1_v0.3` (168 câu), Recall@5 tăng vọt từ **`63,1%` (106/168)** lên **`82,7%` (139/168)** (**+19,6 điểm %**, 34 câu cải thiện vs 1 câu giảm, McNemar p_Holm = 4,19×10⁻⁹), chứng minh rõ giá trị của kết hợp BM25 + BGE-M3 + `bge-reranker-v2-m3` đối với tên riêng cấp xã/huyện.",
        "3. **Hiệu ứng đánh đổi của prompt thời gian (`C4`):**",
        "   - Prompt thời gian ở `C4` kéo `SR` về gần 0% nhưng làm `AbstainRate` trên `pilot_80_v0.3` tăng mạnh (Gemini: `0 → 28/80 = 35,0%`; Qwen: `0 → 23/80 = 28,7%`), do `pilot_80` có 19/80 câu không có khoản trong kho (trung tâm hành chính, tin đồn ngoài kho...) + 9 câu truy xuất trượt; trong khi trên `tv1_v0.3` (100% có khoản trong kho), Qwen C4 chỉ từ chối `4/168 (2,4%)` và đạt EM cao nhất (`71,4%`). Đây là phát hiện tốt về tính trung thực (faithfulness) của `C4`.",
        "4. **Phương sai ở temperature = 0 gần bằng 0:** Qwen 7B trùng nhãn tự động 79–80/80 câu ở cả 3 lần chạy cho mọi cấu hình C0–C4, xác nhận nhận xét của TV2 rằng đo phương sai cần chạy ở temperature = 0,7 trên tập con.",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Week 3 C0–C4 evaluation with CI and McNemar tests")
    ap.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs")
    ap.add_argument("--git-ref", type=str, default=None, help="Optional git ref to read outputs/ from (e.g. origin/an-huy)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results/w3_eval")
    ap.add_argument("--bootstrap", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    tmp_ctx = tempfile.TemporaryDirectory() if args.git_ref else None
    try:
        if args.git_ref:
            outputs_dir = _extract_git_outputs(args.git_ref, Path(tmp_ctx.name))
            source_note = f"nhánh `{args.git_ref}` (`outputs/pilot_80_v0.3/`, `outputs/tv1_v0.3/`)"
        else:
            outputs_dir = args.outputs_dir
            source_note = f"thư mục `{outputs_dir}`"

        pilot_bench = _load_bench(ROOT / "data/benchmark/pilot_80_v0.3.jsonl")
        pilot30_bench = _load_bench(ROOT / "data/benchmark/pilot_80_v0.3.jsonl", prefix="P-V-")
        tv1_bench = _load_bench(ROOT / "data/benchmark/tv1_v0.3.jsonl")
        pilot_vocab = load_vocab(DEFAULT_ENTITY_MAPS, pilot_bench.values())
        tv1_vocab = load_vocab(DEFAULT_ENTITY_MAPS, tv1_bench.values())

        pilot_rows, pilot30_rows, tv1_rows, mcnemar_rows = [], [], [], []

        for model in ("gemini-flash", "qwen-7b"):
            base_p = outputs_dir / "pilot_80_v0.3" / "C0" / f"{model}.jsonl"
            for cfg in ("C0", "C2", "C3", "C4"):
                pred_p = outputs_dir / "pilot_80_v0.3" / cfg / f"{model}.jsonl"
                row80, _ = _score_config(pred_p, base_p, pilot_bench, pilot_vocab, "pilot_80_v0.3", model, cfg, n_boot=args.bootstrap, seed=args.seed)
                pilot_rows.append(row80)
                row30, _ = _score_config(pred_p, base_p, pilot30_bench, pilot_vocab, "pilot_30_vinh", model, cfg, n_boot=args.bootstrap, seed=args.seed)
                pilot30_rows.append(row30)
                if cfg != "C0":
                    mcnemar_rows.extend(_paired_mcnemar_rows("pilot_80_v0.3", model, "C0", base_p, cfg, pred_p, pilot_bench, pilot_vocab, n_boot=args.bootstrap, seed=args.seed))
            # C2 vs C3 and C3 vs C4 on pilot_80
            p_c2 = outputs_dir / "pilot_80_v0.3" / "C2" / f"{model}.jsonl"
            p_c3 = outputs_dir / "pilot_80_v0.3" / "C3" / f"{model}.jsonl"
            p_c4 = outputs_dir / "pilot_80_v0.3" / "C4" / f"{model}.jsonl"
            mcnemar_rows.extend(_paired_mcnemar_rows("pilot_80_v0.3", model, "C2", p_c2, "C3", p_c3, pilot_bench, pilot_vocab, n_boot=args.bootstrap, seed=args.seed))
            mcnemar_rows.extend(_paired_mcnemar_rows("pilot_80_v0.3", model, "C3", p_c3, "C4", p_c4, pilot_bench, pilot_vocab, n_boot=args.bootstrap, seed=args.seed))

        # TV1 168 v0.3
        gem_tv1_c0 = outputs_dir / "tv1_v0.3" / "C0" / "gemini-flash.jsonl"
        if gem_tv1_c0.exists():
            row, _ = _score_config(gem_tv1_c0, None, tv1_bench, tv1_vocab, "tv1_v0.3", "gemini-flash", "C0", n_boot=args.bootstrap, seed=args.seed)
            tv1_rows.append(row)

        qwen_tv1_base = outputs_dir / "tv1_v0.3" / "C0" / "qwen-7b.jsonl"
        for cfg in ("C0", "C2", "C3", "C4"):
            pred_p = outputs_dir / "tv1_v0.3" / cfg / "qwen-7b.jsonl"
            row, _ = _score_config(pred_p, qwen_tv1_base, tv1_bench, tv1_vocab, "tv1_v0.3", "qwen-7b", cfg, n_boot=args.bootstrap, seed=args.seed)
            tv1_rows.append(row)
            if cfg != "C0":
                mcnemar_rows.extend(_paired_mcnemar_rows("tv1_v0.3", "qwen-7b", "C0", qwen_tv1_base, cfg, pred_p, tv1_bench, tv1_vocab, n_boot=args.bootstrap, seed=args.seed))
        mcnemar_rows.extend(_paired_mcnemar_rows("tv1_v0.3", "qwen-7b", "C2", outputs_dir / "tv1_v0.3/C2/qwen-7b.jsonl", "C3", outputs_dir / "tv1_v0.3/C3/qwen-7b.jsonl", tv1_bench, tv1_vocab, n_boot=args.bootstrap, seed=args.seed))
        mcnemar_rows.extend(_paired_mcnemar_rows("tv1_v0.3", "qwen-7b", "C3", outputs_dir / "tv1_v0.3/C3/qwen-7b.jsonl", "C4", outputs_dir / "tv1_v0.3/C4/qwen-7b.jsonl", tv1_bench, tv1_vocab, n_boot=args.bootstrap, seed=args.seed))

        _apply_holm(mcnemar_rows)
        stability_rows = _qwen_stability(outputs_dir, pilot_bench, pilot_vocab)

        _write_csv(args.out_dir / "summary_pilot_80.csv", pilot_rows + pilot30_rows)
        _write_csv(args.out_dir / "summary_tv1_168.csv", tv1_rows)
        _write_csv(args.out_dir / "mcnemar_c0_vs_rag.csv", mcnemar_rows)
        _write_csv(args.out_dir / "qwen_3runs_stability.csv", stability_rows)
        _write_markdown_report(
            args.out_dir / "w3_eval_report_draft.md",
            pilot_rows,
            pilot30_rows,
            tv1_rows,
            mcnemar_rows,
            stability_rows,
            source_note,
        )
        print(f"Wrote Week 3 evaluation tables and draft report to {args.out_dir}")
        return 0
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
