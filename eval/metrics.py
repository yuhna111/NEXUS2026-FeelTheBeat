"""Metrics per eval/metrics_spec.md v0.2 (TV3).

Usage:
    python -m eval.metrics outputs/C1/qwen-7b.jsonl --bench data/benchmark/pilot_30_vinh.jsonl
        [--labels labels.jsonl] [--baseline outputs/C0/qwen-7b.jsonl] [--k 5] [--json out.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.normalize import normalize
from eval.qa_schema import chunk_id_to_clause_id, recall_gold_ids
from eval.staleness_rules import is_abstention, rejects_premise, rule_verdict

LABELS = ("CORRECT_CURRENT", "STALE", "BLENDED", "OTHER_ERROR", "ABSTAIN")
NEEDS_JUDGE = "NEEDS_JUDGE"
STALE_LABELS = frozenset({"STALE", "BLENDED"})
PRED_REQUIRED = ("question_id", "output")
RETRIEVAL_FREE_CONFIGS = frozenset({"C0"})
ORACLE_CONFIGS = frozenset({"C5"})
ENTITY_TYPES = frozenset({"entity", "entity_list"})
DEFAULT_ENTITY_MAPS = (Path("data/processed/entity_map_63_34_v1.csv"),
                       Path("data/processed/entity_map_63_34_draft.csv"))

_NUM_RE = re.compile(r"(?<![\d/])\d{1,3}(?:[.,]\d{3})+(?![\d/])|(?<![\d/.,])\d+(?![\d/])")
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
_YES = ("có", "đúng", "phải", "rồi", "yes")
_NO = ("không", "chưa", "sai", "no")


def _s(x: Any) -> str:
    return "" if x is None else str(x)


def exact_match(pred: str | None, golds: Iterable[str] | None) -> float:
    p = normalize(_s(pred))
    return float(any(p == normalize(_s(g)) for g in golds or []))


def token_f1(pred: str | None, gold: str | None) -> float:
    p, g = normalize(_s(pred)).split(), normalize(_s(gold)).split()
    if not p or not g:
        return float(p == g)
    common = sum(min(p.count(t), g.count(t)) for t in set(p))
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def set_f1(pred_items: Iterable[str] | None, gold_items: Iterable[str] | None) -> float:
    P = {normalize(_s(x)) for x in pred_items or []} - {""}
    G = {normalize(_s(x)) for x in gold_items or []} - {""}
    if not P and not G:
        return 1.0
    inter = len(P & G)
    if inter == 0:
        return 0.0
    prec, rec = inter / len(P), inter / len(G)
    return 2 * prec * rec / (prec + rec)


def staleness_rate(stale_flags: Sequence[bool]) -> float:
    return sum(bool(f) for f in stale_flags) / len(stale_flags) if stale_flags else 0.0


def knowledge_override_rate(stale_c0: Sequence[bool], correct_k: Sequence[bool]) -> float:
    denom = sum(bool(s) for s in stale_c0)
    if denom == 0:
        return 0.0
    return sum(bool(s) and bool(c) for s, c in zip(stale_c0, correct_k, strict=True)) / denom


def prior_bias_error_rate(gold_in_ctx: Sequence[bool], stale_k: Sequence[bool]) -> float:
    denom = sum(bool(g) for g in gold_in_ctx)
    if denom == 0:
        return 0.0
    return sum(bool(g) and bool(s) for g, s in zip(gold_in_ctx, stale_k, strict=True)) / denom


def recall_at_k(gold_ids: Sequence[set[str]], retrieved: Sequence[Sequence[str]], k: int) -> float:
    hits = [bool(set(g or ()) & set(list(r or [])[:k])) for g, r in zip(gold_ids, retrieved, strict=True)]
    return sum(hits) / len(hits) if hits else 0.0


def mrr(gold_ids: Sequence[set[str]], retrieved: Sequence[Sequence[str]], k: int | None = None) -> float:
    total = 0.0
    for g, r in zip(gold_ids, retrieved, strict=True):
        ranked = list(r or [])
        for rank, cid in enumerate(ranked[:k] if k else ranked, start=1):
            if cid in (g or ()):
                total += 1.0 / rank
                break
    return total / len(gold_ids) if gold_ids else 0.0


FIXED_MIN_COVER = 0.5


def _ws_tokens(s: str | None) -> list[str]:
    return unicodedata.normalize("NFC", s or "").lower().split()


def clause_coverage(clause_text: str | None, chunk_text: str | None) -> float:
    """Longest contiguous run of the clause's tokens inside the chunk, as a share of the clause."""
    a, b = _ws_tokens(clause_text), _ws_tokens(chunk_text)
    if not a or not b:
        return 0.0
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, start=1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best / len(a)


