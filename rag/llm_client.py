"""Unified LLM client (closed APIs + vLLM) with retry and JSONL cache.

Every call is cached by a hash of (model, prompt, params) so re-running never
re-bills the API and every number in the paper is traceable to a cached line.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMClient:
    provider: str                    # openai | gemini | anthropic | vllm
    model: str
    temperature: float = 0.0
    max_tokens: int = 512
    max_retries: int = 8              # backoff 2, 4, 8, … capped at 60 s (API rate limits)
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("LLM_CACHE_DIR", ".llm_cache")))

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_file = self.cache_dir / f"{self.provider}__{self.model.replace('/', '_')}.jsonl"
        self._cache: dict[str, dict] = {}
        if self._cache_file.exists():
            with self._cache_file.open(encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    self._cache[rec["key"]] = rec

    # ------------------------------------------------------------------ cache
    def _key(self, system: str | None, prompt: str, seed: int | None) -> str:
        payload = json.dumps(
            [self.provider, self.model, system, prompt, self.temperature, self.max_tokens, seed],
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _save(self, rec: dict) -> None:
        self._cache[rec["key"]] = rec
        with self._cache_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------- call
    def generate(self, prompt: str, system: str | None = None, seed: int | None = None) -> dict:
        key = self._key(system, prompt, seed)
        if key in self._cache:
            return self._cache[key]

        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                text, usage = self._call(prompt, system, seed)
                break
            except Exception:  # noqa: BLE001 — retry any transient API error
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60.0)

        rec = {
            "key": key,
            "provider": self.provider,
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "temperature": self.temperature,
            "seed": seed,
            "output": text,
            "usage": usage,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        self._save(rec)
        return rec

    def _call(self, prompt: str, system: str | None, seed: int | None) -> tuple[str, dict]:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        if self.provider in ("openai", "vllm"):
            from openai import OpenAI

            client = (
                OpenAI(base_url=os.getenv("VLLM_BASE_URL"), api_key="EMPTY")
                if self.provider == "vllm"
                else OpenAI()
            )
            r = client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature,
                max_tokens=self.max_tokens, seed=seed,
            )
            return r.choices[0].message.content, r.usage.model_dump() if r.usage else {}
        if self.provider == "anthropic":
            import anthropic

            r = anthropic.Anthropic().messages.create(
                model=self.model, system=system or "", max_tokens=self.max_tokens,
                temperature=self.temperature, messages=[{"role": "user", "content": prompt}],
            )
            return r.content[0].text, r.usage.model_dump()
        if self.provider == "gemini":
            from google import genai

            # Keep a reference: a temporary genai.Client() can be closed (and its HTTP
            # session with it) before the request is sent.
            client = genai.Client()
            r = client.models.generate_content(
                model=self.model, contents=prompt,
                config={"system_instruction": system, "temperature": self.temperature,
                        "max_output_tokens": self.max_tokens,
                        **({"seed": seed} if seed is not None else {})},
            )
            usage = r.usage_metadata.model_dump(exclude_none=True) if r.usage_metadata else {}
            # Gemini aliases can be served by a newer model; record what actually answered.
            usage["model_version"] = r.model_version
            return r.text or "", usage
        raise ValueError(f"Unknown provider: {self.provider}")


if __name__ == "__main__":
    # Smoke test: python -m rag.llm_client --provider vllm --model <id> "Câu hỏi"
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="One cached call through LLMClient.")
    ap.add_argument("--provider", required=True, choices=["openai", "gemini", "anthropic", "vllm"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--system")
    ap.add_argument("prompt")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rec = LLMClient(provider=a.provider, model=a.model).generate(a.prompt, system=a.system)
    print(rec["output"])
    print(f"--- usage: {rec['usage']} · cache: {rec['key'][:12]}", file=sys.stderr)
