from __future__ import annotations

import json

import pytest

from qpnpu.layer_slice import (
    REFERENCE_OUTPUT_NAMES,
    create_layer_slice_model,
    run_layer_slice_check,
    validate_layer_slice_check_result,
)
from qpnpu.model_format import load_tensor, read_model_metadata, validate_model_metadata


def test_create_layer_slice_artifact_and_validate_metadata(tmp_path):
    model_dir = tmp_path / "layer_slice"

    metadata = create_layer_slice_model(model_dir, overwrite=True)

    assert (model_dir / "metadata.json").exists()
    assert (model_dir / "model.bin").exists()
    assert (model_dir / "reference_outputs.json").exists()
    assert (model_dir / "tokenizer_stub.json").exists()
    assert (model_dir / "README.md").exists()
    assert metadata["model"]["architecture"] == "qwen_toy_layer_slice"
    assert validate_model_metadata(metadata) == []
    assert {entry["name"] for entry in metadata["tensors"]} >= {
        "token_embedding.weight",
        "layer.0.input_norm.weight",
        "layer.0.q_proj.weight",
        "layer.0.k_proj.weight",
        "layer.0.v_proj.weight",
        "layer.0.o_proj.weight",
        "layer.0.post_attention_norm.weight",
        "layer.0.mlp_gate.weight",
        "layer.0.mlp_up.weight",
        "layer.0.mlp_down.weight",
        "lm_head.weight",
    }

    reference = json.loads((model_dir / "reference_outputs.json").read_text(encoding="utf-8"))
    assert reference["source"] == "phase10-layer-slice-reference"
    assert sorted(reference["outputs"]) == sorted(REFERENCE_OUTPUT_NAMES)


def test_layer_slice_check_passes_and_is_deterministic(tmp_path):
    model_dir = tmp_path / "layer_slice"
    create_layer_slice_model(model_dir, {"seed": 77}, overwrite=True)

    first = run_layer_slice_check(model_dir)
    second = run_layer_slice_check(model_dir)

    assert validate_layer_slice_check_result(first) == []
    assert first["summary"]["all_passed"] is True
    assert first["summary"]["passed_check_count"] == len(REFERENCE_OUTPUT_NAMES)
    assert first["summary"]["next_token_id_actual"] == first["summary"]["next_token_id_expected"]
    assert first["token_ids"] == [104, 101, 108, 108, 111, 0, 0, 0]
    assert [check["sha256_actual"] for check in first["checks"]] == [
        check["sha256_actual"] for check in second["checks"]
    ]
    assert first["summary"]["next_token_id_actual"] == second["summary"]["next_token_id_actual"]


def test_layer_slice_loads_tensor_by_name(tmp_path):
    model_dir = tmp_path / "layer_slice"
    create_layer_slice_model(model_dir, overwrite=True)
    metadata = read_model_metadata(model_dir)

    tensor = load_tensor(model_dir, metadata, "layer.0.mlp_down.weight")

    assert tensor.shape == (32, 64)


def test_layer_slice_check_detects_corrupted_reference(tmp_path):
    model_dir = tmp_path / "layer_slice"
    create_layer_slice_model(model_dir, overwrite=True)
    reference_path = model_dir / "reference_outputs.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    reference["outputs"]["embedding"]["values"][0][0] += 1.0
    reference_path.write_text(json.dumps(reference, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_layer_slice_check(model_dir)

    assert result["summary"]["all_passed"] is False
    assert validate_layer_slice_check_result(result) == ["summary.all_passed must be true"]
    embedding_check = next(check for check in result["checks"] if check["name"] == "embedding")
    assert embedding_check["passed"] is False
    assert embedding_check["max_abs_error"] == pytest.approx(1.0)
