"""Helpers for tiny external QPNPU model artifact manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


MANIFEST_SOURCE = "qpnpu-external-model-manifest"
MANIFEST_FORMAT = "qpnpu_external_sharded"
REQUIRED_FILE_ROLES = {"metadata", "tensor_shard", "tokenizer_stub"}


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest for a file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_external_model_manifest(path: str | Path) -> dict[str, Any]:
    """Read an external model manifest JSON object."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("external model manifest must be a JSON object")
    return data


def write_external_model_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    """Write an external model manifest JSON object."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def validate_external_model_manifest(
    manifest: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
    check_files: bool = False,
) -> list[str]:
    """Validate a small externally delivered QPNPU model manifest.

    Additional fields are tolerated. When ``check_files`` is true, file entries
    are resolved relative to ``base_dir`` and checked for byte length and hash.
    """

    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    errors: list[str] = []
    for key in ["schema_version", "source", "artifact", "model", "files", "warnings"]:
        if key not in manifest:
            errors.append(f"missing required key: {key}")

    if manifest.get("schema_version") != "0.1":
        errors.append("schema_version must be 0.1")
    if manifest.get("source") != MANIFEST_SOURCE:
        errors.append(f"source must be {MANIFEST_SOURCE}")

    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        errors.append("artifact must be an object")
        artifact = {}
    else:
        if not isinstance(artifact.get("model_id"), str) or not artifact.get("model_id"):
            errors.append("artifact.model_id must be a non-empty string")
        if artifact.get("format") != MANIFEST_FORMAT:
            errors.append(f"artifact.format must be {MANIFEST_FORMAT}")
        if not isinstance(artifact.get("total_bytes"), int) or artifact.get("total_bytes") <= 0:
            errors.append("artifact.total_bytes must be a positive integer")

    model = manifest.get("model")
    if not isinstance(model, dict):
        errors.append("model must be an object")
    else:
        if model.get("architecture") != "qwen_toy":
            errors.append("model.architecture must be qwen_toy for Phase 8 demo artifacts")
        for key in ["hidden_size", "num_layers", "vocab_size"]:
            if not isinstance(model.get(key), int) or model.get(key) <= 0:
                errors.append(f"model.{key} must be a positive integer")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("files must be a non-empty list")
        files = []

    seen_roles: set[str] = set()
    total_bytes = 0
    base = Path(base_dir) if base_dir is not None else None
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            errors.append(f"files[{index}] must be an object")
            continue
        errors.extend(_validate_file_entry(entry, index))
        role = entry.get("role")
        if isinstance(role, str):
            seen_roles.add(role)
        if isinstance(entry.get("byte_length"), int) and entry["byte_length"] > 0:
            total_bytes += int(entry["byte_length"])
        if check_files:
            if base is None:
                errors.append("base_dir is required when check_files is true")
            else:
                errors.extend(_validate_local_file(base, entry, index))

    missing_roles = sorted(REQUIRED_FILE_ROLES - seen_roles)
    if missing_roles:
        errors.append("files missing roles: " + ", ".join(missing_roles))
    if isinstance(artifact.get("total_bytes"), int) and total_bytes and artifact["total_bytes"] != total_bytes:
        errors.append("artifact.total_bytes must equal sum(files[].byte_length)")

    if "warnings" in manifest and not isinstance(manifest["warnings"], list):
        errors.append("warnings must be a list")
    elif isinstance(manifest.get("warnings"), list):
        joined = " ".join(str(item).lower() for item in manifest["warnings"])
        for required in ["toy", "not qwen 9b", "not npu", "not a performance"]:
            if required not in joined:
                errors.append(f"warnings must mention {required}")

    return errors


def _validate_file_entry(entry: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"files[{index}]"
    for key in ["role", "path", "url", "byte_length", "sha256"]:
        if key not in entry:
            errors.append(f"{prefix}: missing required key: {key}")

    if not isinstance(entry.get("role"), str) or not entry.get("role"):
        errors.append(f"{prefix}.role must be a non-empty string")
    if not isinstance(entry.get("path"), str) or not entry.get("path"):
        errors.append(f"{prefix}.path must be a non-empty string")
    elif _is_unsafe_relative_path(entry["path"]):
        errors.append(f"{prefix}.path must be a safe relative path")
    if not isinstance(entry.get("url"), str) or not entry.get("url"):
        errors.append(f"{prefix}.url must be a non-empty string")
    if not isinstance(entry.get("byte_length"), int) or entry.get("byte_length") <= 0:
        errors.append(f"{prefix}.byte_length must be a positive integer")
    if not _is_sha256(entry.get("sha256")):
        errors.append(f"{prefix}.sha256 must be a 64-character hex digest")
    return errors


def _validate_local_file(base_dir: Path, entry: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"files[{index}]"
    path_value = entry.get("path")
    if not isinstance(path_value, str) or _is_unsafe_relative_path(path_value):
        return errors
    path = base_dir / path_value
    if not path.exists() or not path.is_file():
        errors.append(f"{prefix}.path does not exist: {path_value}")
        return errors
    expected_length = entry.get("byte_length")
    if isinstance(expected_length, int) and path.stat().st_size != expected_length:
        errors.append(f"{prefix}.byte_length does not match local file size")
    expected_sha = entry.get("sha256")
    if _is_sha256(expected_sha) and sha256_file(path) != expected_sha:
        errors.append(f"{prefix}.sha256 does not match local file")
    return errors


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_unsafe_relative_path(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts
