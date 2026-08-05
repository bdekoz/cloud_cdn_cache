#!/usr/bin/env python3
"""Validate hyperscaler hierarchy/facility layers and mixed-date publication."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
TAG = "20260805"
LAYERS = {
    "coreweave/regions-and-zones": 63,
    "aws/regions-and-zones": 147,
    "google/cloud-regions-and-zones": 173,
    "microsoft/cloud-regions": 57,
    "oracle/cloud-regions": 45,
    "ibm/regions-and-zones": 53,
    "ibm/classic-data-centers": 42,
    "meta/data-centers": 33,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_from_feature(feature: dict[str, Any]) -> dict[str, Any]:
    record = dict(feature["properties"])
    geometry = feature["geometry"]
    if geometry is None:
        record["latitude"] = None
        record["longitude"] = None
    else:
        record["longitude"], record["latitude"] = geometry["coordinates"]
    return record


def records(layer: str) -> list[dict[str, Any]]:
    payload = json.loads((ROOT / "data" / f"{layer}.{TAG}.geojson").read_text(encoding="utf-8"))
    return [canonical_from_feature(feature) for feature in payload["features"]]


def derive_csv(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "jq", "-r", "--slurpfile", "schema", str(ROOT / "schema/location.schema.json"),
            "-f", str(ROOT / "scripts/geojson-to-csv.jq"), str(path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    assert reader.fieldnames == schema["required"]
    output: list[dict[str, Any]] = []
    for row in reader:
        record: dict[str, Any] = dict(row)
        for field in ("aliases", "service_scope", "properties"):
            record[field] = json.loads(row[field])
        for field in ("latitude", "longitude"):
            record[field] = float(row[field]) if row[field] else None
        for field, definition in schema["properties"].items():
            field_type = definition.get("type")
            if isinstance(field_type, list) and "null" in field_type and not row[field]:
                record[field] = None
        output.append(record)
    return output


def validate_layers() -> dict[str, list[dict[str, Any]]]:
    schema = json.loads((ROOT / "schema/location.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    by_layer: dict[str, list[dict[str, Any]]] = {}
    all_ids: set[str] = set()
    for layer, expected_count in LAYERS.items():
        layer_records = records(layer)
        by_layer[layer] = layer_records
        report = json.loads((ROOT / "data" / f"{layer}.{TAG}.report.json").read_text(encoding="utf-8"))
        geojson_path = f"data/{layer}.{TAG}.geojson"
        csv_path = f"data/{layer}.{TAG}.csv"
        assert len(layer_records) == expected_count == report["record_count"], layer
        assert report["schema_version"] == "1.2.0"
        assert report["geometry_null"] == expected_count
        assert report["generated_files"] == [geojson_path]
        assert report["derived_files"]["csv"] == {
            "generator": f"make {csv_path}", "path": csv_path, "source": geojson_path,
        }
        ids = [record["record_id"] for record in layer_records]
        assert ids == sorted(ids), layer
        assert len(ids) == len(set(ids)), layer
        assert not all_ids.intersection(ids), f"cross-layer ID collision in {layer}"
        all_ids.update(ids)
        assert derive_csv(ROOT / geojson_path, schema) == layer_records, layer
        for record in layer_records:
            errors = list(validator.iter_errors(record))
            assert not errors, f"{layer}: {record['record_id']}: {errors[0].message if errors else ''}"
            assert record["schema_version"] == "1.2.0"
            assert record["latitude"] is record["longitude"] is record["coordinate_crs"] is None
    for layer_records in by_layer.values():
        for record in layer_records:
            if record["parent_record_id"]:
                assert record["parent_record_id"] in all_ids, record["record_id"]
    return by_layer


def validate_coreweave(by_layer: dict[str, list[dict[str, Any]]]) -> None:
    layer = by_layer["coreweave/regions-and-zones"]
    zones = [row for row in layer if row["entity_type"] == "availability_zone"]
    supers = [row for row in layer if row["entity_type"] == "super_region"]
    assert len(supers) == 7 and len(zones) == 56
    assert Counter(row["access_status"] for row in zones) == Counter({"dedicated": 38, "public": 18})
    assert sum(row["properties"]["ai_object_storage"] for row in zones) == 25
    assert all(row["parent_record_id"] in {parent["record_id"] for parent in supers} for row in zones)
    general = [row for row in zones if row["access_status"] == "public"]
    assert all("gpu_instance_types" in row["properties"] and "cpu_instance_types" in row["properties"] for row in general)
    report = json.loads((ROOT / "data/coreweave/regions-and-zones.20260805.report.json").read_text())
    assert report["product_matrix_zone_count"] == 18


def validate_aws(by_layer: dict[str, list[dict[str, Any]]]) -> None:
    layer = by_layer["aws/regions-and-zones"]
    regions = [row for row in layer if row["entity_type"] == "cloud_region"]
    zones = [row for row in layer if row["entity_type"] == "availability_zone"]
    assert len(regions) == 39 and len(zones) == 108
    assert Counter(row["properties"]["partition"] for row in regions) == Counter({"aws": 34, "aws-cn": 2, "aws-us-gov": 2, "aws-eusc": 1})
    assert all(row["properties"]["az_id_is_account_stable"] for row in zones)
    assert {row["access_status"] for row in regions if row["properties"]["partition"] in {"aws-cn", "aws-us-gov"}} == {"restricted"}
    eusc = next(row for row in regions if row["source_record_id"] == "eusc-de-east-1")
    assert eusc["access_status"] == "public" and eusc["properties"]["realm"] == "sovereign"
    report = json.loads((ROOT / "data/aws/regions-and-zones.20260805.report.json").read_text())
    assert report["aggregate_availability_zone_count"] == 123
    assert report["unitemized_availability_zone_gap"] == 15
    local_zones = json.loads(
        (ROOT / "data/aws/local-zones.20260804.geojson").read_text(encoding="utf-8")
    )["features"]
    region_ids = {row["record_id"] for row in regions}
    assert len(local_zones) == 45
    assert all(feature["properties"]["parent_record_id"] in region_ids for feature in local_zones)


def validate_google_azure_oci(by_layer: dict[str, list[dict[str, Any]]]) -> None:
    google = by_layer["google/cloud-regions-and-zones"]
    assert Counter(row["entity_type"] for row in google) == Counter({"availability_zone": 130, "cloud_region": 43})
    assert all(row["country_code"] for row in google)
    google_zones = [row for row in google if row["entity_type"] == "availability_zone"]
    assert all(isinstance(row["properties"]["machine_types"], list) for row in google_zones)
    assert any(row["properties"]["low_co2"] for row in google_zones)

    azure = by_layer["microsoft/cloud-regions"]
    assert len(azure) == 57 and {row["entity_type"] for row in azure} == {"cloud_region"}
    assert sum(row["access_status"] == "restricted" for row in azure) == 8
    assert sum(row["properties"]["availability_zone_support"] for row in azure) == 39
    assert all(not row["properties"]["synthetic_availability_zones_generated"] for row in azure)

    oci = by_layer["oracle/cloud-regions"]
    assert len(oci) == 45 and {row["entity_type"] for row in oci} == {"cloud_region"}
    assert all(row["properties"]["availability_domain_records_generated"] == 0 for row in oci)
    assert all(row["properties"]["tenancy_specific_availability_domain_names"] for row in oci)
    assert Counter(row["properties"]["availability_domain_count"] for row in oci) == Counter({1: 40, 3: 5})


def validate_ibm_meta(by_layer: dict[str, list[dict[str, Any]]]) -> None:
    ibm = by_layer["ibm/regions-and-zones"]
    regions = [row for row in ibm if row["entity_type"] == "cloud_region"]
    zones = [row for row in ibm if row["entity_type"] == "availability_zone"]
    assert len(regions) == 13 and len(zones) == 40
    logical_labels = [label for row in regions for label in row["properties"]["account_logical_zone_labels"]]
    assert len(logical_labels) == 39
    assert not {f"ibm:availability_zone:{slug}" for slug in logical_labels}.intersection({row["record_id"] for row in zones})
    assert sum(row["parent_record_id"] == "ibm:cloud_region:us-south" for row in zones) == 4

    classic = by_layer["ibm/classic-data-centers"]
    che = next(row for row in classic if row["site_code"] == "CHE01")
    assert che["lifecycle_status"] == "operational"
    assert che["access_status"] == "sales_restricted"
    assert che["properties"]["closure_date"] == "2027-06-10"
    assert {row["site_code"] for row in classic if row["access_status"] == "restricted"} == {"DAL08", "WDC03"}

    meta = by_layer["meta/data-centers"]
    assert len(meta) == 33
    assert all(row["lifecycle_status"] == "unknown" for row in meta)
    assert all(row["properties"]["lifecycle_not_inferred_from_break_ground_year"] for row in meta)
    assert all(row["properties"]["break_ground_year"] for row in meta)
    assert Counter(row["country_code"] for row in meta) == Counter({"US": 28, "CA": 1, "DK": 1, "IE": 1, "SE": 1, "SG": 1})


def validate_manifest() -> None:
    manifest = json.loads((ROOT / "data/manifest.20260805.json").read_text(encoding="utf-8"))
    assert manifest["layer_count"] == 27
    assert manifest["record_count"] == 15726
    assert manifest["view_count"] == 5
    assert manifest["schema"]["version"] == "1.2.0"
    assert manifest["schema"]["sha256"] == digest(ROOT / manifest["schema"]["path"])
    by_name = {layer["layer"]: layer for layer in manifest["layers"]}
    assert set(LAYERS) <= set(by_name)
    assert all(by_name[name]["snapshot_tag"] == TAG for name in LAYERS)
    assert all(layer["snapshot_tag"] == "20260804" for name, layer in by_name.items() if name not in LAYERS)
    assert {version for layer in manifest["layers"] for version in layer["schema_versions"]} == {"1.1.0", "1.2.0"}
    for layer in manifest["layers"] + manifest["views"]:
        for file_record in layer["files"].values():
            assert digest(ROOT / file_record["path"]) == file_record["sha256"]


def validate_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="hyperscaler-refresh-") as temp:
        output_root = Path(temp)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_hyperscalers.py"),
            "--retrieved-at", "2026-08-05", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        for layer in LAYERS:
            checked_in = ROOT / "data" / f"{layer}.{TAG}.geojson"
            regenerated = output_root / "data" / f"{layer}.{TAG}.geojson"
            assert checked_in.read_bytes() == regenerated.read_bytes(), layer
            assert not regenerated.with_suffix(".csv").exists(), layer
        manifest_output = output_root / "manifest.json"
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/build_manifest.py"),
            "--retrieved-at", "2026-08-05", "--output", str(manifest_output),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        assert manifest_output.read_bytes() == (ROOT / "data/manifest.20260805.json").read_bytes()


def main() -> None:
    by_layer = validate_layers()
    validate_coreweave(by_layer)
    validate_aws(by_layer)
    validate_google_azure_oci(by_layer)
    validate_ibm_meta(by_layer)
    validate_manifest()
    validate_regeneration()
    print(f"validated {sum(LAYERS.values()):,} hyperscaler records across {len(LAYERS)} layers")


if __name__ == "__main__":
    main()
