#!/usr/bin/env python3
"""Validate China audit provenance, dataset overlap, source joins and ID extraction."""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_china_coverage import directory_rows


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    path = "data/china/vendor-coverage-assessment.20261011.json"
    audit = read(path)
    sources = {row["source_id"]: row for row in audit["sources"]}
    assert len(sources) == audit["source_count"]
    assert len({v["vendor_id"] for v in audit["vendors"]}) == len(audit["vendors"])
    for entry in audit["inputs"] + audit["datasets"]:
        assert sha(entry["path"]) == entry["sha256"]
    for vendor in audit["vendors"]:
        assert set(vendor["reviewed_source_ids"]) <= sources.keys()
    for gap in audit["coverage_gaps"]:
        assert set(gap["evidence_source_ids"]) <= sources.keys()
    for vendor, diff in audit["directory_comparisons"].items():
        # Independently extract all provider tokens from retained table cells;
        # comparison catches skipped rows, accidental ID synthesis or scope drift.
        lines = sources[diff["source_id"]]["facts"]["table_lines"]
        tokens = set(re.findall(r"(?:cn|ap|eu|us|me|na|sa)-[a-z0-9-]+", "\n".join(lines)))
        rows = diff["reviewed_directory_rows"]
        ids = {r["source_record_id"] for r in rows}
        assert ids == tokens
        assert len(ids) == len(rows) == diff["reviewed_directory_record_count"]
        old = {r["properties"]["source_record_id"] for r in read(diff["baseline_path"])["features"]}
        assert set(diff["added_ids"]) == ids - old
        assert set(diff["ids_not_listed_in_reviewed_source"]) == old - ids
        regions = {r["source_record_id"]: r for r in rows if r["entity_type"] == "cloud_region"}
        for row in rows:
            if row["entity_type"] == "availability_zone":
                parent = regions[row["parent_source_record_id"]]
                assert parent["service_scope"] == row["service_scope"]
        # An orphan zone is a malformed source and must fail rather than inherit
        # an invented parent or be silently skipped.
        try:
            directory_rows({"facts": {"table_lines": ["Orphan Zone | ap-test-1"]}}, vendor)
        except ValueError:
            pass
        else:
            raise AssertionError("Orphan zone accepted")
    manifest = read("data/manifest.20261011.json")
    layer_ids = {}
    for layer in manifest["layers"]:
        layer_ids[layer["layer"]] = {r["properties"]["record_id"] for r in read(layer["files"]["geojson"]["path"])["features"]}
    for view in manifest["views"]:
        if isinstance(view["view_of"], str):
            ids = {r["properties"]["record_id"] for r in read(view["files"]["geojson"]["path"])["features"]}
            assert ids <= layer_ids[view["view_of"]]
    assert audit["canonical_location_records_generated"] == 0
    assert all(d["excluded_from_location_totals"] for d in audit["datasets"] if d["role"] != "canonical_layer")
    for entry in manifest["assessments"]:
        assert sha(entry["path"]) == entry["sha256"]
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "audit.json"
        subprocess.run([sys.executable, "-B", "scripts/assess_china_coverage.py", "--output", str(output)], cwd=ROOT, check=True, capture_output=True)
        assert output.read_bytes() == (ROOT / path).read_bytes()
    print("China coverage review: provenance, source IDs, scope/parent joins, views and reproduction valid")


if __name__ == "__main__":
    main()
