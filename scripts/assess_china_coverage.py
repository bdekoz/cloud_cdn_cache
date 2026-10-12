#!/usr/bin/env python3
"""Rebuild the China coverage audit from reviewed source facts and retained layers.

This emits assessment evidence, not new canonical locations. Source facts and
enrichment decisions are reviewed inputs; regional counts and ID diffs are derived.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "20261011"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile(path, role):
    payload = read(ROOT / path)
    rows = payload["features"]
    return {
        "path": path, "sha256": digest(ROOT / path), "role": role,
        "record_count": len(rows),
        "entity_types": dict(sorted(Counter(r["properties"].get("entity_type", "legacy_untyped") for r in rows).items())),
        "geometry_null": sum(r["geometry"] is None for r in rows),
        "retrieval_dates": sorted({r["properties"]["retrieved_at"] for r in rows if "retrieved_at" in r["properties"]}),
        "excluded_from_location_totals": role != "canonical_layer",
    }


def directory_rows(source, vendor):
    rows = []
    scope = "public_cloud"
    parent = None
    prefixes = ("cn-", "ap-", "eu-", "us-", "me-", "na-", "sa-")
    for line in source["facts"]["table_lines"]:
        if "### Alibaba Finance" in line:
            scope = "finance_cloud"
        if "### Alibaba Gov" in line:
            scope = "government_cloud"
        if " | " not in line:
            continue
        cells = [c.strip().replace("`", "") for c in line.split(" | ")]
        zone = cells[-1]
        if not zone.startswith(prefixes):
            continue
        if len(cells) >= 5:
            parent = cells[1]
            current_scope = scope
            if vendor == "tencent":
                current_scope = "specialized_cloud" if parent.endswith(("-fsi", "-adc")) else "public_cloud"
            rows.append({"entity_type": "cloud_region", "source_record_id": parent,
                         "service_scope": current_scope, "source_label": cells[0]})
        if parent is None:
            raise ValueError("Zone has no source-established parent")
        rows.append({"entity_type": "availability_zone", "source_record_id": zone,
                     "parent_source_record_id": parent, "service_scope": current_scope,
                     "source_label": cells[-2].replace("^{*}", "").strip(),
                     "sales_restricted_marked": "*" in cells[-2]})
    ids = [row["source_record_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {vendor} directory identifiers")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / f"data/china/vendor-coverage-assessment.{TAG}.json")
    args = parser.parse_args()
    evidence_path = f"data/china/review-evidence.{TAG}.json"
    plan_path = f"data/china/enrichment-plan.{TAG}.json"
    evidence = read(ROOT / evidence_path)
    sources = {source["source_id"]: source for source in evidence["sources"]}
    plan = read(ROOT / plan_path)
    # This is the pre-enrichment audit. Pin the retained August baseline so later
    # implementation cannot silently rewrite its overlap inventory and counts.
    baseline_manifest = "data/manifest.20260805.json"
    manifest = read(ROOT / baseline_manifest)
    vendors = {"alibaba", "tencent", "huawei", "baidu", "volcano", "tianyi", "kingsoft", "jd", "chindata"}
    datasets = []
    for entry in manifest["layers"] + manifest["views"]:
        if entry["layer"].split("/")[0] in vendors:
            role = "derived_view" if "view_of" in entry else "canonical_layer"
            datasets.append(profile(entry["files"]["geojson"]["path"], role))
    for path, role in [
        ("data/alibaba_cloud_data_centers_2.geojson", "legacy_unreconciled"),
        ("data/tencent_cloud_data_centers.geojson", "legacy_unreconciled"),
        ("data/quarantine/alibaba_cloud_data_centers_3.geojson", "quarantined"),
        ("data/quarantine/baidu_cloud_data_centers_2.geojson", "quarantined"),
    ]:
        datasets.append(profile(path, role))
    diffs = {}
    for vendor in ["alibaba", "tencent"]:
        key = f"{vendor}-directory"
        current = directory_rows(sources[key], vendor)
        baseline_path = f"data/{vendor}/regions-and-zones.20260804.geojson"
        baseline = read(ROOT / baseline_path)["features"]
        old_ids = {r["properties"]["source_record_id"] for r in baseline}
        new_ids = {r["source_record_id"] for r in current}
        scopes = {}
        for scope in sorted({r["service_scope"] for r in current}):
            scoped = [r for r in current if r["service_scope"] == scope]
            scopes[scope] = dict(sorted(Counter(r["entity_type"] for r in scoped).items()))
        diffs[vendor] = {
            "source_id": key, "baseline_path": baseline_path,
            "baseline_record_count": len(baseline), "reviewed_directory_record_count": len(current),
            "entity_types": dict(sorted(Counter(r["entity_type"] for r in current).items())),
            "scopes": scopes, "added_ids": sorted(new_ids - old_ids),
            "ids_not_listed_in_reviewed_source": sorted(old_ids - new_ids),
            "missing_listing_is_not_retirement_proof": True,
            "reviewed_directory_rows": current,
            "canonical_layer_updated": False,
        }
    cn_partitions = {}
    for vendor, layer in [("aws", "regions-and-zones"), ("microsoft", "cloud-regions")]:
        path = f"data/{vendor}/{layer}.20260805.geojson"
        rows = [r["properties"] for r in read(ROOT / path)["features"] if r["properties"]["country_code"] == "CN"]
        cn_partitions[vendor] = {"path": path, "sha256": digest(ROOT / path), "china_record_count": len(rows),
                                 "entity_types": dict(sorted(Counter(r["entity_type"] for r in rows).items())),
                                 "source_record_ids": sorted(r["source_record_id"] for r in rows)}
    for vendor in plan["vendors"]:
        for source_id in vendor["reviewed_source_ids"]:
            if source_id not in sources:
                raise ValueError(source_id)
    payload = {
        "assessment_date": "2026-10-11", "type": "ChinaVendorCoverageAssessment",
        "scope": "China-based cloud/platform/model vendors, overseas services, non-China requested platforms, and unresolved identities; coverage cohort, not a market-share ranking.",
        "inputs": [{"path": p, "sha256": digest(ROOT / p)} for p in [evidence_path, plan_path, baseline_manifest]],
        "source_count": len(sources), "sources": list(sources.values()),
        "datasets": datasets, "directory_comparisons": diffs,
        "foreign_hyperscaler_china_partitions": cn_partitions,
        "vendors": plan["vendors"], "enrichment_plan": plan["phases"],
        "cross_source_rules": plan["cross_source_rules"],
        "coverage_gaps": plan["coverage_gaps"],
        "canonical_location_records_generated": 0,
        "assessment_rows_are_not_physical_sites": True,
        "limitations": [
            "Review facts are provider/filing declarations or indexed first-party extracts; no active network measurements or independent capacity inventory.",
            "Search-index extracts can be stale; capture_method and source dates are retained. Source-specific retrieval failures remain explicit.",
            "The review does not establish GPU stock, training-cluster ownership, facility coordinates, or a complete vendor universe.",
            "Canonical August layers are not refreshed by this assessment. Missing rows remain enrichment candidates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"vendor_count": len(plan["vendors"]), "source_count": len(sources),
                      "canonical_locations_added": 0, "directory_counts": {v: d["entity_types"] for v, d in diffs.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
