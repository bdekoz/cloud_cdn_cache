#!/usr/bin/env python3
"""Normalize the public, partial city map from the June 2026 CDN study."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from location_common import (
    REPO_ROOT,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    canonical_record,
    country_identity,
    fetch,
    repo_ref,
    retrieval_tag,
    sha256,
    slug,
    write_layer,
    write_provenance,
)


STUDY_URL = "https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/"
MAP_URL = "https://www.google.com/maps/d/kml?mid=1AHRJ8wfAVk2nHYWuO8Mojs0zp__9V0o&forcekml=1"
PUBLISHED_AT = "2026-06-06"
KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

PROVIDERS = {
    "Google GGC": {"provider": "Google", "dataset": "Google GGC"},
    "Meta FNA": {"provider": "Meta", "dataset": "Facebook/Meta FNA"},
    "Netflix OCA": {"provider": "Netflix", "dataset": "Netflix OCA"},
}

ARTICLE_COUNTRY_COUNTS = {
    "Google GGC": 215,
    "Meta FNA": 204,
    "Netflix OCA": 181,
}

KML_COUNTRY_CODES = {
    "Antigua and Barbuda": "AG",
    "Bonaire, Sint Eustatius and Saba": "BQ",
    "Bosnia and Herzegovina": "BA",
    "Cabo Verde": "CV",
    "Congo (DRC)": "CD",
    "Congo Republic": "CG",
    "Ivory Coast": "CI",
    "Myanmar": "MM",
    "Saint Kitts and Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Pierre and Miquelon": "PM",
    "Saint Vincent and the Grenadines": "VC",
    "São Tomé and Príncipe": "ST",
    "The Netherlands": "NL",
    "Trinidad and Tobago": "TT",
    "Turks and Caicos Islands": "TC",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def raw_path(retrieved_at: str) -> Path:
    return REPO_ROOT / "data/raw/observations" / f"global-cdn-mapping.{retrieval_tag(retrieved_at)}.kml"


def extended_data(placemark: ET.Element) -> dict[str, str]:
    return {
        item.get("name", ""): (item.findtext("kml:value", default="", namespaces=KML_NS) or "").strip()
        for item in placemark.findall("kml:ExtendedData/kml:Data", KML_NS)
    }


def identity_hash(*values: object) -> str:
    value = "\x1f".join(str(item) for item in values)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def parse_kml(
    path: Path, retrieved_at: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = ET.parse(path).getroot()
    digest = sha256(path)
    records: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    folder_counts: dict[str, int] = {}
    provider_raw_counts: Counter[str] = Counter()
    country_sets: dict[str, set[str]] = defaultdict(set)
    city_sets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    asn_sets: dict[str, set[int]] = defaultdict(set)
    missing_city_counts: Counter[str] = Counter()

    for folder in root.findall(".//kml:Folder", KML_NS):
        folder_name = (folder.findtext("kml:name", default="", namespaces=KML_NS) or "").strip()
        provider_key = folder_name.split(" (", 1)[0]
        if provider_key not in PROVIDERS:
            raise ValueError(f"unexpected map folder: {folder_name!r}")
        placemarks = folder.findall("kml:Placemark", KML_NS)
        folder_counts[folder_name] = len(placemarks)
        provider_raw_counts[provider_key] += len(placemarks)
        config = PROVIDERS[provider_key]

        for position, placemark in enumerate(placemarks, start=1):
            values = extended_data(placemark)
            try:
                asn = int(float(values["asn"]))
                latitude = float(values["latitude"])
                longitude = float(values["longitude"])
            except (KeyError, ValueError) as error:
                rejected.append({
                    "folder": folder_name,
                    "position": position,
                    "reason": "invalid_required_value",
                    "values": values,
                })
                continue
            if not 1 <= asn <= 4_294_967_295:
                rejected.append({
                    "asn": values.get("asn"),
                    "folder": folder_name,
                    "position": position,
                    "reason": "invalid_asn",
                })
                continue
            if not (math.isfinite(latitude) and -90 <= latitude <= 90 and math.isfinite(longitude) and -180 <= longitude <= 180):
                rejected.append({
                    "asn": asn,
                    "folder": folder_name,
                    "position": position,
                    "reason": "invalid_coordinate",
                })
                continue

            point = placemark.findtext("kml:Point/kml:coordinates", default="", namespaces=KML_NS).strip()
            point_values = [part.strip() for part in point.split(",")]
            if (
                len(point_values) < 2
                or not math.isclose(float(point_values[0]), longitude, abs_tol=1e-9)
                or not math.isclose(float(point_values[1]), latitude, abs_tol=1e-9)
            ):
                raise ValueError(f"KML Point/ExtendedData coordinate disagreement in {folder_name} row {position}")

            source_country = values.get("country", "").strip()
            country, country_code = country_identity(source_country)
            if not country_code and source_country in KML_COUNTRY_CODES:
                country, country_code = source_country, KML_COUNTRY_CODES[source_country]
            if not country_code:
                raise ValueError(f"unrecognized country in KML: {source_country!r}")
            source_city = values.get("city", "").strip()
            city = None if source_city in {"", "\\N"} else source_city
            if city is None:
                missing_city_counts[provider_key] += 1
            as_name = (placemark.findtext("kml:name", default="", namespaces=KML_NS) or "").strip()
            if not as_name:
                raise ValueError(f"blank AS name for AS{asn} in {folder_name} row {position}")

            record_hash = identity_hash(provider_key, asn, source_city, source_country, latitude, longitude)
            records.append(canonical_record(
                schema_version=SCHEMA_VERSION,
                record_id=f"observation:observed_presence:cdn-city-{slug(provider_key)}-{record_hash}",
                aliases=[],
                provider=str(config["provider"]),
                service="cdn_mapping_city_observation",
                entity_type="observed_presence",
                parent_record_id=None,
                jurisdiction_scope={"CN": "mainland_china", "HK": "hong_kong", "MO": "macau", "TW": "taiwan"}.get(country_code, "other"),
                access_status="not_applicable",
                service_scope=["tls_measurement", "maxmind_geolocation"],
                source_collection="anurag_bhatia_cdn_mapping_map_2026",
                source_record_id=f"{provider_key}:{asn}:{source_city}:{latitude}:{longitude}",
                name=f"{provider_key} observation — AS{asn} — {city or country}",
                site_code=None,
                lifecycle_status="unknown",
                source_scope="observed",
                city=city,
                metro=None,
                subdivision=None,
                country=country,
                country_code=country_code,
                latitude=latitude,
                longitude=longitude,
                location_precision="city" if city else "unknown",
                coordinate_method="geocoded",
                coordinate_crs="EPSG:4326",
                source_url=MAP_URL,
                raw_source_ref=repo_ref(path),
                source_sha256=digest,
                source_published_at=PUBLISHED_AT,
                retrieved_at=retrieved_at,
                first_seen=PUBLISHED_AT,
                last_seen=PUBLISHED_AT,
                confidence="medium",
                properties={
                    "as_name": as_name,
                    "asn": asn,
                    "dataset": config["dataset"],
                    "folder": folder_name,
                    "geolocation_database": "MaxMind GeoIP Lite",
                    "geolocation_is_not_facility": True,
                    "map_is_partial": True,
                    "measurement_method": "routed-prefix TLS certificate scan followed by MaxMind geolocation",
                    "observation_scope": "asn_city_geolocation",
                    "observed_at": PUBLISHED_AT,
                    "source_city": source_city,
                    "source_country": source_country,
                    "study_url": STUDY_URL,
                },
            ))
            country_sets[provider_key].add(source_country)
            city_sets[provider_key].add((source_city, source_country))
            asn_sets[provider_key].add(asn)

    provider_counts = Counter(record["properties"]["dataset"] for record in records)
    valid_country_counts = {provider: len(country_sets[provider]) for provider in PROVIDERS}
    return records, {
        "accepted_record_count": len(records),
        "article_country_counts": ARTICLE_COUNTRY_COUNTS,
        "country_coverage_gaps": {
            provider: ARTICLE_COUNTRY_COUNTS[provider] - valid_country_counts[provider]
            for provider in PROVIDERS
        },
        "folder_counts": dict(sorted(folder_counts.items())),
        "folders_at_2000_record_limit": sorted(name for name, count in folder_counts.items() if count == 2000),
        "license_status": "not stated in source; review before downstream redistribution",
        "missing_city_counts": dict(sorted(missing_city_counts.items())),
        "partiality_basis": "The public map contains only Google GGC, Meta FNA, and Netflix OCA. Its Google and Meta country counts are lower than the article aggregates, and several folders contain exactly 2,000 placemarks.",
        "provider_counts": dict(sorted(provider_counts.items())),
        "provider_raw_counts": dict(sorted(provider_raw_counts.items())),
        "raw_record_count": sum(provider_raw_counts.values()),
        "rejected_record_count": len(rejected),
        "rejections_by_reason": dict(sorted(Counter(row["reason"] for row in rejected).items())),
        "rejected_records": rejected,
        "unique_asn_counts": {provider: len(asn_sets[provider]) for provider in PROVIDERS},
        "unique_city_country_counts": {provider: len(city_sets[provider]) for provider in PROVIDERS},
        "valid_country_counts": valid_country_counts,
    }


def main() -> None:
    args = parse_args()
    path = raw_path(args.retrieved_at)
    if args.fetch:
        fetch(MAP_URL, path)
    if not path.exists():
        raise FileNotFoundError(path)
    write_provenance(
        path,
        source_url=MAP_URL,
        retrieved_at=args.retrieved_at,
        media_type="application/vnd.google-earth.kml+xml",
        source_published_at=PUBLISHED_AT,
        notes="Public My Maps KML embedded by the June 2026 study. It is a partial MaxMind city-geolocation observation layer, not a facility inventory. No explicit redistribution license was found.",
    )
    records, audit = parse_kml(path, args.retrieved_at)
    report = write_layer(
        records=records,
        output_dir=args.output_root / "data/observations",
        layer_name="cdn-mapping-cities",
        retrieved_at=args.retrieved_at,
        source_url=MAP_URL,
        raw_path=path,
        parser_name="update_observation_cities.py",
        schema_path=args.schema,
        extra_report={
            "geometry_policy": "Coordinates are MaxMind city-geolocation evidence and never facility or POP coordinates.",
            **audit,
        },
    )
    print(json.dumps({
        "record_count": report["record_count"],
        "provider_counts": report["provider_counts"],
        "rejected_record_count": report["rejected_record_count"],
        "valid_country_counts": report["valid_country_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
