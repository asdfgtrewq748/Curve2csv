"""Generate a split and merge its hashes into the dataset manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from benchmarks.generator.render import render_sample
from benchmarks.generator.spec import GLOBAL_SEED, make_spec


def _load_config(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid config: {path}")
    return payload


def generate_split(
    config: dict[str, object], split: str, out_root: Path, manifest_path: Path
) -> list[dict[str, object]]:
    splits = config.get("splits")
    if not isinstance(splits, dict) or split not in splits:
        raise SystemExit(f"unknown split {split}")
    count = int(splits[split])
    global_seed = int(config.get("global_seed", GLOBAL_SEED))
    entries: list[dict[str, object]] = []
    for index in range(count):
        spec = make_spec(split, index, global_seed)
        sample_dir = out_root / split / f"{index:05d}"
        document = render_sample(spec, sample_dir)
        entries.append(
            {
                "split": split,
                "index": index,
                "id": document["id"],
                "sha256": document["sha256"],
                "spec_seed": spec.spec_seed,
                "chart_type": spec.chart_type,
                "degradation": spec.degradation,
                "series_bucket": spec.series_bucket,
                "color_mode": spec.color_mode,
                "domain_shape": spec.shape,
            }
        )
        if (index + 1) % 50 == 0 or index + 1 == count:
            print(f"generated {split} {index + 1}/{count}", flush=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "dataset_version": config.get("dataset_version", "synth-v0.1"),
            "global_seed": global_seed,
            "samples": [],
        }
    kept = [
        row
        for row in manifest.get("samples", [])
        if isinstance(row, dict) and row.get("split") != split
    ]
    manifest["samples"] = kept + entries
    manifest["dataset_version"] = config.get("dataset_version", "synth-v0.1")
    manifest["global_seed"] = global_seed
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return entries


def verify_split(
    config: dict[str, object], split: str, out_root: Path, manifest_path: Path
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        int(row["index"]): str(row["sha256"])
        for row in manifest["samples"]
        if row.get("split") == split
    }
    splits = config["splits"]
    assert isinstance(splits, dict)
    count = int(splits[split])
    if len(expected) != count:
        raise SystemExit(f"manifest has {len(expected)} {split} rows, config wants {count}")
    mismatches = 0
    for index in range(count):
        path = out_root / split / f"{index:05d}" / "img.png"
        import hashlib

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected.get(index) != digest:
            mismatches += 1
            print(f"hash mismatch {split} {index}")
    if mismatches:
        raise SystemExit(f"{mismatches} hash mismatches in {split}")
    print(f"manifest hashes ok for {split} ({count})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="benchmarks.generator.cli")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path, default=Path("benchmarks/manifest/synth-v0.1.json")
    )
    parser.add_argument(
        "--verify", action="store_true", help="check img.png hashes against the manifest"
    )
    args = parser.parse_args(argv)
    config = _load_config(args.config)
    if args.verify:
        verify_split(config, args.split, args.out, args.manifest)
        return
    generate_split(config, args.split, args.out, args.manifest)


if __name__ == "__main__":
    main()