def fixed_chunk_hit(chunk_id: str, chunk_text: str | None,
                    gold_clauses: Mapping[str, str | Sequence[str]],
                    min_cover: float = FIXED_MIN_COVER) -> bool:
    """metrics_spec §5.8: same doc_id as a gold clause and covers ≥ min_cover of that clause contiguously."""
    doc = (chunk_id or "").split("#", 1)[0]
    for cid, texts in gold_clauses.items():
        if cid.split("#", 1)[0] != doc:
            continue
        for t in [texts] if isinstance(texts, str) else texts:
            if clause_coverage(t, chunk_text) >= min_cover:
                return True
    return False


def fixed_hit_rank(context_ids: Sequence[str], chunk_texts: Mapping[str, str],
                   gold_clauses: Mapping[str, str | Sequence[str]], k: int | None = None,
                   min_cover: float = FIXED_MIN_COVER) -> int | None:
    ranked = list(context_ids or [])
    for rank, cid in enumerate(ranked[:k] if k else ranked, start=1):
        if fixed_chunk_hit(cid, chunk_texts.get(cid), gold_clauses, min_cover):
            return rank
    return None


@dataclass(frozen=True)
class Ratio:
    num: int
    den: int
    ci: tuple[float, float] | None = None

    @property
    def value(self) -> float | None:
        return self.num / self.den if self.den else None

    def as_dict(self) -> dict[str, Any]:
        return {"num": self.num, "den": self.den, "value": self.value,
                "ci95": list(self.ci) if self.ci else None}


def bootstrap_ci(values: Sequence[float], n_boot: int = 1000, alpha: float = 0.05,
                 seed: int = 0) -> tuple[float, float] | None:
    if not values or n_boot <= 0:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    lo = means[max(0, math.floor(alpha / 2 * n_boot))]
    hi = means[min(n_boot - 1, math.ceil((1 - alpha / 2) * n_boot) - 1)]
    return lo, hi


def ratio(flags: Sequence[bool], n_boot: int = 0, seed: int = 0) -> Ratio:
    vals = [1.0 if f else 0.0 for f in flags]
    return Ratio(int(sum(vals)), len(vals), bootstrap_ci(vals, n_boot, seed=seed) if n_boot else None)


def paired_bootstrap(a: Sequence[float], b: Sequence[float], n_boot: int = 1000,
                     seed: int = 0) -> dict[str, float] | None:
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    if not a:
        return None
    diffs = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    n = len(diffs)
    boots = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    observed = sum(diffs) / n
    p = 2 * min(sum(d <= 0 for d in boots), sum(d >= 0 for d in boots)) / n_boot
    return {"diff": observed, "ci_lo": boots[int(0.025 * n_boot)],
            "ci_hi": boots[min(n_boot - 1, math.ceil(0.975 * n_boot) - 1)], "p": min(1.0, p)}


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def holm_bonferroni(pvalues: Sequence[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    if len(a) != len(b):
        raise ValueError("annotations must have equal length")
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def _canon_num(s: str) -> str:
    return re.sub(r"[.,]", "", s).lstrip("0") or "0"


def extract_numbers(text: str | None) -> list[str]:
    t = _DATE_RE.sub(" ", unicodedata.normalize("NFC", _s(text)))
    return [_canon_num(m.group(0)) for m in _NUM_RE.finditer(t)]


def extract_dates(text: str | None) -> list[tuple[int, int, int]]:
    return [(int(y), int(m), int(d)) for d, m, y in _DATE_RE.findall(_s(text))]


def yes_no_polarity(text: str | None) -> bool | None:
    words = normalize(_s(text)).split()
    head = words[0] if words else ""
    if head in _YES:
        return True
    if head in _NO:
        return False
    return None


def extract_entities(text: str | None, vocab: Iterable[str]) -> set[str]:
    t = f" {normalize(_s(text))} "
    out: set[str] = set()
    for name in sorted({normalize(_s(v)) for v in vocab} - {""}, key=len, reverse=True):
        token = f" {name} "
        if token in t:
            out.add(name)
            t = t.replace(token, " | ")
    return out


def _contains(text: str, name: str) -> bool:
    return f" {normalize(name)} " in f" {normalize(text)} " if normalize(name) else False


def _gold(q: Mapping[str, Any]) -> Mapping[str, Any]:
    g = q.get("gold_answer")
    return g if isinstance(g, Mapping) else {}


def _gold_entities(q: Mapping[str, Any]) -> list[str]:
    g = _gold(q)
    return [e for e in g.get("entities") or [] if e] or [a for a in g.get("aliases") or [] if a]


def _obsolete(q: Mapping[str, Any]) -> list[str]:
    o = q.get("obsolete_answer")
    return [e for e in (o.get("obsolete_entities") or [] if isinstance(o, Mapping) else []) if e]


def answer_match(output: str | None, q: Mapping[str, Any], vocab: Iterable[str] = ()) -> bool | None:
    g = _gold(q)
    atype, out = g.get("answer_type"), _s(output)
    if atype == "entity":
        names = _gold_entities(q)
        return any(_contains(out, n) for n in names) if names else None
    if atype in ("entity_list", "set"):
        gold = {normalize(e) for e in _gold_entities(q)} - {""}
        if not gold:
            return None
        found = extract_entities(out, set(vocab) | gold)
        return found == gold if found <= gold or not gold <= found else None
    if atype == "number":
        nums = [_canon_num(a) for a in g.get("aliases") or [] if re.fullmatch(r"[\d.,]+", _s(a).strip())]
        target = nums[0] if nums else next(iter(extract_numbers(g.get("text"))), None)
        return target in extract_numbers(out) if target else None
    if atype == "yes_no":
        want, got = yes_no_polarity(g.get("text")), yes_no_polarity(out)
        return None if want is None or got is None else want == got
    if atype == "premise_rejection":
        return rejects_premise(out)
    if atype == "date":
        want = extract_dates(g.get("text"))
        return want[0] in extract_dates(out) if want else None
    return None


def answer_set_f1(output: str | None, q: Mapping[str, Any], vocab: Iterable[str] = ()) -> float | None:
    if _gold(q).get("answer_type") not in ("entity_list", "set"):
        return None
    gold = {normalize(e) for e in _gold_entities(q)} - {""}
    return set_f1(extract_entities(output, set(vocab) | gold), gold) if gold else None


def is_negative_control(q: Mapping[str, Any]) -> bool:
    return q.get("item_role") == "control" and q.get("category") == "B_obsolete_trap"


def current_entities_for_rules(q: Mapping[str, Any]) -> list[str]:
    if _gold(q).get("answer_type") not in ENTITY_TYPES:
        return []
    question = _s(q.get("question"))
    return [e for e in _gold_entities(q) if not _contains(question, e)]


def auto_label(output: str | None, q: Mapping[str, Any], vocab: Iterable[str] = ()) -> str:
    out = _s(output)
    verdict = rule_verdict(out, _obsolete(q), current_entities_for_rules(q))
    if verdict is None:
        return NEEDS_JUDGE
    if verdict == "STALE":
        return "STALE"
    if is_negative_control(q) and rejects_premise(out):
        return "OTHER_ERROR"
    match = answer_match(out, q, vocab)
    if match is True:
        return "CORRECT_CURRENT"
    if is_abstention(out):
        return "ABSTAIN"
    return "OTHER_ERROR" if match is False else NEEDS_JUDGE


def read_jsonl(path: Path, warn: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    out = []
    with path.open(encoding="utf-8-sig") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                if warn:
                    warn(f"{path}:{n}: invalid JSON ({e.msg})")
                continue
            if isinstance(rec, dict):
                out.append(rec)
            elif warn:
                warn(f"{path}:{n}: not a JSON object")
    return out


def load_predictions(path: Path, warn: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    out = []
    for rec in read_jsonl(path, warn):
        missing = [k for k in PRED_REQUIRED if k not in rec]
        if missing or not rec.get("question_id"):
            if warn:
                warn(f"{path}: skip record missing {missing or ['question_id']}")
            continue
        rec["output"] = _s(rec.get("output"))
        ctx = rec.get("context_ids")
        rec["context_ids"] = [str(c) for c in ctx if c] if isinstance(ctx, list) else []
        out.append(rec)
    return out


def load_labels(path: Path, warn: Callable[[str], None] | None = None) -> dict[str, str]:
    rows: Iterable[Mapping[str, Any]]
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = read_jsonl(path, warn)
    out: dict[str, str] = {}
    for r in rows:
        qid, label = _s(r.get("question_id")).strip(), _s(r.get("label")).strip().upper()
        if qid and label in LABELS:
            out[qid] = label
        elif qid and warn:
            warn(f"{path}: ignore label {label!r} for {qid}")
    return out


def load_vocab(paths: Iterable[Path], bench: Iterable[Mapping[str, Any]] = ()) -> set[str]:
    vocab: set[str] = set()
    for p in paths:
        if p.exists():
            with p.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    vocab.update(_s(row.get(c)).strip() for c in ("old_province", "new_province"))
            break
    for q in bench:
        vocab.update(_gold_entities(q))
    return {v for v in vocab if v}


def _to_clause_id(cid: str) -> str:
    return chunk_id_to_clause_id(cid) or cid


def _gold_in_context(pred: Mapping[str, Any], gold: set[str] | None, k: int) -> bool | None:
    if _s(pred.get("config")) in ORACLE_CONFIGS:
        return True
    if not gold:
        return None
    return bool(gold & {_to_clause_id(c) for c in pred["context_ids"][:k]})


def _breakdown(items: list[tuple[Mapping[str, Any], str]], key: Callable[[Mapping[str, Any]], Any],
               n_boot: int, seed: int) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for q, label in items:
        groups[_s(key(q)) or "null"].append(label)
    return {g: {"SR": ratio([lab == "STALE" for lab in labs], n_boot, seed).as_dict(),
                "SR_plus": ratio([lab in STALE_LABELS for lab in labs], n_boot, seed).as_dict()}
            for g, labs in sorted(groups.items())}


def evaluate(preds: list[dict[str, Any]], bench: Mapping[str, Mapping[str, Any]],
             labels: Mapping[str, str] | None = None, baseline: list[dict[str, Any]] | None = None,
             baseline_labels: Mapping[str, str] | None = None, k: int = 5, vocab: Iterable[str] = (),
             n_boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    vocab = set(vocab)
    labels = labels or {}
    known = [p for p in preds if p["question_id"] in bench]
    unknown = sorted({p["question_id"] for p in preds} - set(bench))

    def label_of(p: Mapping[str, Any], explicit: Mapping[str, str]) -> tuple[str, str]:
        qid = p["question_id"]
        if qid in explicit:
            return explicit[qid], "labels_file"
        if _s(p.get("label")).upper() in LABELS:
            return _s(p["label"]).upper(), "prediction"
        return auto_label(p["output"], bench[qid], vocab), "auto"

    per_q: dict[str, str] = {}
    sources: Counter[str] = Counter()
    for p in known:
        lab, src = label_of(p, labels)
        per_q[p["question_id"]] = lab
        sources[src] += 1
    labeled = [(bench[q], lab) for q, lab in per_q.items() if lab in LABELS]
    labs = [lab for _, lab in labeled]

    em_flags, f1s = [], []
    for p in known:
        q = bench[p["question_id"]]
        m = answer_match(p["output"], q, vocab)
        if m is not None:
            em_flags.append(m)
        f = answer_set_f1(p["output"], q, vocab)
        if f is not None:
            f1s.append(f)

    neg = [p for p in known if is_negative_control(bench[p["question_id"]])]

    retrieval_preds = [p for p in known if _s(p.get("config")) not in RETRIEVAL_FREE_CONFIGS
                       and _s(p.get("config")) not in ORACLE_CONFIGS]
    golds, rets = [], []
    for p in retrieval_preds:
        g = recall_gold_ids(bench[p["question_id"]])
        if g:
            golds.append(g)
            rets.append([_to_clause_id(c) for c in p["context_ids"]])

    pber_pairs = []
    for p in known:
        lab = per_q[p["question_id"]]
        gic = _gold_in_context(p, recall_gold_ids(bench[p["question_id"]]), k)
        if lab in LABELS and gic is not None and _s(p.get("config")) not in RETRIEVAL_FREE_CONFIGS:
            pber_pairs.append((gic, lab in STALE_LABELS))

    report: dict[str, Any] = {
        "n_predictions": len(preds), "n_scored": len(known), "unknown_question_ids": unknown,
        "missing_question_ids": sorted(set(bench) - {p["question_id"] for p in known}),
        "label_sources": dict(sources), "label_counts": dict(Counter(per_q.values())),
        "pending_judge": sorted(q for q, lab in per_q.items() if lab == NEEDS_JUDGE),
        "SR": ratio([lab == "STALE" for lab in labs], n_boot, seed).as_dict(),
        "SR_plus": ratio([lab in STALE_LABELS for lab in labs], n_boot, seed).as_dict(),
        "AbstainRate": ratio([lab == "ABSTAIN" for lab in labs], n_boot, seed).as_dict(),
        "EM": ratio(em_flags, n_boot, seed).as_dict(),
        "F1_set": {"mean": sum(f1s) / len(f1s) if f1s else None, "n": len(f1s),
                   "ci95": bootstrap_ci(f1s, n_boot, seed=seed) if f1s else None},
        "OverRejection": ratio([rejects_premise(p["output"]) for p in neg], n_boot, seed).as_dict(),
        "by_category": _breakdown(labeled, lambda q: q.get("category"), n_boot, seed),
        "by_item_role": _breakdown(labeled, lambda q: q.get("item_role"), n_boot, seed),
        "by_province_is_control": _breakdown(labeled, lambda q: q.get("province_is_control"), n_boot, seed),
        f"Recall@{k}": Ratio(round(recall_at_k(golds, rets, k) * len(golds)), len(golds)).as_dict(),
        f"MRR@{k}": {"value": mrr(golds, rets, k) if golds else None, "n": len(golds)},
        "PBER": Ratio(sum(g and s for g, s in pber_pairs), sum(g for g, _ in pber_pairs)).as_dict(),
    }
    if baseline is not None:
        base_known = {p["question_id"]: p for p in baseline if p["question_id"] in bench}
        pairs = []
        for qid, lab in per_q.items():
            if qid not in base_known:
                continue
            b, _ = label_of(base_known[qid], baseline_labels or {})
            if b in LABELS and lab in LABELS:
                pairs.append((b == "STALE", lab == "CORRECT_CURRENT"))
        report["KOR"] = Ratio(sum(s and c for s, c in pairs), sum(s for s, _ in pairs)).as_dict()
    return report


def _fmt(d: Mapping[str, Any]) -> str:
    if not d.get("den"):
        return "n/a (0/0)"
    ci = d.get("ci95")
    tail = f" [{ci[0]:.1%}–{ci[1]:.1%}]" if ci else ""
    return f"{d['num']}/{d['den']} = {d['value']:.1%}{tail}"


def _fmt_mean(value: float | None, n: int) -> str:
    return f"{'n/a' if value is None else format(value, '.3f')} (n={n})"


def print_report(r: Mapping[str, Any], k: int, out: Any = None) -> None:
    lines = [f"predictions: {r['n_predictions']}  scored: {r['n_scored']}  label sources: {r['label_sources']}",
             f"labels: {r['label_counts']}"]
    if r["pending_judge"]:
        lines.append(f"pending LLM judge ({len(r['pending_judge'])}): {', '.join(r['pending_judge'])}")
    if r["unknown_question_ids"]:
        lines.append(f"not in benchmark: {', '.join(r['unknown_question_ids'])}")
    for name in ("SR", "SR_plus", "AbstainRate", "EM", "OverRejection", "PBER", "KOR"):
        if name in r:
            lines.append(f"{name:<14}{_fmt(r[name])}")
    lines.append(f"{'F1_set':<14}{_fmt_mean(r['F1_set']['mean'], r['F1_set']['n'])}")
    lines.append(f"{'Recall@' + str(k):<14}{_fmt(r[f'Recall@{k}'])}")
    lines.append(f"{'MRR@' + str(k):<14}{_fmt_mean(r[f'MRR@{k}']['value'], r[f'MRR@{k}']['n'])}")
    for group in ("by_category", "by_item_role", "by_province_is_control"):
        lines.append(f"{group}:")
        lines += [f"  {g:<22} SR {_fmt(v['SR'])} · SR+ {_fmt(v['SR_plus'])}" for g, v in r[group].items()]
    print("\n".join(lines), file=out or sys.stdout)


def _warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a prediction JSONL against the benchmark")
    ap.add_argument("predictions", type=Path)
    ap.add_argument("--bench", type=Path, default=Path("data/benchmark/vn_admin2025_qa_v1.0.jsonl"))
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--baseline-labels", type=Path)
    ap.add_argument("--entity-map", type=Path)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    warn = _warn
    if not args.predictions.exists():
        print(f"error: {args.predictions} not found", file=sys.stderr)
        return 2
    bench = {q["id"]: q for q in read_jsonl(args.bench, warn) if q.get("id")}
    if not bench:
        print(f"error: benchmark {args.bench} is empty or missing", file=sys.stderr)
        return 2
    preds = load_predictions(args.predictions, warn)
    if not preds:
        print(f"error: no usable predictions in {args.predictions}", file=sys.stderr)
        return 2
    vocab = load_vocab([args.entity_map] if args.entity_map else DEFAULT_ENTITY_MAPS, bench.values())
    report = evaluate(
        preds, bench,
        labels=load_labels(args.labels, warn) if args.labels else None,
        baseline=load_predictions(args.baseline, warn) if args.baseline else None,
        baseline_labels=load_labels(args.baseline_labels, warn) if args.baseline_labels else None,
        k=args.k, vocab=vocab, n_boot=args.bootstrap, seed=args.seed,
    )
    print_report(report, args.k)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
