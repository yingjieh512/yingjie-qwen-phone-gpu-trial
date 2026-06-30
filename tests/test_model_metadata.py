import pytest

from qpnpu.model_format import (
    load_tensor,
    minimal_model_metadata,
    read_model_metadata,
    tensor_index,
    validate_model_metadata,
)
from qpnpu.toy_model import create_toy_model


def test_minimal_model_metadata_validates() -> None:
    assert validate_model_metadata(minimal_model_metadata()) == []


def test_missing_required_model_metadata_fields_produces_errors() -> None:
    errors = validate_model_metadata({"schema_version": "0.1"})
    assert errors
    assert any("model" in error for error in errors)


def test_toy_metadata_validates_and_loads_tensor(tmp_path) -> None:
    model_dir = tmp_path / "toy_qwen"
    create_toy_model(model_dir)
    metadata = read_model_metadata(model_dir)

    assert validate_model_metadata(metadata) == []
    tensors = tensor_index(metadata)
    assert "token_embedding.weight" in tensors

    embedding = load_tensor(model_dir, metadata, "token_embedding.weight")
    assert embedding.shape == (256, 32)
    assert str(embedding.dtype) == "float32"


def test_load_missing_tensor_fails_clearly(tmp_path) -> None:
    model_dir = tmp_path / "toy_qwen"
    create_toy_model(model_dir)
    metadata = read_model_metadata(model_dir)

    with pytest.raises(KeyError, match="tensor not found"):
        load_tensor(model_dir, metadata, "missing.weight")