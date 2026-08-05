#!/usr/bin/env python3
"""Normalize authoritative provider location lists into the canonical schema."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Callable

from bs4 import BeautifulSoup

from location_common import (
    REPO_ROOT,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    canonical_record,
    country_identity,
    fetch,
    normalize_key,
    repo_ref,
    retrieval_tag,
    sha256,
    slug,
    write_layer,
    write_provenance,
)


SOURCES = {
    "cloudflare": (
        "https://www.cloudflarestatus.com/api/v2/components.json",
        "data/raw/cloudflare/components.{tag}.json",
        "application/json",
        None,
    ),
    "azure": (
        "https://learn.microsoft.com/en-us/azure/frontdoor/edge-locations-by-region",
        "data/raw/microsoft/frontdoor-locations.{tag}.html",
        "text/html",
        "2025-09-25",
    ),
    "azure-codes": (
        "https://learn.microsoft.com/en-us/azure/frontdoor/edge-locations-by-abbreviation",
        "data/raw/microsoft/frontdoor-codes.{tag}.html",
        "text/html",
        "2025-12-18",
    ),
    "cloudfront": (
        "https://aws.amazon.com/cloudfront/features/",
        "data/raw/aws/cloudfront-features.{tag}.html",
        "text/html",
        None,
    ),
    "local-zones": (
        "https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html",
        "data/raw/aws/available-local-zones.{tag}.html",
        "text/html",
        None,
    ),
    "fastly": (
        "https://www.fastly.com/documentation/guides/getting-started/concepts/using-fastlys-global-pop-network/",
        "data/raw/fastly/global-pop-network.{tag}.html",
        "text/html",
        None,
    ),
    "cachefly": (
        "https://www.cachefly.com/network-map/",
        "data/raw/cachefly/network-map.{tag}.html",
        "text/html",
        "2026-03-24",
    ),
    "alibaba": (
        "https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones",
        "data/raw/alibaba/regions-and-zones.{tag}.html",
        "text/html",
        "2026-07-01",
    ),
    "tencent": (
        "https://intl.cloud.tencent.com/document/product/416/64284?lang=en",
        "data/raw/tencent/regions-and-zones.{tag}.html",
        "text/html",
        "2026-02-12",
    ),
}

DATASETS = ("cloudflare", "azure", "azure-codes", "cloudfront", "local-zones", "fastly", "cachefly", "alibaba", "tencent")

LEGACY = {
    "cloudflare": REPO_ROOT / "data/cloudflare_data_centers_30-07-2023.csv",
    "azure": REPO_ROOT / "data/microsoft_frontdoor_pops_01-12-2023.csv",
    "cloudfront": REPO_ROOT / "data/Amazon_Edge_30-07-2023.csv",
    "local-zones": REPO_ROOT / "data/amazon_localzones_11-07-2023.csv",
    "fastly": REPO_ROOT / "data/fastly_POPs_10-07-2023.csv",
    "cachefly": REPO_ROOT / "data/Cachefly_30-07-2023.csv",
}


class CoordinateResolver:
    """Conservative city-centroid inheritance from a named legacy layer."""

    def __init__(self, csv_path: Path | None = None, geojson_path: Path | None = None):
        self.exact: dict[str, tuple[float, float, str, str]] = {}
        self.city_values: dict[str, set[tuple[float, float, str, str]]] = defaultdict(set)
        self.by_id: dict[str, tuple[float, float, dict[str, Any]]] = {}
        if csv_path:
            self._load_csv(csv_path)
        if geojson_path:
            self._load_geojson(geojson_path)

    def _add(self, city: str, country: str, lat: float, lon: float) -> None:
        value = (lat, lon, city, country)
        self.exact.setdefault(normalize_key(f"{city}, {country}"), value)
        self.city_values[normalize_key(city)].add(value)

    def _load_csv(self, path: Path) -> None:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                city = (row.get("City") or "").strip()
                country = (row.get("Country") or "").strip()
                try:
                    lat, lon = float(row["Latitude"]), float(row["Longitude"])
                except (KeyError, TypeError, ValueError):
                    continue
                if city:
                    self._add(city, country, lat, lon)

    def _load_geojson(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            geometry = feature.get("geometry") or {}
            coordinates = geometry.get("coordinates")
            if geometry.get("type") != "Point" or not coordinates:
                continue
            props = feature.get("properties") or {}
            for field in ("region", "region_id"):
                if props.get(field):
                    self.by_id[normalize_key(str(props[field]))] = (float(coordinates[1]), float(coordinates[0]), props)
                    parenthetical = re.match(r"^(.*?)\s*\(([^)]+)\)", str(props[field]))
                    if parenthetical:
                        country_raw, derived_city = parenthetical.groups()
                        country, _ = country_identity(country_raw)
                        self._add(derived_city, country or country_raw, float(coordinates[1]), float(coordinates[0]))
            city = str(props.get("city") or "")
            country = str(props.get("country") or "")
            if city:
                self._add(city, country, float(coordinates[1]), float(coordinates[0]))

    def resolve(self, city: str | None, country: str | None, *aliases: str | None) -> tuple[float | None, float | None]:
        for identifier in aliases:
            if identifier and normalize_key(identifier) in self.by_id:
                lat, lon, _ = self.by_id[normalize_key(identifier)]
                return lat, lon
        if city and country:
            exact = self.exact.get(normalize_key(f"{city}, {country}"))
            if exact:
                return exact[0], exact[1]
        for candidate in (city, *aliases):
            if not candidate:
                continue
            values = self.city_values.get(normalize_key(candidate), set())
            points = {(value[0], value[1]) for value in values}
            if len(points) == 1:
                return next(iter(points))
        return None, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("all", *DATASETS), default="all")
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT, help="Root beneath which generated data directories are written.")
    return parser.parse_args()


def source_path(key: str, retrieved_at: str) -> Path:
    return REPO_ROOT / SOURCES[key][1].format(tag=retrieval_tag(retrieved_at))


def base_record(
    *,
    prefix: str,
    identifier: str,
    provider: str,
    service: str,
    entity_type: str,
    collection: str,
    source_record_id: str | None,
    name: str,
    site_code: str | None,
    lifecycle_status: str,
    city: str | None,
    metro: str | None,
    subdivision: str | None,
    country: str | None,
    country_code: str | None,
    latitude: float | None,
    longitude: float | None,
    location_precision: str,
    coordinate_method: str,
    source_key: str,
    retrieved_at: str,
    confidence: str,
    properties: dict[str, Any],
    aliases: list[str] | None = None,
    parent_record_id: str | None = None,
    jurisdiction_scope: str | None = None,
    access_status: str | None = None,
    service_scope: list[str] | None = None,
    coordinate_crs: str | None = None,
) -> dict[str, Any]:
    source_url, _, _, published = SOURCES[source_key]
    raw_path = source_path(source_key, retrieved_at)
    return canonical_record(
        schema_version=SCHEMA_VERSION,
        record_id=f"{prefix}:{entity_type}:{slug(identifier)}",
        aliases=sorted(set(aliases or [])),
        provider=provider,
        service=service,
        entity_type=entity_type,
        parent_record_id=parent_record_id,
        **({"jurisdiction_scope": jurisdiction_scope} if jurisdiction_scope is not None else {}),
        **({"access_status": access_status} if access_status is not None else {}),
        service_scope=service_scope or [],
        source_collection=collection,
        source_record_id=source_record_id,
        name=name,
        site_code=site_code,
        lifecycle_status=lifecycle_status,
        source_scope="provider_declared",
        city=city,
        metro=metro,
        subdivision=subdivision,
        country=country,
        country_code=country_code,
        latitude=latitude,
        longitude=longitude,
        location_precision=location_precision,
        coordinate_method=coordinate_method,
        coordinate_crs=coordinate_crs if coordinate_crs is not None else ("EPSG:4326" if latitude is not None else None),
        source_url=source_url,
        raw_source_ref=repo_ref(raw_path),
        source_sha256=sha256(raw_path),
        source_published_at=published,
        retrieved_at=retrieved_at,
        first_seen=retrieved_at,
        last_seen=retrieved_at,
        confidence=confidence,
        properties=properties,
    )


def parse_cloudflare(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(source_path("cloudflare", retrieved_at).read_text(encoding="utf-8"))
    components = payload["components"]
    geographic_groups = {
        component["id"]: component["name"]
        for component in components
        if component.get("group") and component.get("name") in {
            "Africa", "Asia", "Europe", "Latin America & the Caribbean", "Middle East", "North America", "Oceania"
        }
    }
    resolver = CoordinateResolver(csv_path=LEGACY["cloudflare"])
    records = []
    for component in components:
        if component.get("group") or component.get("group_id") not in geographic_groups:
            continue
        match = re.match(r"^(.*?)\s*-\s*\(([A-Z0-9]+)\)$", component["name"])
        if not match:
            raise ValueError(f"unrecognized Cloudflare component: {component['name']!r}")
        location, code = match.groups()
        parts = [part.strip() for part in location.split(",")]
        city, country_raw = parts[0], parts[-1]
        subdivision = ", ".join(parts[1:-1]) or None
        country, country_code = country_identity(country_raw)
        lat, lon = resolver.resolve(city, country, location)
        records.append(base_record(
            prefix="cloudflare", identifier=code, provider="Cloudflare", service="cloudflare_network",
            entity_type="edge_pop", collection="cloudflare_status_components", source_record_id=component["id"],
            name=f"{city} ({code})", site_code=code, lifecycle_status="operational", city=city, metro=city,
            subdivision=subdivision, country=country, country_code=country_code, latitude=lat, longitude=lon,
            location_precision="city", coordinate_method="legacy" if lat is not None else "unknown",
            source_key="cloudflare", retrieved_at=retrieved_at, confidence="high",
            properties={"component_status": component["status"], "region_group": geographic_groups[component["group_id"]]},
        ))
    return records, {"geographic_group_count": len(geographic_groups), "status_api_component_count": len(components)}


def _azure_location(value: str) -> tuple[str, str | None, str | None, int]:
    count_match = re.search(r"\s*\((\d+)\)$", value)
    count = int(count_match.group(1)) if count_match else 1
    value = re.sub(r"\s*\(\d+\)$", "", value).strip()
    parts = [part.strip() for part in value.split(",")]
    city = parts[0]
    country_raw = parts[-1]
    subdivision = ", ".join(parts[1:-1]) or None
    country, _ = country_identity(country_raw)
    return city, subdivision, country, count


def parse_azure(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    location_soup = BeautifulSoup(source_path("azure", retrieved_at).read_bytes(), "html.parser")
    code_soup = BeautifulSoup(source_path("azure-codes", retrieved_at).read_bytes(), "html.parser")
    codes: dict[str, list[str]] = defaultdict(list)
    code_rows = 0
    for row in code_soup.find("table").find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) == 3:
            code_rows += 1
            code, location, _ = cells
            codes[normalize_key(location.split(",")[0])].extend(part.strip() for part in code.split("/") if part.strip())
    resolver = CoordinateResolver(csv_path=LEGACY["azure"])
    records = []
    commercial_count = 0
    government_count = 0
    for table_index, table in enumerate(location_soup.find_all("table")[:2]):
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            region_group = cells[0].get_text(" ", strip=True)
            for raw_location in cells[1].get_text("\n", strip=True).splitlines():
                city, subdivision, country, asset_count = _azure_location(raw_location)
                _, country_code = country_identity(country)
                lat, lon = resolver.resolve(city, country)
                pop_codes = sorted(set(codes.get(normalize_key(city), [])))
                government = table_index == 1
                if government:
                    government_count += asset_count
                else:
                    commercial_count += asset_count
                identifier = f"{country_code or country}-{subdivision or ''}-{city}"
                records.append(base_record(
                    prefix="microsoft", identifier=identifier, provider="Microsoft", service="azure_front_door",
                    entity_type="edge_pop", collection="azure_front_door_metros", source_record_id=None,
                    name=city, site_code=pop_codes[0] if pop_codes else None, lifecycle_status="operational",
                    city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
                    latitude=lat, longitude=lon, location_precision="city",
                    coordinate_method="legacy" if lat is not None else "unknown", source_key="azure",
                    retrieved_at=retrieved_at, confidence="high",
                    properties={
                        "asset_count": asset_count,
                        "cloud": "us_government" if government else "commercial",
                        "pop_codes": pop_codes,
                        "pop_codes_raw_source_ref": repo_ref(source_path("azure-codes", retrieved_at)),
                        "pop_codes_source_sha256": sha256(source_path("azure-codes", retrieved_at)),
                        "region_group": region_group,
                    },
                ))
    return records, {
        "code_identifier_count": sum(len(v) for v in codes.values()),
        "code_table_row_count": code_rows,
        "commercial_asset_count_from_table": commercial_count,
        "commercial_metro_count_from_table": sum(not row["properties"]["cloud"] == "us_government" for row in records),
        "government_asset_count_from_table": government_count,
        "government_metro_count_from_table": sum(row["properties"]["cloud"] == "us_government" for row in records),
        "page_claims": {"commercial_asset_count": 192, "commercial_metro_count": 109, "government_asset_count": 4},
        "pop_code_auxiliary_source": {
            "raw_source_ref": repo_ref(source_path("azure-codes", retrieved_at)),
            "sha256": sha256(source_path("azure-codes", retrieved_at)),
            "source_url": SOURCES["azure-codes"][0],
        },
    }


def parse_azure_codes(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("azure-codes", retrieved_at).read_bytes(), "html.parser")
    resolver = CoordinateResolver(csv_path=LEGACY["azure"])
    records = []
    for row in soup.find("table").find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) != 3:
            continue
        code, location, region = cells
        parts = [part.strip() for part in location.split(",")]
        city = parts[0]
        country_raw = parts[-1]
        subdivision = ", ".join(parts[1:-1]) or None
        country, country_code = country_identity(country_raw)
        lat, lon = resolver.resolve(city, country)
        atomic_codes = [part.strip() for part in code.split("/") if part.strip()]
        records.append(base_record(
            prefix="microsoft", identifier=f"frontdoor-code-{code}", provider="Microsoft",
            service="azure_front_door", entity_type="edge_pop", collection="azure_front_door_abbreviations",
            source_record_id=code, name=f"{location} ({code})", site_code=code, lifecycle_status="operational",
            city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
            latitude=lat, longitude=lon, location_precision="city",
            coordinate_method="legacy" if lat is not None else "unknown", source_key="azure-codes",
            retrieved_at=retrieved_at, confidence="high",
            properties={"atomic_abbreviations": atomic_codes, "azure_region": region, "directory_scope": "pop_abbreviation"},
        ))
    return records, {
        "atomic_abbreviation_count": sum(len(row["properties"]["atomic_abbreviations"]) for row in records),
        "directory_row_count": len(records),
        "location_label_count": len({(row["city"], row["subdivision"], row["country"]) for row in records}),
        "unit_warning": "Directory rows and metro asset counts are different source units and must not be added.",
    }


def _cloudfront_html(retrieved_at: str) -> str:
    soup = BeautifulSoup(source_path("cloudfront", retrieved_at).read_bytes(), "html.parser")
    for script in soup.find_all("script", type="application/json"):
        try:
            payload = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        stack: list[Any] = [payload]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                if value.get("itemHeading") == "Points of Presence (PoPs)":
                    return str(value["itemLongLoc"])
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
    raise ValueError("CloudFront POP location block not found")


def parse_cloudfront(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_html = _cloudfront_html(retrieved_at).replace(
        "Portugal:</b> LisbonRomania: Bucharest (3)</p>",
        "Portugal:</b> Lisbon</p><p><b>Romania:</b> Bucharest (3)</p>",
    )
    soup = BeautifulSoup(source_html, "html.parser")
    resolver = CoordinateResolver(csv_path=LEGACY["cloudfront"])
    records = []
    region_group: str | None = None
    total_assets = 0
    for paragraph in soup.find_all("p"):
        bold = paragraph.find("b")
        if not bold:
            continue
        heading = bold.get_text(" ", strip=True).strip()
        if heading == "Embedded Points of Presence (PoPs)":
            break
        content = paragraph.get_text(" ", strip=True)[len(heading):].strip()
        if not content:
            region_group = heading.rstrip(":")
            continue
        if not heading.endswith(":"):
            # The source uniquely formats Singapore as a country/location row
            # without a colon; other unpunctuated bold values are region headings.
            singapore = re.fullmatch(r"Singapore\s*\((\d+)\)", paragraph.get_text(" ", strip=True))
            if singapore:
                country, country_code = country_identity("Singapore")
                city, asset_count = "Singapore", int(singapore.group(1))
                lat, lon = resolver.resolve(city, country)
                total_assets += asset_count
                records.append(base_record(
                    prefix="aws", identifier="cloudfront-sg-singapore", provider="Amazon Web Services",
                    service="aws_cloudfront", entity_type="edge_pop", collection="aws_cloudfront_features",
                    source_record_id=None, name=city, site_code=None, lifecycle_status="operational", city=city,
                    metro=city, subdivision=None, country=country, country_code=country_code, latitude=lat,
                    longitude=lon, location_precision="city", coordinate_method="legacy" if lat is not None else "unknown",
                    source_key="cloudfront", retrieved_at=retrieved_at, confidence="high",
                    properties={"asset_count": asset_count, "infrastructure_class": "standard_pop", "region_group": region_group},
                ))
            else:
                region_group = heading
            continue
        country_raw = heading[:-1].strip()
        country, country_code = country_identity(country_raw)
        for token in [part.strip() for part in content.split(",") if part.strip()]:
            match = re.match(r"^(.*?)(?:\s+\((\d+)\)|\s+(\d+)\))?$", token)
            if not match:
                raise ValueError(f"unrecognized CloudFront location: {token!r}")
            city = match.group(1).strip()
            source_city = city
            city = {"Tel Avivi": "Tel Aviv"}.get(city, city)
            asset_count = int(match.group(2) or match.group(3) or 1)
            total_assets += asset_count
            lat, lon = resolver.resolve(city, country)
            records.append(base_record(
                prefix="aws", identifier=f"cloudfront-{country_code or country}-{city}", provider="Amazon Web Services",
                service="aws_cloudfront", entity_type="edge_pop", collection="aws_cloudfront_features",
                source_record_id=None, name=city, site_code=None, lifecycle_status="operational", city=city, metro=city,
                subdivision=None, country=country, country_code=country_code, latitude=lat, longitude=lon,
                location_precision="city", coordinate_method="legacy" if lat is not None else "unknown",
                source_key="cloudfront", retrieved_at=retrieved_at, confidence="high",
                properties={"asset_count": asset_count, "infrastructure_class": "standard_pop", "region_group": region_group},
                aliases=[source_city] if source_city != city else [],
            ))
    return records, {"standard_pop_asset_count_from_city_list": total_assets, "provider_aggregate_counts": {"regional_edge_caches": 15, "standard_pops": "750+", "embedded_pops": "1140+"}, "unlocated_infrastructure_classes": ["regional_edge_cache", "embedded_pop"]}


def _local_zone_place(group_name: str, geography: str) -> tuple[str | None, str | None, str | None]:
    match = re.search(r"\(([^)]+)\)", group_name)
    city = match.group(1) if match else None
    geography_parts = [part.strip() for part in geography.split(",")]
    country_raw = geography_parts[-1]
    country, code = country_identity(country_raw)
    return city, country, code


def parse_local_zones(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("local-zones", retrieved_at).read_bytes(), "html.parser")
    resolver = CoordinateResolver(csv_path=LEGACY["local-zones"])
    records = []
    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find("tr").find_all(["th", "td"])]
        if headers[:3] != ["Local Zone Group Long Name", "Local Zone Name", "Local Zone ID"]:
            continue
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(cells) != 7:
                continue
            group_name, zone_name, zone_id, network_border, parent_region, parent_zone_id, geography = cells
            city, country, country_code = _local_zone_place(group_name, geography)
            lat, lon = resolver.resolve(city, country, zone_name)
            records.append(base_record(
                prefix="aws", identifier=zone_id, provider="Amazon Web Services", service="aws_local_zones",
                entity_type="local_zone", collection="aws_available_local_zones", source_record_id=zone_id,
                name=group_name, site_code=zone_name, lifecycle_status="operational", city=city, metro=city,
                subdivision=None, country=country, country_code=country_code, latitude=lat, longitude=lon,
                location_precision="city", coordinate_method="legacy" if lat is not None else "unknown",
                source_key="local-zones", retrieved_at=retrieved_at, confidence="high",
                parent_record_id=f"aws:cloud_region:{slug(parent_region)}",
                properties={"geography": geography, "network_border_group": network_border, "parent_region": parent_region, "parent_zone_id": parent_zone_id},
            ))
    return records, {"available_zone_id_count": len(records), "local_zone_group_count": len({row["name"] for row in records})}


def parse_fastly(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("fastly", retrieved_at).read_bytes(), "html.parser")
    tables = soup.find_all("table")
    groupings: dict[str, list[str]] = {}
    for row in tables[1].find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) == 3:
            groupings[cells[1]] = [part.strip() for part in cells[2].split(",")]
    resolver = CoordinateResolver(csv_path=LEGACY["fastly"])
    records = []
    for row in tables[0].find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) != 3:
            continue
        location, pop_id, coordinate_text = cells
        coordinate_match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", coordinate_text)
        if not coordinate_match:
            raise ValueError(f"Fastly coordinate missing for {pop_id}")
        lat, lon = map(float, coordinate_match.groups())
        country = None
        country_code = None
        values = resolver.city_values.get(normalize_key(location), set())
        countries = {value[3] for value in values if value[3]}
        if len(countries) == 1:
            country, country_code = country_identity(next(iter(countries)))
        records.append(base_record(
            prefix="fastly", identifier=pop_id, provider="Fastly", service="fastly_network", entity_type="edge_pop",
            collection="fastly_pop_directory", source_record_id=pop_id, name=f"{location} ({pop_id})", site_code=pop_id,
            lifecycle_status="operational", city=location, metro=location, subdivision=None, country=country,
            country_code=country_code, latitude=lat, longitude=lon, location_precision="city", coordinate_method="provider",
            source_key="fastly", retrieved_at=retrieved_at, confidence="high",
            properties={"approximate_coordinates": True, "sites_spanned": groupings.get(pop_id, [])},
        ))
    return records, {"grouped_pop_identifier_count": len(groupings), "location_label_count": len({row["city"] for row in records})}


_CACHEFLY_CORRECTIONS = {"Buenos Aries": "Buenos Aires", "Kula Lumpur": "Kuala Lumpur", "Kiev": "Kyiv"}


def parse_cachefly(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("cachefly", retrieved_at).read_bytes(), "html.parser")
    resolver = CoordinateResolver(csv_path=LEGACY["cachefly"])
    records = []
    for paragraph in soup.find_all("p"):
        strong = paragraph.find("strong")
        if not strong or not strong.get_text(" ", strip=True).endswith(":"):
            continue
        country_raw = strong.get_text(" ", strip=True)[:-1]
        country, country_code = country_identity(country_raw)
        if country_code is None:
            continue
        full_text = paragraph.get_text(" ", strip=True)
        locations = full_text[len(strong.get_text(" ", strip=True)):].strip()
        for raw_city in [part.strip() for part in re.split(r"\s*[–—]\s*", locations) if part.strip()]:
            planned = "coming soon" in raw_city.lower()
            private = "▴" in raw_city
            premium = "●" in raw_city
            source_label = re.sub(r"\s*\(coming soon\)\s*", "", raw_city, flags=re.I).replace("▴", "").replace("●", "").strip()
            city = _CACHEFLY_CORRECTIONS.get(source_label, source_label)
            lat, lon = resolver.resolve(city, country, source_label)
            aliases = [source_label] if source_label != city else []
            records.append(base_record(
                prefix="cachefly", identifier=f"{country_code}-{city}", provider="CacheFly", service="cachefly_network",
                entity_type="edge_pop", collection="cachefly_network_map", source_record_id=None, name=city, site_code=None,
                lifecycle_status="planned" if planned else "operational", city=city, metro=city, subdivision=None,
                country=country, country_code=country_code, latitude=lat, longitude=lon, location_precision="city",
                coordinate_method="legacy" if lat is not None else "unknown", source_key="cachefly",
                retrieved_at=retrieved_at, confidence="high", aliases=aliases,
                properties={"service_tier": "private" if private else "premium" if premium else "standard"},
            ))
    declared = sum(
        int(match.group(1))
        for heading in soup.find_all("h3")
        if (match := re.search(r"(\d+)\s+Locations", heading.get_text(" ", strip=True)))
    )
    return records, {
        "location_count_from_list": len(records),
        "page_heading_declared_location_count": declared,
        "private_location_count": sum(row["properties"]["service_tier"] == "private" for row in records),
        "premium_location_count": sum(row["properties"]["service_tier"] == "premium" for row in records),
    }


def _alibaba_place(region_name: str) -> tuple[str | None, str | None, str | None, list[str]]:
    aliases: list[str] = []
    match = re.match(r"^(.*?)\s*\((.*?)\)$", region_name)
    if match:
        country_raw, city = match.groups()
        city = re.sub(r"\s*-\s*(?:Local|Partner) Region.*$", "", city).strip()
        if city == "Hong Kong":
            return "Hong Kong", "Hong Kong", "HK", aliases
        country_raw = {"China": "China", "US": "United States", "UK": "United Kingdom", "UAE": "United Arab Emirates", "SAU": "Saudi Arabia"}.get(country_raw, country_raw)
        country, code = country_identity(country_raw)
        return city, country, code, aliases
    country, code = country_identity(region_name)
    if code:
        return region_name if code in {"SG"} else None, country, code, aliases
    return None, None, None, aliases


def _cloud_records(
    *,
    provider_key: str,
    retrieved_at: str,
    regions: list[dict[str, Any]],
    resolver: CoordinateResolver,
    place: Callable[[str], tuple[str | None, str | None, str | None, list[str]]],
) -> list[dict[str, Any]]:
    provider = "Alibaba Cloud" if provider_key == "alibaba" else "Tencent Cloud"
    prefix = provider_key
    records = []
    for region in regions:
        city, country, country_code, aliases = place(region["region_name"])
        lat, lon = resolver.resolve(city, country, region["region_id"])
        closing = "Closing Down" in region["region_name"]
        region_status = "inactive" if closing else "operational"
        region_properties = region.get("properties", {})
        region_access = region_properties.get("access_status", "public")
        region_service_scope = region_properties.get("service_scope", ["public_cloud"])
        records.append(base_record(
            prefix=prefix, identifier=region["region_id"], provider=provider, service=f"{provider_key}_cloud",
            entity_type="cloud_region", collection=f"{provider_key}_regions_and_zones", source_record_id=region["region_id"],
            name=region["region_name"], site_code=region["region_id"], lifecycle_status=region_status, city=city, metro=city,
            subdivision=None, country=country, country_code=country_code, latitude=lat, longitude=lon,
            location_precision="region", coordinate_method="legacy" if lat is not None else "unknown",
            source_key=provider_key, retrieved_at=retrieved_at, confidence="high", aliases=aliases,
            access_status=region_access, service_scope=region_service_scope,
            properties={"declared_zone_count": region["declared_zone_count"], **region_properties},
        ))
        parent_record_id = f"{prefix}:cloud_region:{slug(region['region_id'])}"
        for zone in region["zones"]:
            restricted = bool(zone.get("properties", {}).get("sales_restricted"))
            records.append(base_record(
                prefix=prefix, identifier=zone["zone_id"], provider=provider, service=f"{provider_key}_cloud",
                entity_type="availability_zone", collection=f"{provider_key}_regions_and_zones", source_record_id=zone["zone_id"],
                name=zone["zone_name"], site_code=zone["zone_id"], lifecycle_status=region_status, city=city, metro=city,
                subdivision=None, country=country, country_code=country_code, latitude=lat, longitude=lon,
                location_precision="region", coordinate_method="legacy" if lat is not None else "unknown",
                source_key=provider_key, retrieved_at=retrieved_at, confidence="high",
                parent_record_id=parent_record_id,
                access_status=region_access if region_access != "public" else "sales_restricted" if restricted else "public",
                service_scope=region_service_scope,
                properties={"parent_region_id": region["region_id"], **zone.get("properties", {})},
            ))
    return records


def parse_alibaba(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("alibaba", retrieved_at).read_bytes(), "html.parser")
    regions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for table in soup.find_all("table")[1:3]:
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(cells) == 5:
                region_name, region_id, declared, zone_name, zone_id = cells
                current = {"region_name": region_name, "region_id": region_id, "declared_zone_count": int(declared), "zones": []}
                regions.append(current)
            elif len(cells) == 2 and current:
                zone_name, zone_id = cells
            else:
                continue
            current["zones"].append({"zone_name": zone_name, "zone_id": zone_id, "properties": {}})
    resolver = CoordinateResolver(geojson_path=REPO_ROOT / "data/alibaba_cloud_data_centers_2.geojson")
    records = _cloud_records(provider_key="alibaba", retrieved_at=retrieved_at, regions=regions, resolver=resolver, place=_alibaba_place)
    return records, {"public_region_count": len(regions), "availability_zone_count": sum(len(region["zones"]) for region in regions), "excluded_specialized_tables": ["financial cloud", "government cloud"]}


_TENCENT_COUNTRY_BY_CITY = {
    "Beijing": "China", "Shanghai": "China", "Nanjing": "China", "Guangzhou": "China", "Chengdu": "China",
    "Chongqing": "China", "Zhongwei": "China", "Shenzhen": "China", "Singapore": "Singapore",
    "Jakarta": "Indonesia", "Seoul": "South Korea", "Tokyo": "Japan", "Bangkok": "Thailand",
    "Saudi Arabia": "Saudi Arabia", "São Paulo": "Brazil", "Silicon Valley": "United States",
    "Virginia": "United States", "Frankfurt": "Germany",
}


def _tencent_place(region_name: str) -> tuple[str | None, str | None, str | None, list[str]]:
    if region_name.startswith("Hong Kong"):
        return "Hong Kong", "Hong Kong", "HK", []
    match = re.search(r"\(([^)]+)\)", region_name)
    city = match.group(1) if match else next((value for value in _TENCENT_COUNTRY_BY_CITY if value in region_name), None)
    country_raw = _TENCENT_COUNTRY_BY_CITY.get(city or "")
    country, code = country_identity(country_raw)
    return city, country, code, []


def parse_tencent(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("tencent", retrieved_at).read_bytes(), "html.parser")
    regions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for table in soup.find_all("table")[1:3]:
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True).replace("\ufeff", "").strip() for cell in row.find_all(["th", "td"])]
            if len(cells) != 5 or not cells[3] or not cells[4]:
                continue
            region_name, region_id, declared, zone_name, zone_id = cells
            if region_id:
                specialized_financial = "Finance" in region_name
                specialized_automotive = "Self-driving Cloud" in region_name
                current = {
                    "region_name": region_name,
                    "region_id": region_id,
                    "declared_zone_count": int(declared),
                    "zones": [],
                    "properties": {
                        "access_status": "dedicated" if specialized_financial or specialized_automotive else "public",
                        "service_scope": ["financial_cloud"] if specialized_financial else ["automotive_cloud"] if specialized_automotive else ["public_cloud"],
                        "specialized_financial_region": specialized_financial,
                        "specialized_automotive_region": specialized_automotive,
                    },
                }
                regions.append(current)
            if current:
                restricted = zone_name.endswith("*")
                current["zones"].append({"zone_name": zone_name.rstrip(" *"), "zone_id": zone_id, "properties": {"sales_restricted": restricted}})
    resolver = CoordinateResolver(geojson_path=REPO_ROOT / "data/tencent_cloud_data_centers.geojson")
    records = _cloud_records(provider_key="tencent", retrieved_at=retrieved_at, regions=regions, resolver=resolver, place=_tencent_place)
    return records, {
        "region_count": len(regions),
        "availability_zone_count": sum(len(region["zones"]) for region in regions),
        "sales_restricted_zone_count": sum(zone["properties"]["sales_restricted"] for region in regions for zone in region["zones"]),
        "specialized_region_count": sum(region["properties"]["service_scope"] != ["public_cloud"] for region in regions),
        "specialized_availability_zone_count": sum(len(region["zones"]) for region in regions if region["properties"]["service_scope"] != ["public_cloud"]),
    }


PARSERS = {
    "cloudflare": parse_cloudflare,
    "azure": parse_azure,
    "azure-codes": parse_azure_codes,
    "cloudfront": parse_cloudfront,
    "local-zones": parse_local_zones,
    "fastly": parse_fastly,
    "cachefly": parse_cachefly,
    "alibaba": parse_alibaba,
    "tencent": parse_tencent,
}

OUTPUTS = {
    "cloudflare": ("data/cloudflare", "edge"),
    "azure": ("data/microsoft", "front-door"),
    "azure-codes": ("data/microsoft", "front-door-codes"),
    "cloudfront": ("data/aws", "cloudfront"),
    "local-zones": ("data/aws", "local-zones"),
    "fastly": ("data/fastly", "pops"),
    "cachefly": ("data/cachefly", "locations"),
    "alibaba": ("data/alibaba", "regions-and-zones"),
    "tencent": ("data/tencent", "regions-and-zones"),
}


def main() -> None:
    args = parse_args()
    retrieval_tag(args.retrieved_at)
    selected = DATASETS if args.dataset == "all" else (args.dataset,)
    source_keys = set(selected)
    if "azure" in selected:
        source_keys.add("azure-codes")
    for key in sorted(source_keys):
        url, _, media_type, published = SOURCES[key]
        raw_path = source_path(key, args.retrieved_at)
        if args.fetch:
            fetch(url, raw_path)
        if not raw_path.exists():
            raise FileNotFoundError(f"raw snapshot missing: {raw_path}; run with --fetch")
        write_provenance(
            raw_path, source_url=url, retrieved_at=args.retrieved_at, media_type=media_type,
            source_published_at=published,
            notes="Immutable provider source snapshot used by scripts/update_authoritative.py; provider HTML/API content may be copyrighted and is retained for reproducibility.",
        )
    summaries = {}
    for dataset in selected:
        records, extra = PARSERS[dataset](args.retrieved_at)
        output_dir, layer_name = OUTPUTS[dataset]
        source_key = dataset
        report = write_layer(
            records=records, output_dir=args.output_root / output_dir, layer_name=layer_name,
            retrieved_at=args.retrieved_at, source_url=SOURCES[source_key][0], raw_path=source_path(source_key, args.retrieved_at),
            parser_name=f"update_authoritative.py:{dataset}", schema_path=args.schema, extra_report=extra,
        )
        summaries[dataset] = report
        if dataset in {"alibaba", "tencent"}:
            mainland_records = [
                row for row in records
                if row["jurisdiction_scope"] == "mainland_china"
                and (dataset != "tencent" or row["service_scope"] == ["public_cloud"])
            ]
            mainland_report = write_layer(
                records=mainland_records,
                output_dir=args.output_root / output_dir,
                layer_name="mainland-regions-and-zones",
                retrieved_at=args.retrieved_at,
                source_url=SOURCES[source_key][0],
                raw_path=source_path(source_key, args.retrieved_at),
                parser_name=f"update_authoritative.py:{dataset}:mainland",
                schema_path=args.schema,
                extra_report={
                    "derived_from_layer": f"{output_dir}/{layer_name}",
                    "jurisdiction_filter": "mainland_china",
                    "service_scope_filter": "public_cloud" if dataset == "tencent" else None,
                    "cloud_region_count": sum(row["entity_type"] == "cloud_region" for row in mainland_records),
                    "availability_zone_count": sum(row["entity_type"] == "availability_zone" for row in mainland_records),
                },
            )
            summaries[f"{dataset}-mainland"] = mainland_report
            if dataset == "tencent":
                specialized_records = [
                    row for row in records
                    if row["jurisdiction_scope"] == "mainland_china" and row["service_scope"] != ["public_cloud"]
                ]
                specialized_report = write_layer(
                    records=specialized_records,
                    output_dir=args.output_root / output_dir,
                    layer_name="mainland-specialized-regions-and-zones",
                    retrieved_at=args.retrieved_at,
                    source_url=SOURCES[source_key][0],
                    raw_path=source_path(source_key, args.retrieved_at),
                    parser_name="update_authoritative.py:tencent:mainland-specialized",
                    schema_path=args.schema,
                    extra_report={
                        "derived_from_layer": f"{output_dir}/{layer_name}",
                        "jurisdiction_filter": "mainland_china",
                        "service_scope_filter": ["financial_cloud", "automotive_cloud"],
                        "cloud_region_count": sum(row["entity_type"] == "cloud_region" for row in specialized_records),
                        "availability_zone_count": sum(row["entity_type"] == "availability_zone" for row in specialized_records),
                    },
                )
                summaries["tencent-mainland-specialized"] = specialized_report
    print(json.dumps({key: {"record_count": value["record_count"], "geometry_null": value["geometry_null"]} for key, value in summaries.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
