#!/usr/bin/env python
"""Create a tiny externally deliverable QPNPU toy model artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from qpnpu.model_artifact import (  # noqa: E402
    MANIFEST_FORMAT,
    MANIFEST_SOURCE,
    sha256_file,
    validate_external_model_manifest,
    write_external_model_manifest,
)
from qpnpu.toy_model import create_toy_model  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output artifact directory.")
    parser.add_argument("--base-url", default="", help="Optional base URL for generated manifest file URLs.")
    parser.add_argument("--hidden-size", type=int, default=16)
    parser.add_argument("--vocab-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        if not args.overwrite:
            print(f"error: refusing to overwrite existing artifact directory: {out}", file=sys.stderr)
            return 2
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    metadata = create_toy_model(
        out,
        {
            "hidden_size": args.hidden_size,
            "vocab_size": args.vocab_size,
            "seed": args.seed,
        },
        overwrite=True,
    )

    shards_dir = out / "shards"
    shards_dir.mkdir(exist_ok=True)
    tensor_shard = shards_dir / "model-00000.qpnpu"
    (out / "model.bin").replace(tensor_shard)
    for tensor in metadata["tensors"]:
        tensor["file"] = "shards/model-00000.qpnpu"
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = _build_manifest(out, metadata, args.base_url)
    errors = validate_external_model_manifest(manifest, base_dir=out, check_files=True)
    if errors:
        print("error: generated manifest did not validate:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    manifest_path = write_external_model_manifest(out / "manifest.json", manifest)

    total_bytes = manifest["artifact"]["total_bytes"]
    print(f"wrote external toy artifact: {out}")
    print(f"wrote manifest: {manifest_path}")
    print(f"artifact bytes: {total_bytes}")
    print("warning: tiny external toy model only; not Qwen 9B, not NPU, not a performance claim")
    return 0


def _build_manifest(out: Path, metadata: dict, base_url: str) -> dict:
    files = []
    for role, path in [
        ("metadata", "metadata.json"),
        ("tokenizer_stub", "tokenizer_stub.json"),
        ("tensor_shard", "shards/model-00000.qpnpu"),
    ]:
        file_path = out / path
        files.append(
            {
                "role": role,
                "path": path,
                "url": _join_url(base_url, path) if base_url else path,
                "byte_length": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
        )

    total_bytes = sum(item["byte_length"] for item in files)
    return {
        "schema_version": "0.1",
        "source": MANIFEST_SOURCE,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "artifact": {
            "model_id": "toy-qwen-external-smoke",
            "format": MANIFEST_FORMAT,
            "total_bytes": total_bytes,
            "file_count": len(files),
        },
        "model": metadata["model"],
        "files": files,
        "decode_smoke": {
            "prompt": "hello",
            "max_new_tokens": 8,
        },
        "warnings": [
            "external toy model delivery demo only",
            "toy model only; not Qwen 9B",
            "not NPU, QNN, NNAPI, or Vulkan execution",
            "not a performance claim",
        ],
    }


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
