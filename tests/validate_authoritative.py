#!/usr/bin/env python3
"""Validate authoritative refreshes, observation separation, and reproducibility."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
TAG = "20260804"
LAYERS = {
    "cloudflare/edge": 338,
    "microsoft/front-door": 110,
    "microsoft/front-door-codes": 128,
    "aws/cloudfront": 102,
    "aws/local-zones": 45,
    "fastly/pops": 164,
    "cachefly/locations": 87,
    "alibaba/regions-and-zones": 137,
    "tencent/regions-and-zones": 84,
    "baidu/regions-and-zones": 27,
    "huawei/mainland-regions": 9,
    "volcano/regions-and-zones": 17,
    "kingsoft/mainland-regions-and-zones": 22,
    "jd/mainland-regions-and-zones": 14,
    "tianyi/vpc-resource-pools": 63,
    "chindata/data-centers": 4,
    "observations/cdn-mapping": 13631,
}

VIEWS = {
    "alibaba/mainland-regions-and-zones": ("alibaba/regions-and-zones", 73),
    "tencent/mainland-regions-and-zones": ("tencent/regions-and-zones", 31),
    "tencent/mainland-specialized-regions-and-zones": ("tencent/regions-and-zones", 17),
    "baidu/mainland-regions-and-zones": ("baidu/regions-and-zones", 25),
    "volcano/mainland-regions-and-zones": ("volcano/regions-and-zones", 14),
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
        assert geometry["type"] == "Point"
        record["longitude"], record["latitude"] = geometry["coordinates"]
    return record


def derive_csv_records(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "jq",
            "-r",
            "--slurpfile",
            "schema",
            str(ROOT / "schema/location.schema.json"),
            "-f",
            str(ROOT / "scripts/geojson-to-csv.jq"),
            str(path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    assert reader.fieldnames == schema["required"]
    records = []
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


def validate_report_outputs(report: dict[str, Any], layer: str) -> None:
    geojson_path = f"data/{layer}.{TAG}.geojson"
    csv_path = f"data/{layer}.{TAG}.csv"
    assert report["generated_files"] == [geojson_path]
    assert report["derived_files"]["csv"] == {
        "generator": f"make {csv_path}",
        "path": csv_path,
        "source": geojson_path,
    }


def validate_layers() -> None:
    schema = json.loads((ROOT / "schema/location.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    all_ids: set[str] = set()
    services: set[str] = set()
    aws_region_ids = {
        feature["properties"]["record_id"]
        for feature in json.loads((ROOT / "data/aws/regions-and-zones.20260805.geojson").read_text(encoding="utf-8"))["features"]
        if feature["properties"]["entity_type"] == "cloud_region"
    }
    for layer, expected_count in LAYERS.items():
        geojson_path = ROOT / "data" / f"{layer}.{TAG}.geojson"
        report_path = ROOT / "data" / f"{layer}.{TAG}.report.json"
        payload = json.loads(geojson_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        validate_report_outputs(report, layer)
        records = [canonical_from_feature(feature) for feature in payload["features"]]
        assert len(records) == expected_count == report["record_count"], layer
        ids = [record["record_id"] for record in records]
        assert ids == sorted(ids), f"{layer}: records are not deterministically sorted"
        assert len(ids) == len(set(ids)), f"{layer}: duplicate record IDs"
        assert not (all_ids & set(ids)), f"{layer}: cross-layer record ID collision"
        all_ids.update(ids)
        csv_records = derive_csv_records(geojson_path, schema)
        assert csv_records == records, f"{layer}: derived CSV/GeoJSON mismatch"
        for record in records:
            errors = list(validator.iter_errors(record))
            assert not errors, f"{layer}: {record['record_id']}: {errors[0].message if errors else ''}"
            assert record["schema_version"] == "1.1.0"
            assert record["coordinate_crs"] == ("EPSG:4326" if record["latitude"] is not None else None)
            if record["parent_record_id"] is not None:
                allowed_parents = aws_region_ids if layer == "aws/local-zones" else set(ids)
                assert record["parent_record_id"] in allowed_parents, f"{layer}: missing parent"
            services.add(record["service"])
        assert sum(record["latitude"] is None for record in records) == report["geometry_null"], layer
    assert services == {
        "cloudflare_network", "azure_front_door", "aws_cloudfront", "aws_local_zones",
        "fastly_network", "cachefly_network", "alibaba_cloud", "tencent_cloud",
        "baidu_cloud", "huawei_cloud", "volcano_cloud", "kingsoft_cloud", "jd_cloud",
        "ctyun_cloud", "chindata_colocation",
        "cdn_mapping_observation",
    }


def validate_views() -> None:
    schema = json.loads((ROOT / "schema/location.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    view_ids: dict[str, set[str]] = {}
    for view, (parent, expected_count) in VIEWS.items():
        payload = json.loads((ROOT / "data" / f"{view}.{TAG}.geojson").read_text(encoding="utf-8"))
        report = json.loads((ROOT / "data" / f"{view}.{TAG}.report.json").read_text(encoding="utf-8"))
        validate_report_outputs(report, view)
        records = [canonical_from_feature(feature) for feature in payload["features"]]
        assert derive_csv_records(ROOT / "data" / f"{view}.{TAG}.geojson", schema) == records
        ids = {record["record_id"] for record in records}
        parent_payload = json.loads((ROOT / "data" / f"{parent}.{TAG}.geojson").read_text(encoding="utf-8"))
        parent_ids = {feature["properties"]["record_id"] for feature in parent_payload["features"]}
        assert len(records) == expected_count == report["record_count"], view
        assert ids <= parent_ids, view
        assert report["derived_from_layer"] == f"data/{parent}", view
        assert all(not list(validator.iter_errors(record)) for record in records), view
        assert all(record["jurisdiction_scope"] == "mainland_china" for record in records), view
        view_ids[view] = ids
    assert view_ids["tencent/mainland-regions-and-zones"].isdisjoint(
        view_ids["tencent/mainland-specialized-regions-and-zones"]
    )


def validate_semantics() -> None:
    reports = {
        layer: json.loads((ROOT / "data" / f"{layer}.{TAG}.report.json").read_text(encoding="utf-8"))
        for layer in LAYERS
    }
    assert reports["cloudflare/edge"]["geographic_group_count"] == 7
    assert reports["microsoft/front-door"]["commercial_asset_count_from_table"] == 191
    assert reports["microsoft/front-door"]["commercial_metro_count_from_table"] == 107
    assert reports["microsoft/front-door"]["page_claims"] == {
        "commercial_asset_count": 192, "commercial_metro_count": 109, "government_asset_count": 4
    }
    assert reports["microsoft/front-door-codes"]["directory_row_count"] == 128
    assert reports["microsoft/front-door-codes"]["atomic_abbreviation_count"] == 130
    assert reports["microsoft/front-door-codes"]["location_label_count"] == 114
    assert reports["aws/cloudfront"]["standard_pop_asset_count_from_city_list"] == 749
    assert reports["aws/cloudfront"]["unlocated_infrastructure_classes"] == ["regional_edge_cache", "embedded_pop"]
    assert reports["aws/local-zones"]["available_zone_id_count"] == 45
    assert reports["fastly/pops"]["location_label_count"] == 135
    assert reports["cachefly/locations"]["location_count_from_list"] == 87
    assert reports["cachefly/locations"]["page_heading_declared_location_count"] == 88
    assert reports["alibaba/regions-and-zones"]["public_region_count"] == 32
    assert reports["alibaba/regions-and-zones"]["availability_zone_count"] == 105
    assert reports["tencent/regions-and-zones"]["region_count"] == 22
    assert reports["tencent/regions-and-zones"]["availability_zone_count"] == 62
    assert reports["alibaba/regions-and-zones"]["schema_version"] == "1.1.0"
    assert reports["tencent/regions-and-zones"]["specialized_region_count"] == 4
    assert reports["tencent/regions-and-zones"]["specialized_availability_zone_count"] == 13
    assert reports["baidu/regions-and-zones"]["region_count"] == 8
    assert reports["baidu/regions-and-zones"]["availability_zone_count"] == 19
    assert reports["baidu/regions-and-zones"]["mainland_region_count"] == 7
    assert reports["baidu/regions-and-zones"]["mainland_availability_zone_count"] == 18
    assert reports["huawei/mainland-regions"]["mainland_region_count"] == 9
    assert reports["huawei/mainland-regions"]["availability_zone_count"] is None
    assert reports["volcano/regions-and-zones"]["region_count"] == 4
    assert reports["volcano/regions-and-zones"]["availability_zone_count_from_explicit_ids"] == 13
    assert reports["volcano/regions-and-zones"]["source_count_discrepancies"] == [
        {"declared_zone_count": 3, "explicit_zone_id_count": 4, "region_id": "cn-shanghai"}
    ]
    assert reports["kingsoft/mainland-regions-and-zones"]["mainland_region_count"] == 8
    assert reports["kingsoft/mainland-regions-and-zones"]["availability_zone_count"] == 14
    assert reports["kingsoft/mainland-regions-and-zones"]["financial_region_count"] == 2
    assert reports["jd/mainland-regions-and-zones"]["mainland_region_count"] == 4
    assert reports["jd/mainland-regions-and-zones"]["availability_zone_count"] == 10
    assert reports["tianyi/vpc-resource-pools"]["resource_pool_count"] == 63
    assert reports["tianyi/vpc-resource-pools"]["regional_resource_pool_count"] == 40
    assert reports["tianyi/vpc-resource-pools"]["availability_zone_capable_resource_pool_count"] == 23
    assert reports["tianyi/vpc-resource-pools"]["availability_zone_records_generated"] == 0
    assert reports["chindata/data-centers"]["directory_code_count"] == 4
    assert reports["chindata/data-centers"]["facility_location_count"] == 0
    observations = reports["observations/cdn-mapping"]
    assert observations["record_count"] == observations["geometry_null"] == 13631
    assert observations["accepted_record_count"] == 13631
    assert observations["raw_record_count"] == 13638
    assert observations["rejected_record_count"] == 7
    assert observations["rejections_by_reason"] == {"invalid_asn": 7}
    assert {row["asn"] for row in observations["rejected_records"]} == {"0"}
    assert {row["dataset"] for row in observations["rejected_records"]} == {
        "Google GGC", "Netflix OCA", "Facebook/Meta FNA", "Akamai",
        "Microsoft CDN", "Apple", "AWS CloudFront",
    }
    assert observations["provider_counts"] == {
        "Akamai": 1093,
        "Amazon Web Services": 216,
        "Apple": 973,
        "Google": 4246,
        "Meta": 2547,
        "Microsoft": 1654,
        "Netflix": 2902,
    }
    assert observations["license_status"].startswith("not stated")


def validate_provenance() -> None:
    for provenance_path in sorted((ROOT / "data/raw").rglob("*.provenance.json")):
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        raw_path = ROOT / (provenance.get("raw_source_ref") or provenance["raw_file"])
        expected_digest = provenance.get("sha256") or provenance["raw_sha256"]
        assert raw_path.exists(), provenance_path
        assert digest(raw_path) == expected_digest, provenance_path
    audit = json.loads((ROOT / "data/quarantine/audit.20260804.json").read_text(encoding="utf-8"))
    assert audit["baidu"]["legacy_claim_count"] == 35
    assert audit["baidu"]["official_region_column_count"] == 8
    assert audit["alibaba_speculative_layer"]["feature_count"] == 14


def validate_assessments() -> None:
    cloud = json.loads((ROOT / "data/china/provider-assessment.20260804.json").read_text(encoding="utf-8"))
    edge = json.loads((ROOT / "data/china-edge/provider-assessment.20260804.json").read_text(encoding="utf-8"))
    colo = json.loads((ROOT / "data/china-colocation/operator-assessment.20260804.json").read_text(encoding="utf-8"))
    assert len(cloud["providers"]) == 10
    assert len(edge["providers"]) == 10
    assert edge["canonical_location_records_generated"] == 0
    assert "unauthorized or leaked inventories" in edge["excluded_source_classes"]
    assert {row["operator"] for row in colo["operators"]} == {"GDS Holdings", "VNET Group", "Chindata"}
    assert colo["canonical_location_records_generated"] == 4
    assert not (ROOT / "data/china-mobile").exists()
    assert not (ROOT / "data/china-unicom").exists()

    tencent = json.loads((ROOT / "data/tencent/regions-and-zones.20260804.geojson").read_text(encoding="utf-8"))
    records = [canonical_from_feature(feature) for feature in tencent["features"]]
    restricted = [row for row in records if row["properties"].get("sales_restricted")]
    assert restricted and all(row["lifecycle_status"] == "operational" for row in restricted)
    specialized = [row for row in records if {"financial_cloud", "automotive_cloud"} & set(row["service_scope"])]
    assert len(specialized) == 17 and all(row["access_status"] == "dedicated" for row in specialized)


def validate_manifest() -> None:
    manifest = json.loads((ROOT / "data/manifest.20260804.json").read_text(encoding="utf-8"))
    assert manifest["layer_count"] == 19
    assert manifest["record_count"] == 15106
    assert manifest["network_evidence_layer_count"] == 0
    assert manifest["network_evidence_record_count"] == 0
    assert manifest["view_count"] == 5
    assert sum(view["record_count"] for view in manifest["views"]) == 160
    assert manifest["schema"]["version"] == "1.2.0"
    assert manifest["schema"]["sha256"] == digest(ROOT / manifest["schema"]["path"])
    assert {layer["layer"] for layer in manifest["layers"]} == {
        "google/edge", "google/data-centers", *LAYERS.keys()
    }
    for layer in manifest["layers"]:
        assert layer["snapshot_tag"] == TAG
        assert set(layer["files"]) == {"geojson", "report"}
        for file_record in layer["files"].values():
            assert digest(ROOT / file_record["path"]) == file_record["sha256"]
        csv_file = layer["derived_files"]["csv"]
        assert csv_file == {
            "generator": f"make {csv_file['path']}",
            "path": layer["files"]["geojson"]["path"].removesuffix(".geojson") + ".csv",
            "source": layer["files"]["geojson"]["path"],
        }
        assert sum(layer["entity_types"].values()) == layer["record_count"]
    for view in manifest["views"]:
        assert view["snapshot_tag"] == TAG
        assert view["view_of"] in {layer["layer"] for layer in manifest["layers"]}
        assert set(view["files"]) == {"geojson", "report"}
        for file_record in view["files"].values():
            assert digest(ROOT / file_record["path"]) == file_record["sha256"]
        csv_file = view["derived_files"]["csv"]
        assert csv_file == {
            "generator": f"make {csv_file['path']}",
            "path": view["files"]["geojson"]["path"].removesuffix(".geojson") + ".csv",
            "source": view["files"]["geojson"]["path"],
        }
    for assessment in manifest["assessments"]:
        assert digest(ROOT / assessment["path"]) == assessment["sha256"]


def validate_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="cloud-cdn-refresh-") as temp:
        output_root = Path(temp)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_authoritative.py"), "--dataset", "all",
            "--retrieved-at", "2026-08-04", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_observations.py"),
            "--retrieved-at", "2026-08-04", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_china.py"), "--dataset", "all",
            "--retrieved-at", "2026-08-04", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_china_edge.py"),
            "--retrieved-at", "2026-08-04", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_china_colocation.py"),
            "--retrieved-at", "2026-08-04", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        for layer in LAYERS:
            checked_in = ROOT / "data" / f"{layer}.{TAG}.geojson"
            regenerated = output_root / "data" / f"{layer}.{TAG}.geojson"
            assert checked_in.read_bytes() == regenerated.read_bytes(), f"non-deterministic output: {layer}.geojson"
            assert not regenerated.with_suffix(".csv").exists(), f"unexpected generated CSV: {layer}"
        for view in VIEWS:
            checked_in = ROOT / "data" / f"{view}.{TAG}.geojson"
            regenerated = output_root / "data" / f"{view}.{TAG}.geojson"
            assert checked_in.read_bytes() == regenerated.read_bytes(), f"non-deterministic output: {view}.geojson"
            assert not regenerated.with_suffix(".csv").exists(), f"unexpected generated CSV: {view}"
        for assessment in (
            "china/provider-assessment", "china-edge/provider-assessment", "china-colocation/operator-assessment"
        ):
            checked_in = ROOT / "data" / f"{assessment}.{TAG}.json"
            regenerated = output_root / "data" / f"{assessment}.{TAG}.json"
            assert checked_in.read_bytes() == regenerated.read_bytes(), f"non-deterministic output: {assessment}"


def main() -> None:
    validate_layers()
    validate_views()
    validate_semantics()
    validate_provenance()
    validate_assessments()
    validate_manifest()
    validate_regeneration()
    print(f"validated {sum(LAYERS.values()):,} canonical records across {len(LAYERS)} refreshed layers")


if __name__ == "__main__":
    main()
