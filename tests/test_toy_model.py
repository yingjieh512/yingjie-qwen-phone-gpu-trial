from pathlib import Path

from qpnpu.model_format import read_model_metadata, tensor_index, validate_model_metadata
from qpnpu.toy_model import create_toy_model


def test_create_toy_model_writes_expected_files(tmp_path: Path) -> None:
    model_dir = tmp_path / "toy_qwen"
    metadata = create_toy_model(model_dir)

    assert (model_dir / "metadata.json").exists()
    assert (model_dir / "model.bin").exists()
    assert (model_dir / "tokenizer_stub.json").exists()
    assert (model_dir / "README.md").exists()
    assert validate_model_metadata(metadata) == []
    assert validate_model_metadata(read_model_metadata(model_dir)) == []

    tensors = tensor_index(metadata)
    assert set(tensors) == {"token_embedding.weight", "norm.weight", "lm_head.weight"}
    assert tensors["token_embedding.weight"]["shape"] == [256, 32]
    assert tensors["norm.weight"]["shape"] == [32]
    assert tensors["lm_head.weight"]["shape"] == [256, 32]


def test_create_toy_model_refuses_overwrite_without_flag(tmp_path: Path) -> None:
    model_dir = tmp_path / "toy_qwen"
    create_toy_model(model_dir)

    try:
        create_toy_model(model_dir)
    except FileExistsError as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")


def test_create_toy_model_overwrite_regenerates(tmp_path: Path) -> None:
    model_dir = tmp_path / "toy_qwen"
    create_toy_model(model_dir)
    metadata = create_toy_model(model_dir, overwrite=True)

    assert validate_model_metadata(metadata) == []
    assert (model_dir / "model.bin").stat().st_size > 0