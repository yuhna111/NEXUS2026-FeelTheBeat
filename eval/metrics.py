"""Metrics (plan §1.4, TV3): EM, token-F1, set-F1, SR, KOR, PBER, Recall@k, MRR."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from eval.normalize import normalize


# ----------------------------------------------------------------- answer level
def exact_match(pred: str, golds: Iterable[str]) -> float:
    p = normalize(pred)
    return float(any(p == normalize(g) for g in golds))


def token_f1(pred: str, gold: str) -> float:
    p, g = normalize(pred).split(), normalize(gold).split()
    if not p or not g:
        return float(p == g)
    common = sum(min(p.count(t), g.count(t)) for t in set(p))
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def set_f1(pred_items: Iterable[str], gold_items: Iterable[str]) -> float:
    P = {normalize(x) for x in pred_items}
    G = {normalize(x) for x in gold_items}
    if not P and not G:
        return 1.0
    if not P or not G:
        return 0.0
    inter = len(P & G)
    if inter == 0:
        return 0.0
    prec, rec = inter / len(P), inter / len(G)
    return 2 * prec * rec / (prec + rec)


# ------------------------------------------------------------- staleness level
def staleness_rate(stale_flags: Sequence[bool]) -> float:
    """SR = mean over questions of 1[answer asserts an obsolete entity as current]."""
    return sum(stale_flags) / len(stale_flags) if stale_flags else 0.0


def knowledge_override_rate(stale_c0: Sequence[bool], correct_k: Sequence[bool]) -> float:
    """KOR_k = |stale in C0 ∧ correct in k| / |stale in C0|."""
    denom = sum(stale_c0)
    if denom == 0:
        return 0.0
    return sum(s and c for s, c in zip(stale_c0, correct_k, strict=True)) / denom


def prior_bias_error_rate(gold_in_ctx: Sequence[bool], stale_k: Sequence[bool]) -> float:
    """PBER_k = |gold in context ∧ stale| / |gold in context|."""
    denom = sum(gold_in_ctx)
    if denom == 0:
        return 0.0
    return sum(g and s for g, s in zip(gold_in_ctx, stale_k, strict=True)) / denom


# -------------------------------------------------------------- retrieval level
def recall_at_k(gold_ids: Sequence[set[str]], retrieved: Sequence[Sequence[str]], k: int) -> float:
    hits = [bool(g & set(r[:k])) for g, r in zip(gold_ids, retrieved, strict=True)]
    return sum(hits) / len(hits) if hits else 0.0


def mrr(gold_ids: Sequence[set[str]], retrieved: Sequence[Sequence[str]]) -> float:
    total = 0.0
    for g, r in zip(gold_ids, retrieved, strict=True):
        for rank, cid in enumerate(r, start=1):
            if cid in g:
                total += 1.0 / rank
                break
    return total / len(gold_ids) if gold_ids else 0.0


if __name__ == "__main__":
    # TODO(TV3): CLI — read outputs/<config>/*.jsonl + benchmark, write results/main_table.csv
    raise SystemExit("eval CLI not implemented yet (Week 5)")
