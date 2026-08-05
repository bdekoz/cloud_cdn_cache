#!/usr/bin/env python3
"""Validate the partial MaxMind city-observation layer from the June 2026 study."""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
TAG = "20260805"
LAYER = "observations/cdn-mapping-cities"
EXPECTED_COUNT = 11659


def canonical_from_feature(feature: dict[str, Any]) -> dict[str, Any]:
    record = dict(feature["properties"])
    record["longitude"], record["latitude"] = feature["geometry"]["coordinates"]
    return record


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
    records: list[dict[str, Any]] = []
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
        records.append(record)
    return records


def validate_layer() -> None:
    schema = json.loads((ROOT / "schema/location.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    path = ROOT / "data" / f"{LAYER}.{TAG}.geojson"
    report = json.loads((ROOT / "data" / f"{LAYER}.{TAG}.report.json").read_text(encoding="utf-8"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = [canonical_from_feature(feature) for feature in payload["features"]]
    assert len(records) == EXPECTED_COUNT == report["record_count"]
    assert report["geometry_null"] == 0
    assert report["raw_record_count"] == 11663
    assert report["accepted_record_count"] == EXPECTED_COUNT
    assert report["rejected_record_count"] == 4
    assert report["rejections_by_reason"] == {"invalid_asn": 4}
    assert report["provider_counts"] == {
        "Facebook/Meta FNA": 2736,
        "Google GGC": 4802,
        "Netflix OCA": 4121,
    }
    assert report["valid_country_counts"] == {
        "Google GGC": 198,
        "Meta FNA": 183,
        "Netflix OCA": 181,
    }
    assert report["country_coverage_gaps"] == {
        "Google GGC": 17,
        "Meta FNA": 21,
        "Netflix OCA": 0,
    }
    assert len(report["folders_at_2000_record_limit"]) == 5
    assert report["missing_city_counts"] == {"Netflix OCA": 599}
    assert report["license_status"].startswith("not stated")
    assert derive_csv(path, schema) == records

    ids = [record["record_id"] for record in records]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert Counter(record["provider"] for record in records) == Counter({
        "Google": 4802,
        "Meta": 2736,
        "Netflix": 4121,
    })
    assert sum(record["city"] is None for record in records) == 599
    assert all(record["source_scope"] == "observed" for record in records)
    assert all(record["service"] == "cdn_mapping_city_observation" for record in records)
    assert all(record["coordinate_method"] == "geocoded" for record in records)
    assert all(record["coordinate_crs"] == "EPSG:4326" for record in records)
    assert all(record["properties"]["geolocation_is_not_facility"] for record in records)
    assert all(record["properties"]["map_is_partial"] for record in records)
    assert all(record["properties"]["asn"] > 0 for record in records)
    assert all(record["country_code"] for record in records)
    for record in records:
        errors = list(validator.iter_errors(record))
        assert not errors, f"{record['record_id']}: {errors[0].message if errors else ''}"

    asn_payload = json.loads((ROOT / "data/observations/cdn-mapping.20260804.geojson").read_text(encoding="utf-8"))
    observed_asns: dict[str, set[int]] = defaultdict(set)
    for feature in asn_payload["features"]:
        properties = feature["properties"]
        observed_asns[properties["properties"]["dataset"]].add(properties["properties"]["asn"])
    city_asns: dict[str, set[int]] = defaultdict(set)
    for record in records:
        city_asns[record["properties"]["dataset"]].add(record["properties"]["asn"])
    assert all(city_asns[dataset] <= observed_asns[dataset] for dataset in city_asns)
    assert {dataset: len(values) for dataset, values in city_asns.items()} == {
        "Google GGC": 3344,
        "Facebook/Meta FNA": 1896,
        "Netflix OCA": 2902,
    }


def validate_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="city-observation-refresh-") as temp:
        output_root = Path(temp)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_observation_cities.py"),
            "--retrieved-at", "2026-08-05", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        checked_in = ROOT / "data" / f"{LAYER}.{TAG}.geojson"
        regenerated = output_root / "data" / f"{LAYER}.{TAG}.geojson"
        assert checked_in.read_bytes() == regenerated.read_bytes()
        assert not regenerated.with_suffix(".csv").exists()


def main() -> None:
    validate_layer()
    validate_regeneration()
    print(f"validated {EXPECTED_COUNT:,} partial city observations")


if __name__ == "__main__":
    main()
