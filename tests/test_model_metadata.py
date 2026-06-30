from qpnpu.model_format import minimal_model_metadata, validate_model_metadata


def test_minimal_model_metadata_validates() -> None:
    assert validate_model_metadata(minimal_model_metadata()) == []


def test_missing_required_model_metadata_fields_produces_errors() -> None:
    errors = validate_model_metadata({"schema_version": "0.1"})
    assert errors
    assert any("model" in error for error in errors)

