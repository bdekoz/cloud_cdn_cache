#!/usr/bin/env python3
"""Build a consolidated manifest without relabeling older retained snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, SCHEMA_CONTRACT_VERSION, SCHEMA_PATH, repo_ref, retrieval_tag, sha256, write_json


BASELINE_TAG = "20260804"
HYPERSCALER_TAG = "20260805"

BASELINE_LAYERS = (
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
    "baidu/regions-and-zones",
    "huawei/mainland-regions",
    "volcano/regions-and-zones",
    "kingsoft/mainland-regions-and-zones",
    "jd/mainland-regions-and-zones",
    "tianyi/vpc-resource-pools",
    "chindata/data-centers",
    "observations/cdn-mapping",
)

HYPERSCALER_LAYERS = (
    "coreweave/regions-and-zones",
    "aws/regions-and-zones",
    "google/cloud-regions-and-zones",
    "microsoft/cloud-regions",
    "oracle/cloud-regions",
    "ibm/regions-and-zones",
    "ibm/classic-data-centers",
    "meta/data-centers",
)

VIEW_NAMES = {
    "alibaba/mainland-regions-and-zones": "alibaba/regions-and-zones",
    "tencent/mainland-regions-and-zones": "tencent/regions-and-zones",
    "tencent/mainland-specialized-regions-and-zones": "tencent/regions-and-zones",
    "baidu/mainland-regions-and-zones": "baidu/regions-and-zones",
    "volcano/mainland-regions-and-zones": "volcano/regions-and-zones",
}

ASSESSMENT_NAMES = (
    "china/provider-assessment",
    "china-edge/provider-assessment",
    "china-colocation/operator-assessment",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def layer_manifest(layer: str, tag: str) -> dict[str, Any]:
    base = REPO_ROOT / "data" / f"{layer}.{tag}"
    csv_path = Path(f"{base}.csv")
    geojson_path = Path(f"{base}.geojson")
    report_path = Path(f"{base}.report.json")
    collection = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = collection["features"]
    rows = [feature["properties"] for feature in features]
    sources = {}
    for row in rows:
        key = (row["raw_source_ref"], row["source_sha256"], row["source_url"])
        sources[key] = {
            "raw_source_ref": key[0],
            "sha256": key[1],
            "source_url": key[2],
            "source_published_at": row["source_published_at"],
        }
    return {
        "coordinate_methods": dict(sorted(Counter(row["coordinate_method"] for row in rows).items())),
        "derived_files": {
            "csv": {
                "generator": f"make {repo_ref(csv_path)}",
                "path": repo_ref(csv_path),
                "source": repo_ref(geojson_path),
            }
        },
        "entity_types": dict(sorted(Counter(row["entity_type"] for row in rows).items())),
        "files": {
            "geojson": {"path": repo_ref(geojson_path), "sha256": sha256(geojson_path)},
            "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)},
        },
        "geometry_null": sum(feature["geometry"] is None for feature in features),
        "layer": layer,
        "providers": sorted({row["provider"] for row in rows}),
        "record_count": len(rows),
        "snapshot_tag": tag,
        "retrieved_at": sorted({row["retrieved_at"] for row in rows}),
        "schema_versions": sorted({row["schema_version"] for row in rows}),
        "services": sorted({row["service"] for row in rows}),
        "source_scopes": sorted({row["source_scope"] for row in rows}),
        "sources": sorted(sources.values(), key=lambda source: source["raw_source_ref"]),
    }


def assessment_manifest(name: str, tag: str) -> dict[str, str]:
    path = REPO_ROOT / "data" / f"{name}.{tag}.json"
    return {"path": repo_ref(path), "sha256": sha256(path)}


def main() -> None:
    args = parse_args()
    tag = retrieval_tag(args.retrieved_at)
    output = args.output or REPO_ROOT / "data" / f"manifest.{tag}.json"
    if tag < BASELINE_TAG:
        raise ValueError(f"no consolidated snapshot is defined before {BASELINE_TAG}")
    layer_specs = [(layer, BASELINE_TAG) for layer in BASELINE_LAYERS]
    if tag >= HYPERSCALER_TAG:
        layer_specs.extend((layer, HYPERSCALER_TAG) for layer in HYPERSCALER_LAYERS)
    layers = [layer_manifest(layer, snapshot_tag) for layer, snapshot_tag in layer_specs]
    views = []
    for view, parent in VIEW_NAMES.items():
        entry = layer_manifest(view, BASELINE_TAG)
        entry["view_of"] = parent
        views.append(entry)
    quarantine_audit = REPO_ROOT / "data/quarantine/audit.20260804.json"
    write_json(output, {
        "assessments": [assessment_manifest(name, BASELINE_TAG) for name in ASSESSMENT_NAMES],
        "generated_from_retained_snapshots_at": args.retrieved_at,
        "layer_count": len(layers),
        "layers": layers,
        "record_count": sum(layer["record_count"] for layer in layers),
        "schema": {"path": repo_ref(SCHEMA_PATH), "sha256": sha256(SCHEMA_PATH), "version": SCHEMA_CONTRACT_VERSION},
        "scope_note": "Canonical counts span unlike provider-declared and observed entity types and are not a physical-site total. Derived views repeat source-layer IDs and are excluded from record_count.",
        "quarantine": {"audit_path": repo_ref(quarantine_audit), "audit_sha256": sha256(quarantine_audit)},
        "view_count": len(views),
        "views": views,
    })
    print(json.dumps({"layer_count": len(layers), "record_count": sum(layer["record_count"] for layer in layers), "view_count": len(views), "output": repo_ref(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
