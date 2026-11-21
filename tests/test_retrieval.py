from rag.chunkers import Chunk
from rag.eval_retrieval import hit_rank, norm, score
from rag.index_build import chunk_stats, point_id
from rag.retriever import BM25Retriever, Hit, hybrid_fuse

CHUNKS = [
    Chunk("NQ-1#D1.K1", "NQ-1", "Điều 1. Sắp xếp\nHợp nhất phường Hàng Bạc và phường Hàng Đào thành phường Hoàn Kiếm."),
    Chunk("NQ-1#D1.K2", "NQ-1", "Điều 1. Sắp xếp\nHợp nhất xã Tân Điền và xã Tân Phú thành xã Tân Điền."),
    Chunk("NQ-2#D2", "NQ-2", "Điều 2. Hiệu lực thi hành\nNghị quyết có hiệu lực từ ngày 01/07/2025."),
]


def simple_tok(text):
    return [t for t in norm(text).replace(".", " ").split() if t]


def test_bm25_ranks_matching_chunk_first():
    bm = BM25Retriever(CHUNKS, simple_tok)
    hits = bm.search("phường Hoàn Kiếm được hợp nhất từ những phường nào", k=2)
    assert hits[0].chunk_id == "NQ-1#D1.K1"
    assert len(hits) == 2


def test_hybrid_fuse_rewards_agreement_and_keeps_duplicate_ids_apart():
    a = Hit("X#D1.K1", "X", "text one", 9.0)
    b = Hit("X#D1.K2", "X", "text two", 8.0)
    dup = Hit("X#D1.K1", "X", "another clause with the same id", 7.0)
    fused = hybrid_fuse([[a, b, dup], [b, a]], k=60, top_n=3)
    assert {fused[0].chunk_id, fused[1].chunk_id} == {"X#D1.K1", "X#D1.K2"}
    assert len(fused) == 3 and fused[2].text == "another clause with the same id"


def test_hit_rank_legal_by_id_fixed_by_prefix():
    clauses = {"NQ-1#D1.K2": [norm("Hợp nhất xã Tân Điền và xã Tân Phú thành xã Tân Điền.")]}
    legal = [Hit("NQ-1#D1.K1", "NQ-1", "", 1), Hit("NQ-1#D1.K2", "NQ-1", "", 1)]
    assert hit_rank(legal, {"NQ-1#D1.K2"}, "legal", clauses, k=5) == 2
    assert hit_rank(legal, {"NQ-1#D1.K2"}, "legal", clauses, k=1) is None
    fixed = [Hit("NQ-1#fixed0", "NQ-1", "... HỢP NHẤT xã Tân Điền  và xã Tân Phú thành xã Tân Điền. Điều 2 ...", 1)]
    assert hit_rank(fixed, {"NQ-1#D1.K2"}, "fixed", clauses, k=5) == 1
    assert hit_rank(fixed, {"NQ-1#D1.K1"}, "fixed", clauses, k=5) is None


def test_score():
    assert score([1, None, 2, None]) == {"n": 4, "hits": 2, "recall": 0.5, "mrr": 0.375}


def test_point_ids_unique_for_repeated_chunk_ids():
    c = Chunk("NQ-203#D1.K1", "NQ-203", "a")
    assert point_id(c, 0) != point_id(c, 1)
    assert point_id(c, 0) == point_id(Chunk("NQ-203#D1.K1", "NQ-203", "b"), 0)
    assert chunk_stats([c, c])["duplicate_chunk_ids"] == ["NQ-203#D1.K1"]
