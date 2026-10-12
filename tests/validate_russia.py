#!/usr/bin/env python3
"""Validate Russia view boundaries, Yandex identities, claims, provenance, and reproduction."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from validate_google import derive_csv_records, geojson_records, schema_validator, sha256, validate_records

ROOT = Path(__file__).resolve().parents[1]
TAG = "20261011"


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def main() -> None:
    yandex_path = ROOT / f"data/yandex/data-centers.{TAG}.geojson"
    rows = geojson_records(yandex_path)
    validate_records(rows, schema_validator())
    assert derive_csv_records(yandex_path) == rows
    assert {row["city"] for row in rows} == {"Kaluga", "Vladimir", "Sasovo", "Mytishchi", "Ivanteevka"}
    assert len(rows) == 5
    for row in rows:
        assert row["country_code"] == "RU" and row["service"] == "yandex_data_centers"
        assert row["lifecycle_status"] == "unknown" and row["source_scope"] == "provider_declared"
        assert row["latitude"] is row["longitude"] is row["coordinate_crs"] is None
        assert row["properties"]["capacity_mw"] is None
        assert row["source_sha256"] == sha256(ROOT / row["raw_source_ref"])
        assert row["properties"]["historical_identity_only"] == (row["city"] == "Ivanteevka")
        assert row["source_published_at"] == ("2023-09-28" if row["city"] == "Ivanteevka" else "2025-10-23")
    reports = {row["city"]: row["properties"].get("provider_operational_report") for row in rows}
    assert reports["Sasovo"]["status"] == reports["Vladimir"]["status"] == "temporarily_stopped"
    assert reports["Kaluga"]["status"] == "partially_disrupted"
    assert reports["Ivanteevka"] is reports["Mytishchi"] is None
    audit = read(f"data/yandex/image-claim-review.{TAG}.json")
    assert len(audit["cards"]) == audit["image_card_count"] == 9
    assert audit["capacity_claims_verified"] == 0 and audit["facility_photos_authenticated"] is False
    matched = {card["matched_record_id"] for card in audit["cards"] if card["matched_record_id"]}
    assert matched == {row["record_id"] for row in rows}
    assert sum(card["matched_record_id"] is None for card in audit["cards"]) == 4
    assert audit["source_image"]["source_sha256"] == sha256(ROOT / audit["source_image"]["raw_source_ref"])
    assessment = read(f"data/russia/provider-assessment.{TAG}.json")
    assert assessment["baseline_layer_counts"] == {
        "google/edge": 2, "cloudflare/edge": 3, "cachefly/locations": 2, "observations/cdn-mapping-cities": 79,
    }
    assert len(assessment["provider_review"]) == 9
    assert assessment["edge_rechecks"]["Cloudflare"]["retained_code_missing_from_returned_feed"] == "KJA"
    returned_components = assessment["edge_rechecks"]["Cloudflare"]["russian_components"]
    assert len(returned_components) == 2 and all("KJA" not in row["name"] for row in returned_components)
    assert assessment["edge_rechecks"]["Cloudflare"]["page_updated_at"].startswith("2026-08-27")
    view_path = ROOT / f"data/russia/locations-and-observations.{TAG}.geojson"
    view = geojson_records(view_path)
    validate_records(view, schema_validator())
    assert derive_csv_records(view_path) == view
    assert len(view) == 91
    assert all(row["country_code"] == "RU" for row in view)
    assert Counter(row["entity_type"] for row in view) == {"edge_pop": 7, "observed_presence": 79, "data_center": 5}
    manifest = read(f"data/manifest.{TAG}.json")
    assert manifest["record_count"] == sum(layer["record_count"] for layer in manifest["layers"]) == 27395
    assert manifest["layer_count"] == 29 and manifest["view_count"] == 6
    assert next(layer for layer in manifest["layers"] if layer["layer"] == "yandex/data-centers")["record_count"] == 5
    view_entry = next(entry for entry in manifest["views"] if entry["layer"] == "russia/locations-and-observations")
    assert view_entry["record_count"] == 91
    assert set(view_entry["view_of"]) == set(assessment["baseline_layer_counts"]) | {"yandex/data-centers"}
    source_rows = {}
    for layer in manifest["layers"]:
        for row in geojson_records(ROOT / layer["files"]["geojson"]["path"]):
            assert row["record_id"] not in source_rows, row["record_id"]
            source_rows[row["record_id"]] = row
        for file in layer["files"].values():
            assert sha256(ROOT / file["path"]) == file["sha256"]
    assert all(row == source_rows[row["record_id"]] for row in view)
    for family in ("russia", "yandex"):
        for sidecar in (ROOT / f"data/raw/{family}").glob("*.provenance.json"):
            provenance = json.loads(sidecar.read_text())
            assert provenance["sha256"] == sha256(ROOT / provenance["raw_source_ref"])
    for entry in manifest["assessments"]:
        assert sha256(ROOT / entry["path"]) == entry["sha256"]
    for file in view_entry["files"].values():
        assert sha256(ROOT / file["path"]) == file["sha256"]
    with tempfile.TemporaryDirectory(prefix="russia-review-") as temp:
        output_root = Path(temp)
        subprocess.run([sys.executable, "-B", "scripts/update_russia.py", "--output-root", temp], cwd=ROOT, check=True, capture_output=True)
        for name in (f"yandex/data-centers.{TAG}.geojson", f"yandex/image-claim-review.{TAG}.json",
                     f"russia/locations-and-observations.{TAG}.geojson", f"russia/provider-assessment.{TAG}.json"):
            assert (ROOT / "data" / name).read_bytes() == (output_root / "data" / name).read_bytes(), name
        assert not list(output_root.rglob("*.csv"))
    print("Russia validation passed: 5 Yandex localities; 9 reviewed provider surfaces; 91-row derived view; unverified image claims excluded.")


if __name__ == "__main__":
    main()
