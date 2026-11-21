import pytest

from rag.llm_client import LLMClient


def make(tmp_path, monkeypatch, fail_times=0):
    client = LLMClient(provider="vllm", model="org/test-model", cache_dir=tmp_path)
    calls = {"n": 0}

    def fake_call(prompt, system, seed):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError("transient")
        return f"answer to {prompt}", {"total_tokens": 7}

    monkeypatch.setattr(client, "_call", fake_call)
    monkeypatch.setattr("rag.llm_client.time.sleep", lambda s: None)
    return client, calls


def test_cache_hit_avoids_second_call(tmp_path, monkeypatch):
    client, calls = make(tmp_path, monkeypatch)
    first = client.generate("Việt Nam có bao nhiêu tỉnh?")
    second = client.generate("Việt Nam có bao nhiêu tỉnh?")
    assert first["output"] == second["output"]
    assert calls["n"] == 1


def test_cache_persists_across_instances(tmp_path, monkeypatch):
    client, _ = make(tmp_path, monkeypatch)
    client.generate("câu hỏi", system="hệ thống")
    assert (tmp_path / "vllm__org_test-model.jsonl").exists()

    fresh, calls = make(tmp_path, monkeypatch)
    assert fresh.generate("câu hỏi", system="hệ thống")["output"] == "answer to câu hỏi"
    assert calls["n"] == 0


def test_key_depends_on_system_and_seed(tmp_path, monkeypatch):
    client, calls = make(tmp_path, monkeypatch)
    client.generate("q")
    client.generate("q", system="s")
    client.generate("q", seed=1)
    client.generate("q", seed=2)
    assert calls["n"] == 4


def test_retries_then_succeeds(tmp_path, monkeypatch):
    client, calls = make(tmp_path, monkeypatch, fail_times=2)
    assert client.generate("q")["output"] == "answer to q"
    assert calls["n"] == 3


def test_raises_after_max_retries_and_caches_nothing(tmp_path, monkeypatch):
    client, calls = make(tmp_path, monkeypatch, fail_times=99)
    with pytest.raises(RuntimeError):
        client.generate("q")
    assert calls["n"] == client.max_retries
    assert not (tmp_path / "vllm__org_test-model.jsonl").exists()
