"""CPU-only reference runtime for the tiny toy Qwen-like smoke model."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from qpnpu.model_format import load_tensor, read_model_metadata, validate_model_metadata


class ByteTokenizerStub:
    """Simple byte-level tokenizer stub used only by the toy model."""

    def encode(self, text: str) -> list[int]:
        return list(text.encode("utf-8"))

    def decode(self, token_ids: list[int]) -> str:
        byte_values = bytes(int(token_id) & 0xFF for token_id in token_ids)
        return byte_values.decode("utf-8", errors="replace")


class ToyQwenRuntime:
    """Deterministic CPU reference runtime for qwen_toy artifacts."""

    backend = "cpu_python_reference"

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.metadata = read_model_metadata(self.model_dir)
        errors = validate_model_metadata(self.metadata)
        if errors:
            joined = "; ".join(errors)
            raise ValueError(f"invalid QPNPU model metadata: {joined}")

        self.model = self.metadata["model"]
        if self.model.get("architecture") != "qwen_toy":
            raise ValueError("ToyQwenRuntime only supports architecture=qwen_toy")
        if self.model.get("dtype") != "fp32":
            raise ValueError("ToyQwenRuntime only supports fp32 toy tensors")

        self.tokenizer = ByteTokenizerStub()
        self.token_embedding = load_tensor(self.model_dir, self.metadata, "token_embedding.weight")
        self.norm_weight = load_tensor(self.model_dir, self.metadata, "norm.weight")
        self.lm_head = load_tensor(self.model_dir, self.metadata, "lm_head.weight")
        self.vocab_size = int(self.model["vocab_size"])
        self.hidden_size = int(self.model["hidden_size"])
        self._validate_tensor_shapes()

    def generate(self, prompt: str, max_new_tokens: int) -> dict[str, Any]:
        """Generate deterministic toy token ids from a prompt."""

        if max_new_tokens < 0:
            raise ValueError("max_new_tokens must be non-negative")

        prompt_token_ids = self.tokenizer.encode(prompt)
        current_token = prompt_token_ids[-1] if prompt_token_ids else 0
        generated_token_ids: list[int] = []

        start = time.perf_counter()
        for step in range(max_new_tokens):
            position = len(prompt_token_ids) + step
            hidden = self.token_embedding[current_token % self.vocab_size]
            hidden = _rms_norm(hidden, self.norm_weight)
            logits = self.lm_head @ hidden
            bias_index = (int(current_token) + position + 1) % self.vocab_size
            logits[bias_index] += 1.0 + 0.01 * (position % 7)
            next_token = int(np.argmax(logits))
            generated_token_ids.append(next_token)
            current_token = next_token
        elapsed_s = time.perf_counter() - start

        latency_ms_total = elapsed_s * 1000.0
        tokens_per_second = (len(generated_token_ids) / elapsed_s) if elapsed_s > 0.0 else 0.0
        return {
            "prompt": prompt,
            "prompt_token_ids": prompt_token_ids,
            "generated_token_ids": generated_token_ids,
            "generated_text": self.tokenizer.decode(generated_token_ids),
            "latency_ms_total": latency_ms_total,
            "tokens_per_second": tokens_per_second,
        }

    def _validate_tensor_shapes(self) -> None:
        expected_embedding = (self.vocab_size, self.hidden_size)
        if self.token_embedding.shape != expected_embedding:
            raise ValueError(f"token_embedding.weight shape mismatch: {self.token_embedding.shape}")
        if self.norm_weight.shape != (self.hidden_size,):
            raise ValueError(f"norm.weight shape mismatch: {self.norm_weight.shape}")
        if self.lm_head.shape != expected_embedding:
            raise ValueError(f"lm_head.weight shape mismatch: {self.lm_head.shape}")


def _rms_norm(hidden: np.ndarray, weight: np.ndarray, eps: float = 1.0e-6) -> np.ndarray:
    scale = np.sqrt(np.mean(np.square(hidden, dtype=np.float32), dtype=np.float32) + eps)
    return (hidden / scale) * weight