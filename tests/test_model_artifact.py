import subprocess
import sys
from pathlib import Path

from qpnpu.model_artifact import read_external_model_manifest, validate_external_model_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_create_external_toy_artifact_cli(tmp_path: Path) -> None:
    out = tmp_path / "external_toy"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "model" / "create_external_toy_artifact.py"),
            "--out",
            str(out),
            "--hidden-size",
            "16",
            "--overwrite",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = read_external_model_manifest(out / "manifest.json")
    assert validate_external_model_manifest(manifest, base_dir=out, check_files=True) == []
    assert (out / "metadata.json").exists()
    assert (out / "tokenizer_stub.json").exists()
    assert (out / "shards" / "model-00000.qpnpu").exists()


def test_external_manifest_detects_bad_hash(tmp_path: Path) -> None:
    out = tmp_path / "external_toy"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "model" / "create_external_toy_artifact.py"),
            "--out",
            str(out),
            "--overwrite",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = read_external_model_manifest(out / "manifest.json")
    manifest["files"][0]["sha256"] = "0" * 64

    errors = validate_external_model_manifest(manifest, base_dir=out, check_files=True)

    assert any("sha256 does not match" in error for error in errors)
