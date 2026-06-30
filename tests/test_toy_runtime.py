from pathlib import Path

from qpnpu.toy_model import create_toy_model
from qpnpu.toy_runtime import ByteTokenizerStub, ToyQwenRuntime


def test_byte_tokenizer_stub_roundtrip_ascii() -> None:
    tokenizer = ByteTokenizerStub()
    token_ids = tokenizer.encode("hello")

    assert token_ids == [104, 101, 108, 108, 111]
    assert tokenizer.decode(token_ids) == "hello"


def test_toy_runtime_generate_is_deterministic(tmp_path: Path) -> None:
    model_dir = tmp_path / "toy_qwen"
    create_toy_model(model_dir)

    runtime_a = ToyQwenRuntime(model_dir)
    runtime_b = ToyQwenRuntime(model_dir)
    result_a = runtime_a.generate("hello", max_new_tokens=4)
    result_b = runtime_b.generate("hello", max_new_tokens=4)

    assert result_a["prompt"] == "hello"
    assert result_a["prompt_token_ids"] == [104, 101, 108, 108, 111]
    assert result_a["generated_token_ids"] == result_b["generated_token_ids"]
    assert len(result_a["generated_token_ids"]) == 4
    assert isinstance(result_a["generated_text"], str)
    assert "latency_ms_total" in result_a
    assert "tokens_per_second" in result_a
    assert result_a["latency_ms_total"] >= 0.0
    assert result_a["tokens_per_second"] >= 0.0