#!/usr/bin/env python3
"""Fetch or normalize Google Edge and Google Data Center location layers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema/location.schema.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/google"
DEFAULT_RAW_DIR = REPO_ROOT / "data/raw/google"
DEFAULT_LEGACY_GOOGLE = REPO_ROOT / "data/Google_GGC_01-12-2023.csv"

PEERING_URL = "https://peering.google.com/static/js/site/modules/pages/infrastructure.html"
DATA_CENTER_URL = "https://datacenters.google/locations/"
SCHEMA_VERSION = "1.0.0"

CANONICAL_FIELDS = (
    "schema_version",
    "record_id",
    "aliases",
    "provider",
    "service",
    "entity_type",
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

COUNTRY_CODES = {
    "Argentina": "AR",
    "Australia": "AU",
    "Austria": "AT",
    "Belgium": "BE",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Canada": "CA",
    "Chile": "CL",
    "China": "CN",
    "Colombia": "CO",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Hong Kong": "HK",
    "Hungary": "HU",
    "India": "IN",
    "Indonesia": "ID",
    "Ireland": "IE",
    "Israel": "IL",
    "Italy": "IT",
    "Japan": "JP",
    "Kenya": "KE",
    "Malaysia": "MY",
    "Mexico": "MX",
    "Netherlands": "NL",
    "Nigeria": "NG",
    "Norway": "NO",
    "Oman": "OM",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Qatar": "QA",
    "Russia": "RU",
    "Saudi Arabia": "SA",
    "Singapore": "SG",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Taiwan": "TW",
    "Thailand": "TH",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "United States": "US",
    "Uruguay": "UY",
}

COUNTRY_NORMALIZATION = {
    "Korea, Republic of": "South Korea",
    "Russian Federation": "Russia",
    "Taiwan, Province of China": "Taiwan",
}

US_STATES = {
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
}

ADMIN_REGION_NAMES = {
    ("Andhra Pradesh", "India"),
    ("Selangor", "Malaysia"),
}

# The provider source contains coordinates only. Most labels are inherited from
# the legacy reverse-geocoded layer; these corrections express the metro semantics
# stated by Google rather than overly specific reverse-geocoder administrative names.
EDGE_LABEL_OVERRIDES: dict[tuple[float, float], dict[str, str]] = {
    (45.558, -73.73): {"metro": "Montreal"},
    (22.396, 114.109): {
        "city": "Hong Kong",
        "metro": "Hong Kong",
        "country": "Hong Kong",
        "country_code": "HK",
    },
    (6.524, 3.379): {"city": "Lagos", "metro": "Lagos"},
    (51.509, -0.125): {"city": "London", "metro": "London"},
    (-4.043, 39.668): {"city": "Mombasa", "metro": "Mombasa"},
    (28.635, 77.225): {"city": "Delhi", "metro": "Delhi"},
    (43.653, -79.383): {"city": "Toronto", "metro": "Toronto"},
    (-6.2, 106.817): {"city": "Jakarta", "metro": "Jakarta"},
    (32.166, 34.843): {"city": "Herzliya", "metro": "Tel Aviv"},
    (26.474, 49.797): {
        "city": "Dammam",
        "metro": "Dammam",
        "country": "Saudi Arabia",
        "country_code": "SA",
    },
}


def parse_args() -> argparse.Namespace:
    today = date.today().isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=("edge", "data-center", "all"),
        default="all",
        help="Layer to update (default: all).",
    )
    parser.add_argument("--retrieved-at", default=today)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--peering-source", type=Path)
    parser.add_argument("--data-center-source", type=Path)
    parser.add_argument("--legacy-google", type=Path, default=DEFAULT_LEGACY_GOOGLE)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch selected official sources before normalization.",
    )
    return parser.parse_args()


def retrieval_tag(retrieved_at: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved_at):
        raise ValueError(f"Invalid retrieval date: {retrieved_at!r}")
    return retrieved_at.replace("-", "")


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


def fetch(url: str, output: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "cloud-cdn-cache-updater/1.0 (+dataset research)"},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=30) as response:
        output.write_bytes(response.read())


def extract_balanced_array(text: str, key: str) -> list[list[float]]:
    key_start = text.find(f"{key}:")
    if key_start < 0:
        raise ValueError(f"Could not find {key!r} array in peering source")
    start = text.find("[", key_start)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                payload = re.sub(r",\s*]", "]", text[start : index + 1])
                value = json.loads(payload)
                if not isinstance(value, list):
                    raise ValueError(f"{key!r} did not decode to an array")
                return value
    raise ValueError(f"Unterminated {key!r} array in peering source")


def parse_peering_source(path: Path) -> dict[str, list[list[float]]]:
    text = path.read_text(encoding="utf-8")
    return {
        "datacenters": extract_balanced_array(text, "datacenters"),
        "pops": extract_balanced_array(text, "pops"),
        "ggcs": extract_balanced_array(text, "ggcs"),
    }


def parse_data_center_source(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r'<div id="data-centers-data"[^>]*>\s*(.*?)\s*</div>', text, re.DOTALL
    )
    if match is None:
        raise ValueError("Could not find data-centers-data payload")
    rows = json.loads(f"[{match.group(1)}]")
    if not isinstance(rows, list):
        raise ValueError("Data-center payload did not decode to an array")
    return rows


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_peering_manifest(
    path: Path, retrieved_at: str, arrays: dict[str, list[list[float]]]
) -> None:
    write_json(
        path.with_suffix(".provenance.json"),
        {
            "dataset": "Google peering infrastructure map",
            "raw_file": repo_ref(path),
            "raw_bytes": path.stat().st_size,
            "raw_sha256": sha256(path),
            "retrieved_at": retrieved_at,
            "source_published_at": None,
            "source_url": PEERING_URL,
            "source_scope": "provider_declared",
            "source_counts": {
                "data_centers": len(arrays["datacenters"]),
                "edge_pops": len(arrays["pops"]),
                "global_cache_nodes": len(arrays["ggcs"]),
            },
            "semantics": (
                "The edge POP coordinates represent metros where at least one edge "
                "POP is present, not individual facilities."
            ),
            "license_status": (
                "No standalone redistribution license is stated in the source snapshot; "
                "verify terms before republishing."
            ),
        },
    )


def write_data_center_manifest(
    path: Path, retrieved_at: str, rows: list[dict[str, Any]]
) -> None:
    write_json(
        path.with_suffix(".provenance.json"),
        {
            "dataset": "Google owned and operated data-center directory",
            "raw_file": repo_ref(path),
            "raw_bytes": path.stat().st_size,
            "raw_sha256": sha256(path),
            "retrieved_at": retrieved_at,
            "source_published_at": None,
            "source_url": DATA_CENTER_URL,
            "source_scope": "provider_declared",
            "source_counts": {
                "locations": len(rows),
                "in_development": sum(bool(row["inDevelopment"]) for row in rows),
                "not_marked_in_development": sum(
                    not bool(row["inDevelopment"]) for row in rows
                ),
                "locations_with_coordinates": sum(
                    row["latitude"] is not None and row["longitude"] is not None
                    for row in rows
                ),
            },
            "semantics": (
                "The directory describes locations Google says it owns and operates. "
                "The source marks development status explicitly but supplies coordinates "
                "for only a subset of entries."
            ),
            "license_status": (
                "No standalone redistribution license is stated in the source snapshot; "
                "verify terms before republishing."
            ),
        },
    )


def load_legacy_edge_labels(path: Path) -> dict[tuple[float, float], dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [
            row for row in csv.DictReader(handle) if row["Service Name"] == "pops"
        ]
    return {
        (round(float(row["Latitude"]), 3), round(float(row["Longitude"]), 3)): row
        for row in rows
    }


def normalized_country(value: str) -> tuple[str, str]:
    country = COUNTRY_NORMALIZATION.get(value, value)
    try:
        return country, COUNTRY_CODES[country]
    except KeyError as error:
        raise ValueError(f"No ISO country-code mapping for {value!r}") from error


def edge_record_id(metro: str, country_code: str, latitude: float, longitude: float) -> str:
    identifier = f"{slug(metro)}-{country_code.lower()}" if country_code else ""
    if not identifier:
        identifier = f"{str(latitude).replace('.', '-')}-{str(longitude).replace('.', '-')}"
    return f"google:edge_pop:{identifier}"


def build_edge_records(
    points: list[list[float]],
    source_path: Path,
    legacy_path: Path,
    retrieved_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    legacy = load_legacy_edge_labels(legacy_path)
    source_digest = sha256(source_path)
    records: list[dict[str, Any]] = []
    matched_legacy_coordinates = 0

    for index, point in enumerate(points):
        if len(point) != 2:
            raise ValueError(f"Invalid edge coordinate at index {index}: {point!r}")
        latitude, longitude = float(point[0]), float(point[1])
        coordinate_key = (round(latitude, 3), round(longitude, 3))
        legacy_row = legacy.get(coordinate_key)
        override = EDGE_LABEL_OVERRIDES.get(coordinate_key, {})

        if legacy_row is not None:
            matched_legacy_coordinates += 1
            city = legacy_row["City"].strip() or None
            metro = city
            country, country_code = normalized_country(legacy_row["Country"].strip())
            label_method = "legacy_coordinate_match"
        else:
            city = None
            metro = None
            country = None
            country_code = None
            label_method = "curated_coordinate_match"

        city = override.get("city", city)
        metro = override.get("metro", metro)
        country = override.get("country", country)
        country_code = override.get("country_code", country_code)
        if override and legacy_row is not None:
            label_method = "legacy_coordinate_match_with_curated_normalization"
        if not metro:
            metro = f"{latitude:.6f}, {longitude:.6f}"
        if country and not country_code:
            country_code = COUNTRY_CODES[country]
        display_location = (
            metro if not country or metro == country else f"{metro}, {country}"
        )

        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_id": edge_record_id(
                    metro, country_code or "", latitude, longitude
                ),
                "aliases": [],
                "provider": "Google",
                "service": "google_edge",
                "entity_type": "edge_pop",
                "source_collection": "google_peering_infrastructure",
                "source_record_id": None,
                "name": display_location,
                "site_code": None,
                "lifecycle_status": "operational",
                "source_scope": "provider_declared",
                "city": city,
                "metro": metro,
                "subdivision": None,
                "country": country,
                "country_code": country_code,
                "latitude": latitude,
                "longitude": longitude,
                "location_precision": "metro",
                "coordinate_method": "provider",
                "source_url": PEERING_URL,
                "raw_source_ref": repo_ref(source_path),
                "source_sha256": source_digest,
                "source_published_at": None,
                "retrieved_at": retrieved_at,
                "first_seen": retrieved_at,
                "last_seen": retrieved_at,
                "confidence": "medium",
                "properties": {
                    "representation": "metro_with_one_or_more_edge_pops",
                    "provider_coordinate_index": index,
                    "label_method": label_method,
                    "label_source_ref": (
                        repo_ref(legacy_path) if legacy_row is not None else None
                    ),
                },
            }
        )

    report = {
        "legacy_edge_record_count": len(legacy),
        "current_edge_record_count": len(records),
        "legacy_coordinate_match_count": matched_legacy_coordinates,
        "current_source_only_count": len(records) - matched_legacy_coordinates,
        "current_source_only_coordinates": [
            [record["latitude"], record["longitude"]]
            for record in records
            if record["properties"]["label_source_ref"] is None
        ],
        "semantic_note": (
            "Each record is a provider-declared metro where one or more edge POPs "
            "exist; record counts are not facility counts."
        ),
    }
    return records, report


def data_center_location_parts(location: str) -> tuple[str | None, str | None, str, str]:
    if location == "Singapore":
        return "Singapore", None, "Singapore", "SG"

    if "," in location:
        locality, suffix = (part.strip() for part in location.rsplit(",", 1))
        if suffix in US_STATES:
            return locality, suffix, "United States", "US"
        country, country_code = normalized_country(suffix)
        if (locality, country) in ADMIN_REGION_NAMES:
            return None, locality, country, country_code
        return locality, None, country, country_code

    for state in sorted(US_STATES, key=len, reverse=True):
        if location == state:
            return None, state, "United States", "US"
        if location.endswith(f" {state}"):
            return None, state, "United States", "US"
    raise ValueError(f"Could not determine country for data-center location {location!r}")


def data_center_precision(location: str, has_coordinates: bool) -> str:
    if not has_coordinates:
        return "unknown"
    regional_markers = ("County", "Central ", "Northern ", "The Lowcountry")
    if location in {"Andhra Pradesh, India", "Indiana"} or any(
        marker in location for marker in regional_markers
    ):
        return "region"
    return "city"


def clean_source_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def build_data_center_records(
    source_rows: list[dict[str, Any]], source_path: Path, retrieved_at: str
) -> list[dict[str, Any]]:
    source_digest = sha256(source_path)
    records: list[dict[str, Any]] = []

    for source_row in source_rows:
        location = clean_source_text(str(source_row["location"]))
        city, subdivision, country, country_code = data_center_location_parts(location)
        latitude = source_row["latitude"]
        longitude = source_row["longitude"]
        has_coordinates = latitude is not None and longitude is not None
        detail_page = clean_source_text(str(source_row.get("detailPage", "")))
        detail_url = urljoin(DATA_CENTER_URL, detail_page) if detail_page else None
        topics = [clean_source_text(str(value)) for value in source_row.get("topics", [])]
        identifier = f"{slug(location)}-{country_code.lower()}"

        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_id": f"google:data_center:{identifier}",
                "aliases": [],
                "provider": "Google",
                "service": "google_data_centers",
                "entity_type": "data_center",
                "source_collection": "google_data_centers_directory",
                "source_record_id": None,
                "name": location,
                "site_code": None,
                "lifecycle_status": (
                    "in_development"
                    if bool(source_row["inDevelopment"])
                    else "operational"
                ),
                "source_scope": "provider_declared",
                "city": city,
                "metro": None,
                "subdivision": subdivision,
                "country": country,
                "country_code": country_code,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "location_precision": data_center_precision(location, has_coordinates),
                "coordinate_method": "provider" if has_coordinates else "unknown",
                "source_url": DATA_CENTER_URL,
                "raw_source_ref": repo_ref(source_path),
                "source_sha256": source_digest,
                "source_published_at": None,
                "retrieved_at": retrieved_at,
                "first_seen": retrieved_at,
                "last_seen": retrieved_at,
                "confidence": "high",
                "properties": {
                    "representation": "provider_directory_location",
                    "continent": clean_source_text(str(source_row["continent"])),
                    "in_development": bool(source_row["inDevelopment"]),
                    "detail_page": detail_url,
                    "short_description": clean_source_text(
                        str(source_row.get("shortDescription", ""))
                    ),
                    "topics": topics,
                },
            }
        )
    return records


def load_previous_records(
    output_dir: Path, prefix: str, current_path: Path
) -> dict[str, dict[str, str]]:
    candidates = sorted(
        path for path in output_dir.glob(f"{prefix}.*.csv") if path != current_path
    )
    if not candidates:
        return {}
    with candidates[-1].open(newline="", encoding="utf-8-sig") as handle:
        return {row["record_id"]: row for row in csv.DictReader(handle)}


def inherit_history(
    records: list[dict[str, Any]], previous: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    current_ids = {record["record_id"] for record in records}
    for record in records:
        older = previous.get(record["record_id"])
        if older and older.get("first_seen"):
            record["first_seen"] = min(record["first_seen"], older["first_seen"])
    return sorted(current_ids - set(previous)), sorted(set(previous) - current_ids)


def validator_for(schema_path: Path) -> Draft202012Validator:
    with schema_path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(
    records: list[dict[str, Any]], validator: Draft202012Validator
) -> None:
    ids = [record["record_id"] for record in records]
    duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate record IDs: {', '.join(duplicates)}")
    for index, record in enumerate(records):
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
        if errors:
            details = "; ".join(error.message for error in errors[:5])
            raise ValueError(f"Schema validation failed at record {index}: {details}")
        if record["first_seen"] > record["last_seen"]:
            raise ValueError(f"first_seen exceeds last_seen for {record['record_id']}")


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({field: csv_value(record[field]) for field in CANONICAL_FIELDS})


def write_geojson(
    path: Path,
    records: list[dict[str, Any]],
    service: str,
    retrieved_at: str,
    source_url: str,
) -> None:
    features = []
    for record in records:
        properties = {
            field: record[field]
            for field in CANONICAL_FIELDS
            if field not in {"latitude", "longitude"}
        }
        geometry = (
            {
                "type": "Point",
                "coordinates": [record["longitude"], record["latitude"]],
            }
            if record["latitude"] is not None
            else None
        )
        features.append(
            {
                "type": "Feature",
                "id": record["record_id"],
                "properties": properties,
                "geometry": geometry,
            }
        )
    write_json(
        path,
        {
            "type": "FeatureCollection",
            "metadata": {
                "schema_version": SCHEMA_VERSION,
                "provider": "Google",
                "service": service,
                "retrieved_at": retrieved_at,
                "source_url": source_url,
            },
            "features": features,
        },
    )


def write_layer(
    *,
    output_dir: Path,
    prefix: str,
    records: list[dict[str, Any]],
    service: str,
    source_url: str,
    raw_source: Path,
    retrieved_at: str,
    validator: Draft202012Validator,
    comparison: dict[str, Any],
) -> None:
    tag = retrieval_tag(retrieved_at)
    csv_path = output_dir / f"{prefix}.{tag}.csv"
    geojson_path = output_dir / f"{prefix}.{tag}.geojson"
    report_path = output_dir / f"{prefix}.{tag}.report.json"
    previous = load_previous_records(output_dir, prefix, csv_path)
    added_ids, removed_ids = inherit_history(records, previous)
    validate_records(records, validator)
    write_csv(csv_path, records)
    write_geojson(geojson_path, records, service, retrieved_at, source_url)
    write_json(
        report_path,
        {
            "dataset": service,
            "schema_version": SCHEMA_VERSION,
            "retrieved_at": retrieved_at,
            "record_count": len(records),
            "records_with_coordinates": sum(
                record["latitude"] is not None for record in records
            ),
            "records_without_coordinates": sum(
                record["latitude"] is None for record in records
            ),
            "lifecycle_status_counts": dict(
                sorted(Counter(record["lifecycle_status"] for record in records).items())
            ),
            "raw_source_ref": repo_ref(raw_source),
            "raw_source_sha256": sha256(raw_source),
            "csv_file": repo_ref(csv_path),
            "csv_sha256": sha256(csv_path),
            "geojson_file": repo_ref(geojson_path),
            "geojson_sha256": sha256(geojson_path),
            "previous_normalized_record_count": len(previous),
            "added_record_ids": added_ids if previous else [],
            "removed_record_ids": removed_ids,
            "legacy_comparison": comparison,
        },
    )


def main() -> None:
    args = parse_args()
    tag = retrieval_tag(args.retrieved_at)
    peering_source = args.peering_source or (
        args.raw_dir / f"peering-infrastructure.{tag}.html"
    )
    data_center_source = args.data_center_source or (
        args.raw_dir / f"data-centers-directory.{tag}.html"
    )
    selected_edge = args.dataset in {"edge", "all"}
    selected_data_centers = args.dataset in {"data-center", "all"}

    if args.fetch and selected_edge:
        fetch(PEERING_URL, peering_source)
    if args.fetch and selected_data_centers:
        fetch(DATA_CENTER_URL, data_center_source)

    validator = validator_for(args.schema)
    if selected_edge:
        if not peering_source.exists():
            raise FileNotFoundError(
                f"Missing {peering_source}; pass --fetch or --peering-source"
            )
        arrays = parse_peering_source(peering_source)
        write_peering_manifest(peering_source, args.retrieved_at, arrays)
        edge_records, comparison = build_edge_records(
            arrays["pops"], peering_source, args.legacy_google, args.retrieved_at
        )
        write_layer(
            output_dir=args.output_dir,
            prefix="edge",
            records=edge_records,
            service="google_edge",
            source_url=PEERING_URL,
            raw_source=peering_source,
            retrieved_at=args.retrieved_at,
            validator=validator,
            comparison=comparison,
        )
        print(f"Generated Google Edge: {len(edge_records)} records")

    if selected_data_centers:
        if not data_center_source.exists():
            raise FileNotFoundError(
                f"Missing {data_center_source}; pass --fetch or --data-center-source"
            )
        source_rows = parse_data_center_source(data_center_source)
        write_data_center_manifest(data_center_source, args.retrieved_at, source_rows)
        data_center_records = build_data_center_records(
            source_rows, data_center_source, args.retrieved_at
        )
        with args.legacy_google.open(newline="", encoding="utf-8-sig") as handle:
            legacy_data_centers = sum(
                row["Service Name"] == "datacenters" for row in csv.DictReader(handle)
            )
        comparison = {
            "legacy_peering_map_data_center_count": legacy_data_centers,
            "current_owned_data_center_directory_count": len(data_center_records),
            "semantic_note": (
                "The legacy count came from the peering infrastructure map. The new "
                "directory has a broader owned-location scope and must not be treated as "
                "a row-for-row replacement."
            ),
        }
        write_layer(
            output_dir=args.output_dir,
            prefix="data-centers",
            records=data_center_records,
            service="google_data_centers",
            source_url=DATA_CENTER_URL,
            raw_source=data_center_source,
            retrieved_at=args.retrieved_at,
            validator=validator,
            comparison=comparison,
        )
        print(f"Generated Google Data Centers: {len(data_center_records)} records")


if __name__ == "__main__":
    main()
