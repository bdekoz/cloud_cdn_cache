#!/usr/bin/env python3
"""Validate Google normalized layers, cross-format parity, and regeneration."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
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


def read_csv_records(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [csv_record(row) for row in csv.DictReader(handle)]


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
        assert feature["id"] == record["record_id"]
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
    csv_path = GOOGLE_DIR / f"edge.{TAG}.csv"
    geojson_path = GOOGLE_DIR / f"edge.{TAG}.geojson"
    report = read_json(GOOGLE_DIR / f"edge.{TAG}.report.json")
    csv_rows = read_csv_records(csv_path)
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
    assert report["csv_sha256"] == sha256(csv_path)
    assert report["geojson_sha256"] == sha256(geojson_path)
    assert report["legacy_comparison"]["legacy_coordinate_match_count"] == 64
    assert report["legacy_comparison"]["current_source_only_count"] == 1


def validate_data_centers(validator: Draft202012Validator) -> None:
    csv_path = GOOGLE_DIR / f"data-centers.{TAG}.csv"
    geojson_path = GOOGLE_DIR / f"data-centers.{TAG}.geojson"
    report = read_json(GOOGLE_DIR / f"data-centers.{TAG}.report.json")
    csv_rows = read_csv_records(csv_path)
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
    assert report["csv_sha256"] == sha256(csv_path)
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
            f"edge.{TAG}.csv",
            f"edge.{TAG}.geojson",
            f"data-centers.{TAG}.csv",
            f"data-centers.{TAG}.geojson",
        ):
            assert sha256(output_dir / name) == sha256(GOOGLE_DIR / name), name

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
            assert (option_dir / f"{expected_prefix}.{TAG}.csv").exists()
            assert not (option_dir / f"{absent_prefix}.{TAG}.csv").exists()


def main() -> None:
    validator = schema_validator()
    validate_raw_provenance()
    validate_edge(validator)
    validate_data_centers(validator)
    validate_legacy_google_unchanged_in_scope()
    validate_deterministic_regeneration()
    print(
        "Google validation passed: 65 edge metros; 59 data-center locations "
        "(27 in development, 12 with provider coordinates)."
    )


if __name__ == "__main__":
    main()
