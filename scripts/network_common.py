#!/usr/bin/env python3
"""Shared validation and serialization helpers for non-spatial network evidence."""

from __future__ import annotations

import ipaddress
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from location_common import REPO_ROOT, repo_ref, retrieval_tag, write_json


NETWORK_SCHEMA_PATH = REPO_ROOT / "schema/network-evidence.schema.json"
NETWORK_SCHEMA_VERSION = "1.0.0"

NETWORK_FIELDS = (
    "record_id",
    "evidence_type",
    "subject_type",
    "subject_id",
    "provider",
    "service",
    "prefix",
    "ip_family",
    "asn",
    "relationship_type",
    "object_type",
    "object_id",
    "status",
    "source_scope",
    "source_url",
    "raw_source_ref",
    "source_sha256",
    "source_published_at",
    "retrieved_at",
    "observed_at",
    "valid_from",
    "valid_to",
    "confidence",
    "properties",
)


def canonical_network_record(**values: Any) -> dict[str, Any]:
    values = dict(values)
    missing = [field for field in NETWORK_FIELDS if field not in values]
    extra = sorted(set(values) - set(NETWORK_FIELDS))
    if missing or extra:
        raise ValueError(f"network record field mismatch: missing={missing}, extra={extra}")
    return {field: values[field] for field in NETWORK_FIELDS}


def load_network_validator(schema_path: Path = NETWORK_SCHEMA_PATH) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_network_collection(
    collection: dict[str, Any], schema_path: Path = NETWORK_SCHEMA_PATH
) -> None:
    validator = load_network_validator(schema_path)
    errors = sorted(validator.iter_errors(collection), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "<collection>"
        raise ValueError(f"{path}: {error.message}")
    seen: set[str] = set()
    for record in collection["records"]:
        record_id = record["record_id"]
        if record_id in seen:
            raise ValueError(f"duplicate network record_id: {record_id}")
        seen.add(record_id)
        prefix = record["prefix"]
        if prefix is not None:
            network = ipaddress.ip_network(prefix, strict=True)
            if str(network) != prefix:
                raise ValueError(f"non-canonical prefix in {record_id}: {prefix}")
            if network.version != record["ip_family"]:
                raise ValueError(f"IP-family mismatch in {record_id}: {prefix}")


def write_network_layer(
    *,
    records: list[dict[str, Any]],
    layer_name: str,
    retrieved_at: str,
    parser_name: str,
    output_root: Path = REPO_ROOT,
    schema_path: Path = NETWORK_SCHEMA_PATH,
    extra_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tag = retrieval_tag(retrieved_at)
    records.sort(key=lambda record: record["record_id"])
    collection = {
        "layer": layer_name,
        "records": records,
        "retrieved_at": retrieved_at,
        "schema_version": NETWORK_SCHEMA_VERSION,
        "type": "NetworkEvidenceCollection",
    }
    validate_network_collection(collection, schema_path)

    output_dir = output_root / "data/network"
    json_path = output_dir / f"{layer_name}.{tag}.json"
    report_path = output_dir / f"{layer_name}.{tag}.report.json"
    csv_path = output_dir / f"{layer_name}.{tag}.csv"
    logical_dir = REPO_ROOT / "data/network"
    logical_json_path = logical_dir / json_path.name
    logical_csv_path = logical_dir / csv_path.name
    write_json(json_path, collection)

    providers = Counter(record["provider"] for record in records if record["provider"])
    report: dict[str, Any] = {
        "derived_files": {
            "csv": {
                "generator": f"make {repo_ref(logical_csv_path)}",
                "path": repo_ref(logical_csv_path),
                "source": repo_ref(logical_json_path),
            }
        },
        "evidence_types": dict(sorted(Counter(record["evidence_type"] for record in records).items())),
        "generated_files": [repo_ref(logical_json_path)],
        "layer": layer_name,
        "parser": parser_name,
        "provider_counts": dict(sorted(providers.items())),
        "record_count": len(records),
        "retrieved_at": retrieved_at,
        "schema": repo_ref(schema_path),
        "schema_version": NETWORK_SCHEMA_VERSION,
        "semantic_boundary": "Network evidence is non-spatial and does not prove a physical POP, facility, or provider ownership.",
        "statuses": dict(sorted(Counter(record["status"] for record in records).items())),
    }
    if extra_report:
        report.update(extra_report)
    write_json(report_path, report)
    return report
