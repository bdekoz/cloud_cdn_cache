#!/usr/bin/env python3
"""Shared canonical-record, provenance, and serialization helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from babel import Locale
from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema/location.schema.json"
SCHEMA_VERSION = "1.1.0"

CANONICAL_FIELDS = (
    "schema_version",
    "record_id",
    "aliases",
    "provider",
    "service",
    "entity_type",
    "parent_record_id",
    "jurisdiction_scope",
    "access_status",
    "service_scope",
    "source_collection",
    "source_record_id",
    "name",
    "site_code",
    "lifecycle_status",
    "source_scope",
    "city",
    "metro",
    "subdivision",
    "country",
    "country_code",
    "latitude",
    "longitude",
    "location_precision",
    "coordinate_method",
    "coordinate_crs",
    "source_url",
    "raw_source_ref",
    "source_sha256",
    "source_published_at",
    "retrieved_at",
    "first_seen",
    "last_seen",
    "confidence",
    "properties",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_ref(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", ascii_value))


def retrieval_tag(retrieved_at: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved_at):
        raise ValueError(f"Invalid retrieval date: {retrieved_at!r}")
    return retrieved_at.replace("-", "")


def fetch(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "cloud-cdn-cache-data-refresh/1.0 (+https://github.com/stevesong/cloud_cdn_cache)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        output.write_bytes(response.read())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_provenance(
    raw_path: Path,
    *,
    source_url: str,
    retrieved_at: str,
    media_type: str,
    notes: str,
    source_published_at: str | None = None,
) -> Path:
    provenance_path = raw_path.with_suffix(raw_path.suffix + ".provenance.json")
    write_json(
        provenance_path,
        {
            "media_type": media_type,
            "notes": notes,
            "raw_source_ref": repo_ref(raw_path),
            "retrieved_at": retrieved_at,
            "sha256": sha256(raw_path),
            "source_published_at": source_published_at,
            "source_url": source_url,
        },
    )
    return provenance_path


def load_validator(schema_path: Path = SCHEMA_PATH) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(records: Iterable[dict[str, Any]], schema_path: Path = SCHEMA_PATH) -> None:
    validator = load_validator(schema_path)
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.path) or "<record>"
            raise ValueError(f"record {index} ({record.get('record_id')}), {path}: {error.message}")
        record_id = record["record_id"]
        if record_id in seen:
            raise ValueError(f"duplicate record_id: {record_id}")
        seen.add(record_id)


def load_previous_records(output_dir: Path, layer_name: str, current_tag: str) -> dict[str, dict[str, Any]]:
    candidates = sorted(output_dir.glob(f"{layer_name}.*.geojson"), reverse=True)
    for candidate in candidates:
        if f".{current_tag}." in candidate.name:
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        result: dict[str, dict[str, Any]] = {}
        for feature in payload.get("features", []):
            properties = dict(feature.get("properties", {}))
            geometry = feature.get("geometry")
            if geometry:
                properties["longitude"], properties["latitude"] = geometry["coordinates"]
            else:
                properties["longitude"] = None
                properties["latitude"] = None
            result[properties["record_id"]] = properties
        return result
    return {}


def apply_history(records: list[dict[str, Any]], previous: dict[str, dict[str, Any]]) -> None:
    for record in records:
        earlier = previous.get(record["record_id"])
        if earlier:
            record["first_seen"] = earlier["first_seen"]


def write_geojson(path: Path, records: list[dict[str, Any]]) -> None:
    features = []
    for record in records:
        properties = {field: record[field] for field in CANONICAL_FIELDS if field not in ("latitude", "longitude")}
        geometry = None
        if record["latitude"] is not None:
            geometry = {
                "type": "Point",
                "coordinates": [record["longitude"], record["latitude"]],
            }
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    write_json(path, {"type": "FeatureCollection", "features": features})


def write_layer(
    *,
    records: list[dict[str, Any]],
    output_dir: Path,
    layer_name: str,
    retrieved_at: str,
    source_url: str,
    raw_path: Path,
    parser_name: str,
    schema_path: Path = SCHEMA_PATH,
    extra_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tag = retrieval_tag(retrieved_at)
    records.sort(key=lambda row: row["record_id"])
    apply_history(records, load_previous_records(output_dir, layer_name, tag))
    validate_records(records, schema_path)
    csv_path = output_dir / f"{layer_name}.{tag}.csv"
    geojson_path = output_dir / f"{layer_name}.{tag}.geojson"
    report_path = output_dir / f"{layer_name}.{tag}.report.json"
    write_geojson(geojson_path, records)
    report: dict[str, Any] = {
        "coordinate_methods": _counts(records, "coordinate_method"),
        "derived_files": {
            "csv": {
                "generator": f"make {repo_ref(csv_path)}",
                "path": repo_ref(csv_path),
                "source": repo_ref(geojson_path),
            }
        },
        "entity_types": _counts(records, "entity_type"),
        "generated_files": [repo_ref(geojson_path)],
        "geometry_null": sum(row["latitude"] is None for row in records),
        "layer": layer_name,
        "lifecycle_statuses": _counts(records, "lifecycle_status"),
        "parser": parser_name,
        "raw_source_ref": repo_ref(raw_path),
        "record_count": len(records),
        "retrieved_at": retrieved_at,
        "schema": repo_ref(schema_path),
        "schema_version": SCHEMA_VERSION,
        "source_sha256": sha256(raw_path),
        "source_url": source_url,
    }
    if extra_report:
        report.update(extra_report)
    write_json(report_path, report)
    return report


def canonical_record(**values: Any) -> dict[str, Any]:
    values = dict(values)
    values.setdefault("parent_record_id", None)
    values.setdefault("jurisdiction_scope", jurisdiction_scope(values.get("country_code")))
    values.setdefault("access_status", default_access_status(values.get("entity_type")))
    values.setdefault("service_scope", [])
    values.setdefault("coordinate_crs", "EPSG:4326" if values.get("latitude") is not None else None)
    missing = [field for field in CANONICAL_FIELDS if field not in values]
    extra = sorted(set(values) - set(CANONICAL_FIELDS))
    if missing or extra:
        raise ValueError(f"canonical record field mismatch: missing={missing}, extra={extra}")
    return {field: values[field] for field in CANONICAL_FIELDS}


def jurisdiction_scope(country_code: str | None) -> str:
    return {
        "CN": "mainland_china",
        "HK": "hong_kong",
        "MO": "macau",
        "TW": "taiwan",
    }.get(country_code or "", "other" if country_code else "unknown")


def default_access_status(entity_type: str | None) -> str:
    if entity_type in {"cloud_region", "availability_zone", "cloud_resource_pool", "local_zone"}:
        return "public"
    if entity_type in {"edge_pop", "regional_edge_cache", "data_center", "embedded_cache"}:
        return "not_applicable"
    return "unknown"


def legacy_coordinate_index(path: Path, city_column: str = "City", country_column: str = "Country") -> dict[str, tuple[float, float, str, str]]:
    """Index legacy coordinates by normalized city and city/country labels."""
    result: dict[str, tuple[float, float, str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            city = (row.get(city_column) or "").strip()
            country = (row.get(country_column) or "").strip()
            try:
                lat = float(row.get("Latitude") or row.get("latitude") or "")
                lon = float(row.get("Longitude") or row.get("longitude") or "")
            except ValueError:
                continue
            for label in (city, f"{city}, {country}"):
                if label:
                    result.setdefault(normalize_key(label), (lat, lon, city, country))
    return result


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()).strip()


_EN_TERRITORIES = Locale.parse("en").territories
_COUNTRY_BY_KEY = {
    normalize_key(name): (code, name)
    for code, name in _EN_TERRITORIES.items()
    if len(code) == 2 and code.isalpha()
}
_COUNTRY_ALIASES = {
    "bolivia": "BO",
    "czech republic": "CZ",
    "hong kong sar": "HK",
    "hong kong": "HK",
    "iran": "IR",
    "korea": "KR",
    "macao": "MO",
    "macau": "MO",
    "mexico": "MX",
    "palestine": "PS",
    "russia": "RU",
    "south korea": "KR",
    "kingdom of saudi arabia": "SA",
    "syria": "SY",
    "taiwan": "TW",
    "turkiye": "TR",
    "turkey": "TR",
    "uae": "AE",
    "uk": "GB",
    "united states of america": "US",
    "usa": "US",
    "venezuela": "VE",
    "vietnam": "VN",
}
_COUNTRY_CANONICAL_NAMES = {
    "HK": "Hong Kong",
    "MO": "Macao",
    "PS": "Palestine",
    "TW": "Taiwan",
}


def country_identity(value: str | None) -> tuple[str | None, str | None]:
    """Return an English territory name and ISO alpha-2 code when recognized."""
    if not value:
        return None, None
    cleaned = value.strip().strip(".")
    key = normalize_key(cleaned)
    code = _COUNTRY_ALIASES.get(key)
    if code:
        return _COUNTRY_CANONICAL_NAMES.get(code, str(_EN_TERRITORIES.get(code, cleaned))), code
    match = _COUNTRY_BY_KEY.get(key)
    if match:
        return _COUNTRY_CANONICAL_NAMES.get(str(match[0]), str(match[1])), str(match[0])
    return cleaned, None


def geojson_coordinate_index(path: Path, *name_fields: str) -> dict[str, tuple[float, float, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, tuple[float, float, dict[str, Any]]] = {}
    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not coordinates or len(coordinates) < 2:
            continue
        properties = feature.get("properties") or {}
        for field in name_fields:
            value = properties.get(field)
            if value:
                result.setdefault(normalize_key(str(value)), (float(coordinates[1]), float(coordinates[0]), properties))
    return result


def _counts(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = str(record[field])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
