#!/usr/bin/env python3
"""Validate non-spatial provider-prefix and RIPEstat evidence layers."""

from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
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
    "provider-prefixes": 1581,
    "ripestat-routing": 15,
    "peeringdb-relationships": 1529,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_csv(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    result = subprocess.run(
        [
            "jq", "-r", "--slurpfile", "schema", str(ROOT / "schema/network-evidence.schema.json"),
            "-f", str(ROOT / "scripts/network-json-to-csv.jq"), str(path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    fields = schema["$defs"]["record"]["required"]
    assert reader.fieldnames == fields
    records: list[dict[str, Any]] = []
    nullable = {
        field
        for field, definition in schema["$defs"]["record"]["properties"].items()
        if isinstance(definition.get("type"), list) and "null" in definition["type"]
    }
    for row in reader:
        record: dict[str, Any] = dict(row)
        record["properties"] = json.loads(row["properties"])
        for field in ("ip_family", "asn"):
            record[field] = int(row[field]) if row[field] else None
        for field in nullable:
            if row[field] == "":
                record[field] = None
        records.append(record)
    return records


def validate_layers() -> dict[str, list[dict[str, Any]]]:
    schema = json.loads((ROOT / "schema/network-evidence.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    by_layer: dict[str, list[dict[str, Any]]] = {}
    all_ids: set[str] = set()
    for layer, expected_count in LAYERS.items():
        json_path = ROOT / "data/network" / f"{layer}.{TAG}.json"
        report_path = ROOT / "data/network" / f"{layer}.{TAG}.report.json"
        collection = json.loads(json_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(collection))
        assert not errors, f"{layer}: {errors[0].message if errors else ''}"
        records = collection["records"]
        by_layer[layer] = records
        assert len(records) == expected_count == report["record_count"]
        ids = [record["record_id"] for record in records]
        assert ids == sorted(ids)
        assert len(ids) == len(set(ids))
        assert not all_ids.intersection(ids)
        all_ids.update(ids)
        assert derive_csv(json_path, schema) == records
        assert report["generated_files"] == [f"data/network/{layer}.{TAG}.json"]
        assert report["derived_files"]["csv"] == {
            "generator": f"make data/network/{layer}.{TAG}.csv",
            "path": f"data/network/{layer}.{TAG}.csv",
            "source": f"data/network/{layer}.{TAG}.json",
        }
        for record in records:
            assert "geometry" not in record
            if record["prefix"]:
                network = ipaddress.ip_network(record["prefix"], strict=True)
                assert network.version == record["ip_family"]
                assert str(network) == record["prefix"]
    return by_layer


def validate_prefixes(records: list[dict[str, Any]]) -> None:
    assert all(record["evidence_type"] == "provider_prefix" for record in records)
    assert all(record["source_scope"] == "provider_declared" for record in records)
    assert all(record["asn"] is None for record in records)
    assert all(record["properties"]["network_location_not_asserted"] for record in records)
    assert Counter(record["properties"]["feed_scope"] for record in records) == Counter({
        "google_cloud_customer": 1091,
        "azure_front_door_frontend": 226,
        "aws_cloudfront_global": 150,
        "google_owned": 114,
    })
    assert Counter(record["ip_family"] for record in records) == Counter({4: 1337, 6: 244})
    aws = [record for record in records if record["properties"]["feed_scope"] == "aws_cloudfront_global"]
    assert all(record["properties"]["provider_region"] == "GLOBAL" for record in aws)
    assert all(record["properties"]["provider_service_code"] == "CLOUDFRONT" for record in aws)
    azure = [record for record in records if record["properties"]["feed_scope"] == "azure_front_door_frontend"]
    assert all(record["properties"]["provider_service_tag"] == "AzureFrontDoor.Frontend" for record in azure)


def validate_ripestat(records: list[dict[str, Any]], prefixes: list[dict[str, Any]]) -> None:
    assert Counter(record["evidence_type"] for record in records) == Counter({
        "routing_origin": 8,
        "rpki_validation": 7,
    })
    assert Counter(record["status"] for record in records) == Counter({
        "announced": 7,
        "valid": 7,
        "not_announced": 1,
    })
    prefix_ids = {record["record_id"] for record in prefixes}
    assert all(record["source_scope"] == "observed" for record in records)
    assert all(record["properties"]["provider_prefix_record_id"] in prefix_ids for record in records)
    assert all("geo" not in record["source_url"].lower() for record in records)
    routing = [record for record in records if record["evidence_type"] == "routing_origin"]
    assert len({record["properties"]["provider_prefix_record_id"] for record in routing}) == 8
    negative = [record for record in routing if record["status"] == "not_announced"]
    assert len(negative) == 1
    assert negative[0]["properties"]["declared_prefix"] == "2001:3fc6:20::/43"


def validate_peeringdb(records: list[dict[str, Any]]) -> None:
    assert Counter(record["evidence_type"] for record in records) == Counter({
        "facility_registration": 498,
        "ix_membership": 1031,
    })
    assert Counter(record["asn"] for record in records) == Counter({
        8075: 538,
        15169: 454,
        16509: 529,
        396982: 8,
    })
    assert Counter(record["status"] for record in records) == Counter({
        "registered": 498,
        "operational": 1026,
        "not_operational": 5,
    })
    assert all(record["source_scope"] == "registry" for record in records)
    assert all(record["prefix"] is record["ip_family"] is None for record in records)
    assert all(record["properties"]["registration_not_cdn_presence"] for record in records)
    assert all(record["properties"]["registration_not_provider_ownership"] for record in records)
    facilities = [record for record in records if record["evidence_type"] == "facility_registration"]
    ix_memberships = [record for record in records if record["evidence_type"] == "ix_membership"]
    assert all(record["object_id"].startswith("peeringdb:facility:") for record in facilities)
    assert all(record["object_id"].startswith("peeringdb:ix:") for record in ix_memberships)


def validate_manifest() -> None:
    manifest = json.loads((ROOT / "data/manifest.20260805.json").read_text(encoding="utf-8"))
    assert manifest["network_evidence_layer_count"] == 3
    assert manifest["network_evidence_record_count"] == sum(LAYERS.values())
    assert manifest["network_evidence_schema"]["version"] == "1.0.0"
    assert digest(ROOT / manifest["network_evidence_schema"]["path"]) == manifest["network_evidence_schema"]["sha256"]
    by_name = {layer["layer"]: layer for layer in manifest["network_evidence_layers"]}
    assert set(by_name) == set(LAYERS)
    for name, expected_count in LAYERS.items():
        layer = by_name[name]
        assert layer["record_count"] == expected_count
        assert layer["snapshot_tag"] == TAG
        for file_record in layer["files"].values():
            assert digest(ROOT / file_record["path"]) == file_record["sha256"]


def validate_regeneration() -> None:
    with tempfile.TemporaryDirectory(prefix="network-refresh-") as temp:
        output_root = Path(temp)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_network.py"),
            "--retrieved-at", "2026-08-05", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([
            sys.executable, "-B", str(ROOT / "scripts/update_peeringdb.py"),
            "--retrieved-at", "2026-08-05", "--output-root", str(output_root),
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        for layer in LAYERS:
            for suffix in ("json", "report.json"):
                checked_in = ROOT / "data/network" / f"{layer}.{TAG}.{suffix}"
                regenerated = output_root / "data/network" / f"{layer}.{TAG}.{suffix}"
                assert checked_in.read_bytes() == regenerated.read_bytes(), f"{layer}.{suffix}"
            assert not (output_root / "data/network" / f"{layer}.{TAG}.csv").exists()


def main() -> None:
    by_layer = validate_layers()
    validate_prefixes(by_layer["provider-prefixes"])
    validate_ripestat(by_layer["ripestat-routing"], by_layer["provider-prefixes"])
    validate_peeringdb(by_layer["peeringdb-relationships"])
    validate_manifest()
    validate_regeneration()
    print(f"validated {sum(LAYERS.values()):,} records across {len(LAYERS)} network-evidence layers")


if __name__ == "__main__":
    main()
