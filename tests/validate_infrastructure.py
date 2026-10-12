#!/usr/bin/env python3
"""Validate emerging categories, evidence units, chronology, joins, CSV and reproduction."""

from __future__ import annotations

import copy
import csv
import io
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_infrastructure import SCHEMA, TAG, validate_collection
from location_common import REPO_ROOT as ROOT, sha256
from jsonschema import ValidationError


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    path = ROOT / f"data/infrastructure/connectivity.{TAG}.json"
    collection = read(path)
    validate_collection(collection)
    rows = collection["records"]
    by_id = {row["record_id"]: row for row in rows}
    assert len(rows) == 84 and len(collection["categories"]) == 17
    assert all(row["geometry"] is None and row["spatial_representation"] == "none" for row in rows)
    assert [row["record_id"] for row in rows] == sorted(by_id)
    categories = Counter(row["category"] for row in rows)
    assert categories["network_interconnect_presence"] == 49
    assert categories["satellite_gateway_authorization"] == 7
    assert categories["satellite_network_authorization"] == 9
    assert categories["submarine_cable_system"] == 5 and categories["optical_ground_station"] == 2
    pni = [row for row in rows if row["category"] == "network_interconnect_presence"]
    assert len({row["country_codes"][0] for row in pni}) == 28
    assert all(row["unit"] == "directory_entry" and row["source_updated_at"] == "2026-04-02" for row in pni)
    assert all(row["properties"]["facility_ownership_not_asserted"] and row["properties"]["ground_station_presence_not_asserted"] for row in pni)
    assert sum("Ashburn" in row["name"] for row in pni) == 1
    assert all(row["lifecycle_status"] == "unknown" and row["unit"] == "authorization" for row in rows if row["category"].endswith("authorization"))
    gateways = [row for row in rows if row["category"] == "satellite_gateway_authorization"]
    starlink_gateways = [row for row in gateways if row["properties"]["associated_network_license_number"] == "1239247"]
    assert len(starlink_gateways) == 5
    assert len({row["properties"]["station_locality_label"] for row in gateways}) == 6
    assert "ofcom:satellite_gateway_authorization:1416018" in by_id
    assert by_id["spacex:orbital_compute_constellation:starmind"]["lifecycle_status"] == "planned"
    assert by_id["amazon:direct_to_device_satellite_constellation:amazon-leo-d2d"]["properties"]["completed_acquisition_not_asserted"]
    assert by_id["meta:submarine_cable_system:petal"]["properties"]["planned_ready_for_service_year"] == 2029
    assert by_id["meta:submarine_cable_system:petal"]["lifecycle_status"] == "planned"
    assert by_id["rostelecom:terrestrial_fiber_link:tea-next"]["source_published_at"] == "2026-10-06"
    assert by_id["rostelecom:submarine_cable_system:petropavlovsk-kamchatsky-anadyr"]["properties"]["service_restored_at"] == "2026-07-16"
    assert by_id["starlink:space_situational_awareness_system:stargaze"]["properties"]["sensor_location_scope"] == "onboard_starlink_satellites"
    assert by_id["esa:optical_quantum_network_testbed:6b-128"]["properties"]["includes_real_and_simulated_stations"]
    for row in rows:
        assert row["retrieved_at"] == "2026-10-11"
        for key in ("source_published_at", "source_updated_at"):
            assert row[key] is None or row[key] <= row["retrieved_at"]
        for relation in row["relationships"]:
            assert relation["target_record_id"] in by_id
    report = read(path.with_suffix(".report.json"))
    assert report["canonical_sha256"] == sha256(path)
    assert report["category_counts"] == categories and report["record_count"] == len(rows)
    assert report["starlink_interconnect_metadata"]["article_excluded_countries"] == ["IN"]
    assert any(row["country_codes"] == ["IN"] for row in pni)
    for source in report["sources"]:
        raw = ROOT / source["raw_source_ref"]
        assert source["source_sha256"] == sha256(raw)
        provenance = read(raw.with_suffix(raw.suffix + ".provenance.json"))
        assert provenance["sha256"] == sha256(raw)
    view = read(ROOT / f"data/infrastructure/russia-connectivity.{TAG}.json")
    validate_collection(view)
    assert len(view["records"]) == 3
    assert view["records"] == [row for row in rows if "RU" in row["country_codes"]]
    schema = read(SCHEMA)
    output = subprocess.run(["jq", "-r", "--slurpfile", "schema", str(SCHEMA), "-f", "scripts/infrastructure-json-to-csv.jq", str(path)], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    parsed = csv.DictReader(io.StringIO(output))
    assert parsed.fieldnames == schema["properties"]["records"]["items"]["required"]
    csv_rows = []
    for row in parsed:
        decoded = dict(row)
        for field in ("parties", "country_codes", "relationships", "properties"):
            decoded[field] = json.loads(row[field])
        for field in ("source_published_at", "source_updated_at", "geometry"):
            decoded[field] = row[field] or None
        csv_rows.append(decoded)
    assert csv_rows == rows
    # The schema permits a future category once its meaning is registered.
    future = copy.deepcopy(collection)
    future["categories"]["future_transport_system"] = "A future source-defined transport system."
    future["records"][0]["category"] = "future_transport_system"
    validate_collection(future)
    for defect in ("undefined_category", "duplicate_identity", "unresolved_relation", "invented_geometry"):
        bad = copy.deepcopy(collection)
        if defect == "undefined_category":
            bad["records"][0]["category"] = "not_registered"
        elif defect == "duplicate_identity":
            bad["records"].append(copy.deepcopy(bad["records"][0]))
        elif defect == "unresolved_relation":
            bad["records"][0]["relationships"] = [{"relationship_type": "part_of", "target_record_id": "missing:system:parent"}]
        else:
            bad["records"][0]["geometry"] = {"type": "Point", "coordinates": [181, 95]}
            bad["records"][0]["spatial_representation"] = "provider_point"
        try:
            validate_collection(bad)
        except (ValueError, ValidationError):
            pass
        else:
            raise AssertionError(f"Accepted invalid evidence: {defect}")
    manifest_path = ROOT / f"data/manifest.{TAG}.json"
    manifest = read(manifest_path)
    assert manifest["record_count"] == sum(layer["record_count"] for layer in manifest["layers"])
    assert manifest["network_evidence_record_count"] == sum(layer["record_count"] for layer in manifest["network_evidence_layers"])
    assert manifest["infrastructure_evidence_record_count"] == sum(layer["record_count"] for layer in manifest["infrastructure_evidence_layers"])
    assert next(layer for layer in manifest["infrastructure_evidence_layers"] if layer["layer"] == "infrastructure/connectivity")["record_count"] == 84
    assert manifest["infrastructure_evidence_layers"][0]["unit_counts"] == Counter(row["unit"] for row in rows)
    assert manifest["infrastructure_evidence_views"][0]["record_count"] == 3
    for layer in manifest["infrastructure_evidence_layers"] + manifest["infrastructure_evidence_views"]:
        for artifact in layer["files"].values():
            assert sha256(ROOT / artifact["path"]) == artifact["sha256"]
    with tempfile.TemporaryDirectory(prefix="infrastructure-evidence-") as temp:
        output_root = Path(temp)
        subprocess.run([sys.executable, "-B", "scripts/update_infrastructure.py", "--output-root", temp], cwd=ROOT, check=True, capture_output=True)
        for name in (f"connectivity.{TAG}.json", f"russia-connectivity.{TAG}.json"):
            assert (ROOT / "data/infrastructure" / name).read_bytes() == (output_root / "data/infrastructure" / name).read_bytes()
        regenerated = read(output_root / f"data/infrastructure/connectivity.{TAG}.report.json")
        for key in ("derived_files", "generated_files"):
            regenerated.pop(key)
        expected = copy.deepcopy(report)
        for key in ("derived_files", "generated_files"):
            expected.pop(key)
        assert regenerated == expected
        subprocess.run([sys.executable, "-B", "scripts/build_manifest.py", "--retrieved-at", "2026-10-11", "--output", str(output_root / "manifest.json")], cwd=ROOT, check=True, capture_output=True)
        assert (output_root / "manifest.json").read_bytes() == manifest_path.read_bytes()
    print("Infrastructure validation passed: 84 assertions, 17 extensible categories, source dates, units, licence joins, CSV parity and deterministic reproduction.")


if __name__ == "__main__":
    main()
