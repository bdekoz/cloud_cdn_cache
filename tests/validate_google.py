#!/usr/bin/env python3
"""Validate Google normalized layers, cross-format parity, and regeneration."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema/location.schema.json"
GOOGLE_DIR = REPO_ROOT / "data/google"
TAG = "20260804"

NULLABLE_FIELDS = {
    "parent_record_id",
    "source_record_id",
    "site_code",
    "city",
    "metro",
    "subdivision",
    "country",
    "country_code",
    "source_published_at",
    "coordinate_crs",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def csv_record(row: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = dict(row)
    result["aliases"] = json.loads(row["aliases"])
    result["service_scope"] = json.loads(row["service_scope"])
    result["properties"] = json.loads(row["properties"])
    for field in NULLABLE_FIELDS:
        result[field] = row[field] or None
    for field in ("latitude", "longitude"):
        result[field] = float(row[field]) if row[field] else None
    return result


def derive_csv_records(path: Path) -> list[dict[str, object]]:
    result = subprocess.run(
        [
            "jq",
            "-r",
            "--slurpfile",
            "schema",
            str(SCHEMA_PATH),
            "-f",
            str(REPO_ROOT / "scripts/geojson-to-csv.jq"),
            str(path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [csv_record(row) for row in csv.DictReader(io.StringIO(result.stdout))]


def geojson_records(path: Path) -> list[dict[str, object]]:
    collection = read_json(path)
    assert collection["type"] == "FeatureCollection"
    result = []
    for feature in collection["features"]:
        record = dict(feature["properties"])
        if feature["geometry"] is None:
            record["latitude"] = None
            record["longitude"] = None
        else:
            assert feature["geometry"]["type"] == "Point"
            longitude, latitude = feature["geometry"]["coordinates"]
            record["latitude"] = latitude
            record["longitude"] = longitude
        assert feature.get("id", record["record_id"]) == record["record_id"]
        result.append(record)
    return result


def schema_validator() -> Draft202012Validator:
    schema = read_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(
    records: list[dict[str, object]], validator: Draft202012Validator
) -> None:
    assert len(records) == len({record["record_id"] for record in records})
    for record in records:
        errors = list(validator.iter_errors(record))
        assert not errors, f"{record['record_id']}: {[error.message for error in errors]}"


def validate_raw_provenance() -> None:
    for stem in ("peering-infrastructure", "data-centers-directory"):
        raw = REPO_ROOT / f"data/raw/google/{stem}.{TAG}.html"
        manifest = read_json(
            REPO_ROOT / f"data/raw/google/{stem}.{TAG}.provenance.json"
        )
        assert manifest["raw_sha256"] == sha256(raw)
        assert manifest["raw_bytes"] == raw.stat().st_size
        assert manifest["retrieved_at"] == "2026-08-04"


def validate_edge(validator: Draft202012Validator) -> None:
    geojson_path = GOOGLE_DIR / f"edge.{TAG}.geojson"
    report = read_json(GOOGLE_DIR / f"edge.{TAG}.report.json")
    csv_rows = derive_csv_records(geojson_path)
    geojson_rows = geojson_records(geojson_path)

    assert csv_rows == geojson_rows
    assert len(csv_rows) == 65
    validate_records(csv_rows, validator)
    assert all(row["service"] == "google_edge" for row in csv_rows)
    assert all(row["entity_type"] == "edge_pop" for row in csv_rows)
    assert all(row["latitude"] is not None for row in csv_rows)
    assert all(row["location_precision"] == "metro" for row in csv_rows)
    assert any(row["record_id"] == "google:edge_pop:dammam-sa" for row in csv_rows)
    assert report["record_count"] == len(csv_rows)
    assert report["derived_files"]["csv"] == {
        "generator": f"make data/google/edge.{TAG}.csv",
        "path": f"data/google/edge.{TAG}.csv",
        "source": f"data/google/edge.{TAG}.geojson",
    }
    assert report["generated_files"] == [f"data/google/edge.{TAG}.geojson"]
    assert report["geojson_sha256"] == sha256(geojson_path)
    assert report["legacy_comparison"]["legacy_coordinate_match_count"] == 64
    assert report["legacy_comparison"]["current_source_only_count"] == 1


def validate_data_centers(validator: Draft202012Validator) -> None:
    geojson_path = GOOGLE_DIR / f"data-centers.{TAG}.geojson"
    report = read_json(GOOGLE_DIR / f"data-centers.{TAG}.report.json")
    csv_rows = derive_csv_records(geojson_path)
    geojson_rows = geojson_records(geojson_path)

    assert csv_rows == geojson_rows
    assert len(csv_rows) == 59
    validate_records(csv_rows, validator)
    assert Counter(row["lifecycle_status"] for row in csv_rows) == Counter(
        {"operational": 32, "in_development": 27}
    )
    assert sum(row["latitude"] is not None for row in csv_rows) == 12
    assert sum(row["latitude"] is None for row in csv_rows) == 47
    assert all(row["country_code"] for row in csv_rows)
    assert all(
        row["properties"]["in_development"]
        == (row["lifecycle_status"] == "in_development")
        for row in csv_rows
    )
    assert report["record_count"] == len(csv_rows)
    assert report["derived_files"]["csv"] == {
        "generator": f"make data/google/data-centers.{TAG}.csv",
        "path": f"data/google/data-centers.{TAG}.csv",
        "source": f"data/google/data-centers.{TAG}.geojson",
    }
    assert report["generated_files"] == [f"data/google/data-centers.{TAG}.geojson"]
    assert report["geojson_sha256"] == sha256(geojson_path)
    assert (
        report["legacy_comparison"]["legacy_peering_map_data_center_count"] == 24
    )


def validate_legacy_google_unchanged_in_scope() -> None:
    with (REPO_ROOT / "data/Google_GGC_01-12-2023.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        assert sum(1 for _ in csv.DictReader(handle)) == 1267
    legacy_geojson = read_json(REPO_ROOT / "data/Google_GGC_01-12-2023.geojson")
    assert len(legacy_geojson["features"]) == 1267


def validate_deterministic_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="cloud-cdn-google-") as temp_dir:
        output_dir = Path(temp_dir)
        command = [
            sys.executable,
            "-B",
            str(REPO_ROOT / "scripts/update_google.py"),
            "--retrieved-at",
            "2026-08-04",
            "--dataset",
            "all",
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for name in (
            f"edge.{TAG}.geojson",
            f"data-centers.{TAG}.geojson",
        ):
            assert sha256(output_dir / name) == sha256(GOOGLE_DIR / name), name
        assert not list(output_dir.glob(f"*.{TAG}.csv"))

        for dataset, expected_prefix, absent_prefix in (
            ("edge", "edge", "data-centers"),
            ("data-center", "data-centers", "edge"),
        ):
            option_dir = output_dir / dataset
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(REPO_ROOT / "scripts/update_google.py"),
                    "--retrieved-at",
                    "2026-08-04",
                    "--dataset",
                    dataset,
                    "--output-dir",
                    str(option_dir),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            assert (option_dir / f"{expected_prefix}.{TAG}.geojson").exists()
            assert not (option_dir / f"{absent_prefix}.{TAG}.geojson").exists()
            assert not list(option_dir.glob(f"*.{TAG}.csv"))


def validate_current_google(validator: Draft202012Validator) -> None:
    tag = "20261011"
    by_layer = {}
    for layer, count in (("edge", 65), ("data-centers", 68), ("cloud-regions-and-zones", 176)):
        path = GOOGLE_DIR / f"{layer}.{tag}.geojson"
        rows = geojson_records(path)
        report = read_json(path.with_suffix(".report.json"))
        assert len(rows) == report["record_count"] == count
        assert derive_csv_records(path) == rows
        validate_records(rows, validator)
        assert report["geojson_sha256"] == sha256(path)
        assert all(row["retrieved_at"] == row["last_seen"] == "2026-10-11" for row in rows)
        baseline_tag = "20260805" if layer == "cloud-regions-and-zones" else TAG
        baseline = {row["record_id"]: row for row in geojson_records(GOOGLE_DIR / f"{layer}.{baseline_tag}.geojson")}
        for row in rows:
            assert row["first_seen"] == (baseline[row["record_id"]]["first_seen"] if row["record_id"] in baseline else "2026-10-11")
            assert row["source_sha256"] == sha256(REPO_ROOT / row["raw_source_ref"])
        by_layer[layer] = rows

    edges = by_layer["edge"]
    old_edges = geojson_records(GOOGLE_DIR / f"edge.{TAG}.geojson")
    assert [(row["record_id"], row["latitude"], row["longitude"]) for row in edges] == [
        (row["record_id"], row["latitude"], row["longitude"]) for row in old_edges
    ]
    centers = by_layer["data-centers"]
    assert Counter(row["lifecycle_status"] for row in centers) == {"operational": 37, "in_development": 31}
    assert sum(row["latitude"] is not None for row in centers) == 12
    center_report = read_json(GOOGLE_DIR / f"data-centers.{tag}.report.json")
    assert len(center_report["added_record_ids"]) == 14
    assert len(center_report["removed_record_ids"]) == 5
    assert {change["record_id"] for change in center_report["lifecycle_changes"]} == {
        "google:data_center:lincoln-nebraska-us", "google:data_center:mesa-arizona-us",
    }
    assert all(change["previous"] == "in_development" and change["current"] == "operational" for change in center_report["lifecycle_changes"])

    cloud = by_layer["cloud-regions-and-zones"]
    assert all(row["latitude"] is row["longitude"] is None for row in cloud)
    regions = {row["site_code"]: row for row in cloud if row["entity_type"] == "cloud_region"}
    zones = {row["site_code"]: row for row in cloud if row["entity_type"] == "availability_zone"}
    assert len(regions) == 43 and len(zones) == 133
    parents = {
        "europe-west4-ai1a": ("europe-west4-a", "De Kooy", "NL"),
        "us-central1-ai1a": ("us-central1-a", "Lincoln", "US"),
        "us-south1-ai1b": ("us-south1-b", "Austin", "US"),
    }
    assert {code for code, row in zones.items() if row["properties"]["zone_kind"] == "ai"} == set(parents)
    for code, (parent, city, country) in parents.items():
        row = zones[code]
        assert row["city"] == city and row["country_code"] == country
        assert row["access_status"] == "restricted"
        assert row["properties"]["parent_zone_record_id"] == zones[parent]["record_id"]
        assert row["parent_record_id"] == zones[parent]["parent_record_id"]
        assert row["properties"]["access_requirement"] == "enable_ai_zone_visibility_for_project"
    for code, row in zones.items():
        region = code.rsplit("-", 1)[0]
        assert row["parent_record_id"] == regions[region]["record_id"]
        assert code in regions[region]["properties"]["availability_zone_ids"]
        if code not in parents:
            assert row["properties"]["zone_kind"] == "standard" and row["access_status"] == "public"
    endpoints = read_json(REPO_ROOT / f"data/raw/google/gcping-endpoints.{tag}.json")
    assert set(endpoints) - {"global"} == set(regions)
    for code, row in regions.items():
        properties = row["properties"]
        endpoint = properties["gcping"]
        assert endpoint["endpoint_url"] == endpoints[code]["URL"]
        assert endpoint["region_label"] == endpoints[code]["RegionName"]
        assert endpoint["source_scope"] == "observed"
        assert endpoint["official_google_product"] is False
        assert endpoint["source_sha256"] == sha256(REPO_ROOT / endpoint["raw_source_ref"])
        children = [child for child in zones.values() if child["parent_record_id"] == row["record_id"]]
        assert properties["availability_zone_count"] == len(children)
        assert properties["standard_availability_zone_count"] + properties["ai_zone_count"] == len(children)
        assert properties["gpu_zone_ids"] == sorted(child["site_code"] for child in children if "gpu_availability" in child["properties"])
    assert "global" not in regions
    assert all("gcping" not in row["properties"] for row in zones.values())
    gpu_zones = [row for row in zones.values() if "gpu_availability" in row["properties"]]
    assert len(gpu_zones) == 89
    assert zones["europe-west4-ai1a"]["properties"]["gpu_availability"]["machine_types"] == ["G4"]
    assert all("gpu_availability" not in zones[code]["properties"] for code in ("us-central1-ai1a", "us-south1-ai1b"))
    for row in gpu_zones:
        gpu = row["properties"]["gpu_availability"]
        assert gpu["source_sha256"] == sha256(REPO_ROOT / gpu["raw_source_ref"])
    cloud_report = read_json(GOOGLE_DIR / f"cloud-regions-and-zones.{tag}.report.json")
    assert cloud_report["standard_availability_zone_count"] == 130
    assert cloud_report["ai_zone_count"] == 3
    assert cloud_report["gcping"]["latency_measurements_collected"] is False
    assert cloud_report["gcping"]["regions_without_endpoint"] == []
    assert cloud_report["gcping"]["unmatched_endpoint_region_ids"] == []
    assert set(cloud_report["gpu_unlisted_zone_ids"]) == set(zones) - {row["site_code"] for row in gpu_zones}
    for raw in (REPO_ROOT / "data/raw/google").glob(f"*.{tag}.*"):
        if raw.name.endswith(".provenance.json"):
            continue
        manifest_path = raw.with_suffix(".provenance.json") if raw.name.startswith(("peering-", "data-centers-")) else raw.with_suffix(raw.suffix + ".provenance.json")
        provenance = read_json(manifest_path)
        assert provenance.get("raw_sha256", provenance.get("sha256")) == sha256(raw)
        assert provenance["retrieved_at"] == "2026-10-11"
    manifest = read_json(REPO_ROOT / f"data/manifest.{tag}.json")
    assert manifest["record_count"] == 27390 and manifest["layer_count"] == 28
    for layer in manifest["layers"]:
        if layer["layer"].startswith("google/"):
            assert layer["snapshot_tag"] == tag
        for file in layer["files"].values():
            assert sha256(REPO_ROOT / file["path"]) == file["sha256"]
        for source in layer["sources"]:
            assert sha256(REPO_ROOT / source["raw_source_ref"]) == source["sha256"]
    cloud_manifest = next(layer for layer in manifest["layers"] if layer["layer"] == "google/cloud-regions-and-zones")
    assert len(cloud_manifest["sources"]) == 5


def validate_current_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="cloud-cdn-google-enrichment-") as temp:
        output_root = Path(temp)
        output_dir = output_root / "data/google"
        output_dir.mkdir(parents=True)
        for name in (f"edge.{TAG}.geojson", f"data-centers.{TAG}.geojson", "cloud-regions-and-zones.20260805.geojson"):
            shutil.copyfile(GOOGLE_DIR / name, output_dir / name)
        commands = [
            ["scripts/update_google.py", "--output-dir", str(output_dir)],
            ["scripts/update_hyperscalers.py", "--dataset", "google", "--google-enrichment", "--output-root", str(output_root)],
        ]
        for args in commands:
            subprocess.run([sys.executable, "-B", *args, "--retrieved-at", "2026-10-11"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
        for layer in ("edge", "data-centers", "cloud-regions-and-zones"):
            name = f"{layer}.20261011.geojson"
            assert (output_dir / name).read_bytes() == (GOOGLE_DIR / name).read_bytes(), name
            actual = read_json((output_dir / name).with_suffix(".report.json"))
            expected = read_json((GOOGLE_DIR / name).with_suffix(".report.json"))
            for field in ("derived_files", "generated_files", "geojson_file"):
                actual.pop(field, None)
                expected.pop(field, None)
            assert actual == expected, layer
        assert not list(output_dir.glob("*.csv"))
        manifest_output = output_root / "manifest.json"
        subprocess.run([sys.executable, "-B", "scripts/build_manifest.py", "--retrieved-at", "2026-10-11", "--output", str(manifest_output)], cwd=REPO_ROOT, check=True, capture_output=True)
        assert manifest_output.read_bytes() == (REPO_ROOT / "data/manifest.20261011.json").read_bytes()


def main() -> None:
    validator = schema_validator()
    validate_raw_provenance()
    validate_edge(validator)
    validate_data_centers(validator)
    validate_legacy_google_unchanged_in_scope()
    validate_deterministic_regeneration()
    validate_current_google(validator)
    validate_current_regeneration()
    print(
        "Google validation passed: retained historical layers; 65 current edge metros; "
        "68 data-center locations; 43 regions, 130 standard zones and 3 AI zones; "
        "43 GCPing endpoints and 89 GPU-availability joins."
    )


if __name__ == "__main__":
    main()
