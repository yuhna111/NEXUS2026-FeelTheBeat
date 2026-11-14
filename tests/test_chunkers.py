from rag.chunkers import fixed_chunks, legal_chunks
from rag.retriever import rrf_fuse

LEGAL = """Điều 1. Sắp xếp đơn vị hành chính cấp tỉnh
1. Hợp nhất tỉnh A và tỉnh B thành tỉnh A.
2. Hợp nhất tỉnh C và tỉnh D thành tỉnh D.
Điều 2. Hiệu lực thi hành
Nghị quyết có hiệu lực từ ngày 01/07/2025.
"""


def test_legal_chunks():
    chunks = legal_chunks("NQ-TEST", LEGAL)
    assert [c.chunk_id for c in chunks] == ["NQ-TEST#Art1.1", "NQ-TEST#Art1.2", "NQ-TEST#Art2"]
    assert chunks[0].text.startswith("Điều 1.")


def test_fixed_chunks_overlap():
    text = " ".join(str(i) for i in range(1000))
    chunks = fixed_chunks("D", text, size=512, overlap=64)
    assert len(chunks) == 3
    assert chunks[1].text.split()[0] == "448"


def test_rrf():
    assert rrf_fuse([["a", "b", "c"], ["b", "a", "d"]], k=60, top_n=2) in (["a", "b"], ["b", "a"])
    assert rrf_fuse([["a"], ["b", "a"]])[0] == "a"
