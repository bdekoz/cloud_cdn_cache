#!/usr/bin/env python3
"""Build the consolidated manifest for normalized 2026-08-04 layers."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, SCHEMA_PATH, repo_ref, retrieval_tag, sha256, write_json


LAYER_NAMES = (
    "google/edge",
    "google/data-centers",
    "cloudflare/edge",
    "microsoft/front-door",
    "microsoft/front-door-codes",
    "aws/cloudfront",
    "aws/local-zones",
    "fastly/pops",
    "cachefly/locations",
    "alibaba/regions-and-zones",
    "tencent/regions-and-zones",
    "observations/cdn-mapping",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def optional(value: str) -> str | None:
    return value or None


def layer_manifest(layer: str, tag: str) -> dict[str, Any]:
    base = REPO_ROOT / "data" / f"{layer}.{tag}"
    csv_path = Path(f"{base}.csv")
    geojson_path = Path(f"{base}.geojson")
    report_path = Path(f"{base}.report.json")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    sources = {}
    for row in rows:
        key = (row["raw_source_ref"], row["source_sha256"], row["source_url"])
        sources[key] = {
            "raw_source_ref": key[0],
            "sha256": key[1],
            "source_url": key[2],
            "source_published_at": optional(row["source_published_at"]),
        }
    return {
        "coordinate_methods": dict(sorted(Counter(row["coordinate_method"] for row in rows).items())),
        "entity_types": dict(sorted(Counter(row["entity_type"] for row in rows).items())),
        "files": {
            "csv": {"path": repo_ref(csv_path), "sha256": sha256(csv_path)},
            "geojson": {"path": repo_ref(geojson_path), "sha256": sha256(geojson_path)},
            "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)},
        },
        "geometry_null": sum(not row["latitude"] for row in rows),
        "layer": layer,
        "providers": sorted({row["provider"] for row in rows}),
        "record_count": len(rows),
        "retrieved_at": sorted({row["retrieved_at"] for row in rows}),
        "schema_versions": sorted({row["schema_version"] for row in rows}),
        "services": sorted({row["service"] for row in rows}),
        "source_scopes": sorted({row["source_scope"] for row in rows}),
        "sources": sorted(sources.values(), key=lambda source: source["raw_source_ref"]),
    }


def main() -> None:
    args = parse_args()
    tag = retrieval_tag(args.retrieved_at)
    output = args.output or REPO_ROOT / "data" / f"manifest.{tag}.json"
    layers = [layer_manifest(layer, tag) for layer in LAYER_NAMES]
    quarantine_audit = REPO_ROOT / "data/quarantine/audit.20260804.json"
    write_json(output, {
        "generated_from_retained_snapshots_at": args.retrieved_at,
        "layer_count": len(layers),
        "layers": layers,
        "record_count": sum(layer["record_count"] for layer in layers),
        "schema": {"path": repo_ref(SCHEMA_PATH), "sha256": sha256(SCHEMA_PATH), "version": "1.0.0"},
        "scope_note": "Counts span unlike provider-declared and observed entity types and are not a physical-site total.",
        "quarantine": {"audit_path": repo_ref(quarantine_audit), "audit_sha256": sha256(quarantine_audit)},
    })
    print(json.dumps({"layer_count": len(layers), "record_count": sum(layer["record_count"] for layer in layers), "output": repo_ref(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
