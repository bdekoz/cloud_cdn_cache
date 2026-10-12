#!/usr/bin/env python3
"""Normalize the reviewed hyperscaler region, zone, and facility directories."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Callable

from bs4 import BeautifulSoup

from location_common import (
    REPO_ROOT,
    SCHEMA_CONTRACT_VERSION,
    SCHEMA_PATH,
    canonical_record,
    country_identity,
    fetch,
    normalize_key,
    repo_ref,
    retrieval_tag,
    sha256,
    slug,
    write_layer,
    write_json,
    write_provenance,
)


SOURCES: dict[str, dict[str, str | None]] = {
    "coreweave-directory": {
        "url": "https://docs.coreweave.com/platform/regions/all-availability-zones.md",
        "path": "data/raw/coreweave/all-availability-zones.{tag}.md",
        "media_type": "text/markdown",
        "published": "2026-04-17",
    },
    "coreweave-matrix": {
        "url": "https://docs.coreweave.com/platform/instances/availability-matrix.md",
        "path": "data/raw/coreweave/availability-matrix.{tag}.md",
        "media_type": "text/markdown",
        "published": "2026-05-01",
    },
    "aws-az": {
        "url": "https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.md",
        "path": "data/raw/aws/availability-zones.{tag}.md",
        "media_type": "text/markdown",
        "published": None,
    },
    "aws-global": {
        "url": "https://aws.amazon.com/about-aws/global-infrastructure/regions_az/",
        "path": "data/raw/aws/global-regions-and-zones.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "aws-china": {
        "url": "https://docs.amazonaws.cn/en_us/aws/latest/userguide/ARNs.html",
        "path": "data/raw/aws/china-regions.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "aws-govcloud": {
        "url": "https://docs.aws.amazon.com/govcloud-us/latest/UserGuide/using-govcloud.html",
        "path": "data/raw/aws/govcloud-regions.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "aws-eusc": {
        "url": "https://aws.amazon.com/blogs/aws/opening-the-aws-european-sovereign-cloud/",
        "path": "data/raw/aws/european-sovereign-cloud.{tag}.html",
        "media_type": "text/html",
        "published": "2026-01-14",
    },
    "google-compute": {
        "url": "https://docs.cloud.google.com/compute/docs/regions-zones",
        "path": "data/raw/google/compute-regions-zones.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "google-ai-zones": {
        "url": "https://docs.cloud.google.com/compute/docs/regions-zones/ai-zones",
        "path": "data/raw/google/compute-ai-zones.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "google-gpu-zones": {
        "url": "https://docs.cloud.google.com/compute/docs/regions-zones/gpu-regions-zones",
        "path": "data/raw/google/compute-gpu-regions-zones.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "gcping-endpoints": {
        "url": "https://global.gcping.com/api/endpoints",
        "path": "data/raw/google/gcping-endpoints.{tag}.json",
        "media_type": "application/json",
        "published": None,
    },
    "gcping-methodology": {
        "url": "https://gcping.com/",
        "path": "data/raw/google/gcping.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "azure-regions": {
        "url": "https://learn.microsoft.com/en-us/azure/reliability/regions-list",
        "path": "data/raw/microsoft/regions-list.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "oci-regions": {
        "url": "https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm",
        "path": "data/raw/oracle/regions.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "ibm-locations": {
        "url": "https://cloud.ibm.com/docs/overview?topic=overview-locations",
        "path": "data/raw/ibm/locations.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "ibm-closures": {
        "url": "https://cloud.ibm.com/docs/support?topic=support-dc-closure",
        "path": "data/raw/ibm/data-center-closures.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "meta-data-centers": {
        "url": "https://datacenters.atmeta.com/all-locations/",
        "path": "data/raw/meta/data-center-locations.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
}

DATASET_SOURCES = {
    "coreweave": ("coreweave-directory", "coreweave-matrix"),
    "aws": ("aws-az", "aws-global", "aws-china", "aws-govcloud", "aws-eusc"),
    "google": ("google-compute",),
    "azure": ("azure-regions",),
    "oci": ("oci-regions",),
    "ibm": ("ibm-locations", "ibm-closures"),
    "meta": ("meta-data-centers",),
}

OUTPUTS = {
    "coreweave": ("data/coreweave", "regions-and-zones", "coreweave-directory"),
    "aws": ("data/aws", "regions-and-zones", "aws-az"),
    "google": ("data/google", "cloud-regions-and-zones", "google-compute"),
    "azure": ("data/microsoft", "cloud-regions", "azure-regions"),
    "oci": ("data/oracle", "cloud-regions", "oci-regions"),
    "ibm": ("data/ibm", "regions-and-zones", "ibm-locations"),
    "ibm-classic": ("data/ibm", "classic-data-centers", "ibm-locations"),
    "meta": ("data/meta", "data-centers", "meta-data-centers"),
}

US_STATES = {
    normalize_key(name): name
    for name in (
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
        "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
        "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
        "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
        "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
        "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
        "Wisconsin", "Wyoming",
    )
}

CANADIAN_PROVINCES = {
    normalize_key(name): name
    for name in (
        "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
        "Nova Scotia", "Ontario", "Prince Edward Island", "Quebec", "Québec", "Saskatchewan",
    )
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("all", *DATASET_SOURCES), default="all")
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument(
        "--google-enrichment", action="store_true",
        help="Join retained GCPing endpoints, GPU availability and explicit AI zones to Google Cloud.",
    )
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def source_path(key: str, retrieved_at: str) -> Path:
    template = str(SOURCES[key]["path"])
    return REPO_ROOT / template.format(tag=retrieval_tag(retrieved_at))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200a", " ").replace("\xa0", " ")).strip()


def markdown_label(value: str) -> str:
    return clean_text(re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value))


def markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def place_from_label(
    value: str,
    *,
    country_hint: str | None = None,
) -> tuple[str | None, str | None, str | None, str | None]:
    parts = [clean_text(part) for part in value.split(",") if clean_text(part)]
    if parts and parts[-1] in {"APAC", "Europe", "Middle East", "North America", "South America"}:
        parts.pop()
    country: str | None = None
    country_code: str | None = None
    if parts:
        candidate, candidate_code = country_identity(parts[-1])
        if candidate_code:
            country, country_code = candidate, candidate_code
            parts.pop()
    if country_code is None and country_hint:
        country, country_code = country_identity(country_hint)
    city: str | None = None
    subdivision: str | None = None
    if country_code == "US" and parts:
        last_key = normalize_key(parts[-1])
        if last_key in US_STATES or re.fullmatch(r"[A-Z]{2}", parts[-1]):
            subdivision = US_STATES.get(last_key, parts[-1])
            parts.pop()
    elif country_code == "CA" and parts:
        last_key = normalize_key(parts[-1])
        if last_key in CANADIAN_PROVINCES:
            subdivision = CANADIAN_PROVINCES[last_key]
            parts.pop()
    elif len(parts) > 1:
        subdivision = parts[-1]
        parts = parts[:-1]
    if parts:
        city = parts[0]
    elif country_code in {"HK", "SG"}:
        city = country
    return city, subdivision, country, country_code


def base_record(
    *,
    source_key: str,
    retrieved_at: str,
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
    access_status: str,
    service_scope: list[str],
    city: str | None,
    metro: str | None,
    subdivision: str | None,
    country: str | None,
    country_code: str | None,
    location_precision: str,
    properties: dict[str, Any],
    aliases: list[str] | None = None,
    parent_record_id: str | None = None,
    confidence: str = "high",
) -> dict[str, Any]:
    info = SOURCES[source_key]
    raw_path = source_path(source_key, retrieved_at)
    return canonical_record(
        schema_version=SCHEMA_CONTRACT_VERSION,
        record_id=f"{prefix}:{entity_type}:{slug(identifier)}",
        aliases=sorted(set(aliases or [])),
        provider=provider,
        service=service,
        entity_type=entity_type,
        parent_record_id=parent_record_id,
        jurisdiction_scope={"CN": "mainland_china", "HK": "hong_kong", "MO": "macau", "TW": "taiwan"}.get(
            country_code or "", "other" if country_code else "unknown"
        ),
        access_status=access_status,
        service_scope=service_scope,
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
        latitude=None,
        longitude=None,
        location_precision=location_precision,
        coordinate_method="unknown",
        coordinate_crs=None,
        source_url=str(info["url"]),
        raw_source_ref=repo_ref(raw_path),
        source_sha256=sha256(raw_path),
        source_published_at=info["published"],
        retrieved_at=retrieved_at,
        first_seen=retrieved_at,
        last_seen=retrieved_at,
        confidence=confidence,
        properties=properties,
    )


def parse_coreweave_matrix(retrieved_at: str) -> dict[str, dict[str, list[str]]]:
    text = source_path("coreweave-matrix", retrieved_at).read_text(encoding="utf-8")
    result: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"gpu_instance_types": [], "cpu_instance_types": []})
    for heading, field in (("## GPU instances", "gpu_instance_types"), ("## CPU instances", "cpu_instance_types")):
        section = text.split(heading, 1)[1]
        if "\n## " in section:
            section = section.split("\n## ", 1)[0]
        lines = section.splitlines()
        table_start = next(index for index, line in enumerate(lines) if line.startswith("|"))
        headers = [markdown_label(cell) for cell in markdown_cells(lines[table_start])]
        assert len(headers) == 19 and len(set(headers[1:])) == 18
        for line in lines[table_start + 2:]:
            if not line.startswith("|"):
                break
            cells = markdown_cells(line)
            assert len(cells) == len(headers)
            instance = markdown_label(cells[0])
            for zone, availability in zip(headers[1:], cells[1:]):
                if availability == "Yes":
                    result[zone][field].append(instance)
    return result


def parse_coreweave(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = source_path("coreweave-directory", retrieved_at).read_text(encoding="utf-8")
    matrix = parse_coreweave_matrix(retrieved_at)
    matrix_path = source_path("coreweave-matrix", retrieved_at)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = clean_text(line[4:])
        elif current and line.startswith("| ["):
            cells = markdown_cells(line)
            assert len(cells) == 4
            grouped[current].append({
                "zone": markdown_label(cells[0]),
                "location": clean_text(cells[1]),
                "access": clean_text(cells[2]),
                "object_storage": clean_text(cells[3]),
            })
    assert len(grouped) == 7
    assert sum(map(len, grouped.values())) == 56
    records: list[dict[str, Any]] = []
    for super_region, zones in grouped.items():
        places = [place_from_label(zone["location"]) for zone in zones]
        countries = {(place[2], place[3]) for place in places}
        country, country_code = next(iter(countries)) if len(countries) == 1 else (None, None)
        access_counts = Counter(zone["access"] for zone in zones)
        storage_count = sum(zone["object_storage"] == "Yes" for zone in zones)
        parent_id = f"coreweave:super_region:{slug(super_region)}"
        records.append(base_record(
            source_key="coreweave-directory", retrieved_at=retrieved_at,
            prefix="coreweave", identifier=super_region, provider="CoreWeave", service="coreweave_cloud",
            entity_type="super_region", collection="coreweave_availability_zones",
            source_record_id=super_region, name=super_region, site_code=super_region,
            lifecycle_status="operational", access_status="unknown",
            service_scope=sorted({"compute", *(("ai_object_storage",) if storage_count else ())}),
            city=None, metro=None, subdivision=None, country=country, country_code=country_code,
            location_precision="region",
            properties={"access_type_counts": dict(sorted(access_counts.items())), "availability_zone_count": len(zones), "ai_object_storage_zone_count": storage_count},
        ))
        for zone in zones:
            city, subdivision, country, country_code = place_from_label(zone["location"])
            access_status = "public" if zone["access"] == "General Access" else "dedicated"
            product = matrix.get(zone["zone"], {"gpu_instance_types": [], "cpu_instance_types": []})
            has_storage = zone["object_storage"] == "Yes"
            records.append(base_record(
                source_key="coreweave-directory", retrieved_at=retrieved_at,
                prefix="coreweave", identifier=zone["zone"], provider="CoreWeave", service="coreweave_cloud",
                entity_type="availability_zone", collection="coreweave_availability_zones",
                source_record_id=zone["zone"], name=zone["zone"], site_code=zone["zone"],
                lifecycle_status="operational", access_status=access_status,
                service_scope=sorted({"compute", *(("ai_object_storage",) if has_storage else ())}),
                city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
                location_precision="region", parent_record_id=parent_id,
                properties={
                    "access_type": zone["access"], "ai_object_storage": has_storage,
                    "cpu_instance_types": sorted(product["cpu_instance_types"]),
                    "gpu_instance_types": sorted(product["gpu_instance_types"]),
                    "location_label": zone["location"],
                    "product_matrix_raw_source_ref": repo_ref(matrix_path),
                    "product_matrix_sha256": sha256(matrix_path),
                    "product_matrix_source_url": SOURCES["coreweave-matrix"]["url"],
                },
            ))
    return records, {
        "super_region_count": 7,
        "availability_zone_count": 56,
        "general_access_zone_count": 18,
        "dedicated_access_zone_count": 38,
        "ai_object_storage_zone_count": 25,
        "product_matrix_zone_count": len(matrix),
    }


def parse_aws(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = source_path("aws-az", retrieved_at).read_text(encoding="utf-8")
    zone_rows: list[tuple[str, str, str]] = []
    nonstable_rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 3:
            continue
        az_id, region, geography = map(clean_text, cells)
        region = re.sub(r"\s*†.*$", "", region).strip()
        if re.fullmatch(r"[a-z0-9]+-az\d+", az_id):
            zone_rows.append((az_id, region, geography))
        elif re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d+", region) and az_id not in {"AZ ID", "---"}:
            nonstable_rows.append((az_id, region, geography))
    assert len(zone_rows) == 108
    regions: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for az_id, region, geography in zone_rows:
        regions[region].append((az_id, geography))
    assert len(regions) == 34
    records: list[dict[str, Any]] = []
    for region, zones in sorted(regions.items()):
        geography = zones[0][1]
        city, subdivision, country, country_code = place_from_label(geography)
        parent_id = f"aws:cloud_region:{slug(region)}"
        records.append(base_record(
            source_key="aws-az", retrieved_at=retrieved_at,
            prefix="aws", identifier=region, provider="Amazon Web Services", service="aws_cloud",
            entity_type="cloud_region", collection="aws_regions_and_stable_availability_zones",
            source_record_id=region, name=f"AWS Region {region}", site_code=region,
            lifecycle_status="operational", access_status="public", service_scope=["public_cloud"],
            city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
            location_precision="region",
            properties={"partition": "aws", "realm": "commercial", "stable_availability_zone_count": len(zones), "geography": geography},
        ))
        for az_id, geography in zones:
            city, subdivision, country, country_code = place_from_label(geography)
            records.append(base_record(
                source_key="aws-az", retrieved_at=retrieved_at,
                prefix="aws", identifier=az_id, provider="Amazon Web Services", service="aws_cloud",
                entity_type="availability_zone", collection="aws_regions_and_stable_availability_zones",
                source_record_id=az_id, name=az_id, site_code=az_id,
                lifecycle_status="operational", access_status="public", service_scope=["public_cloud"],
                city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
                location_precision="region", parent_record_id=parent_id,
                properties={
                    "account_zone_name_mapping": "may_be_account_specific",
                    "az_id_is_account_stable": True,
                    "geography": geography,
                    "partition": "aws",
                },
            ))
    supplemental = (
        ("aws-china", "cn-north-1", "China (Beijing)", "Beijing, China", "aws-cn", "china", "restricted"),
        ("aws-china", "cn-northwest-1", "China (Ningxia)", "Ningxia, China", "aws-cn", "china", "restricted"),
        ("aws-govcloud", "us-gov-west-1", "AWS GovCloud (US-West)", "United States", "aws-us-gov", "government", "restricted"),
        ("aws-govcloud", "us-gov-east-1", "AWS GovCloud (US-East)", "United States", "aws-us-gov", "government", "restricted"),
        ("aws-eusc", "eusc-de-east-1", "AWS European Sovereign Cloud (Brandenburg)", "Brandenburg, Germany", "aws-eusc", "sovereign", "public"),
    )
    for source_key, region, name, geography, partition, realm, access in supplemental:
        raw_text = source_path(source_key, retrieved_at).read_text(encoding="utf-8")
        assert region in raw_text
        city, subdivision, country, country_code = place_from_label(geography)
        records.append(base_record(
            source_key=source_key, retrieved_at=retrieved_at,
            prefix="aws", identifier=region, provider="Amazon Web Services", service="aws_cloud",
            entity_type="cloud_region", collection="aws_partition_regions", source_record_id=region,
            name=name, site_code=region, lifecycle_status="operational", access_status=access,
            service_scope=["public_cloud"], city=city, metro=city, subdivision=subdivision,
            country=country, country_code=country_code, location_precision="region",
            properties={"partition": partition, "realm": realm, "stable_availability_zone_count": None, "geography": geography},
        ))
    global_text = source_path("aws-global", retrieved_at).read_text(encoding="utf-8")
    match = re.search(r"spans\s+(\d+) Availability Zones within (\d+) Geographic Regions", global_text)
    assert match and tuple(map(int, match.groups())) == (123, 39)
    assert len(records) == 147
    return records, {
        "region_count": 39,
        "stable_availability_zone_id_count": 108,
        "aggregate_availability_zone_count": 123,
        "unitemized_availability_zone_gap": 15,
        "nonstable_directory_rows_excluded": [list(row) for row in nonstable_rows],
        "partition_region_counts": {"aws": 34, "aws-cn": 2, "aws-eusc": 1, "aws-us-gov": 2},
    }


def google_country_hint(region: str) -> str | None:
    if region.startswith("us-"):
        return "United States"
    if region.startswith("northamerica-northeast"):
        return "Canada"
    if region.startswith("northamerica-south"):
        return "Mexico"
    if region == "europe-west2":
        return "United Kingdom"
    return None


def split_list(value: str) -> list[str]:
    return sorted({clean_text(item) for item in clean_text(value).split(",") if clean_text(item)})


def parse_google(retrieved_at: str, *, enrich: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("google-compute", retrieved_at).read_bytes(), "html.parser")
    tables = soup.find_all("table")
    assert len(tables) == 1
    rows: list[dict[str, Any]] = []
    for tr in tables[0].find_all("tr")[1:]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        assert len(cells) == 6
        zone = cells[0]
        match = re.fullmatch(r"(.+\d)-[a-z]", zone)
        assert match, zone
        rows.append({
            "zone": zone, "region": match.group(1), "location": cells[1],
            "machine_types": split_list(cells[2]), "cpus": split_list(cells[3]),
            "options": split_list(cells[4]), "low_co2": "Low CO" in cells[5],
        })
    assert rows, "Google Compute zone directory is empty"
    assert len({row["zone"] for row in rows}) == len(rows), "Duplicate Google zone ID"
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["region"]].append(row)
    records: list[dict[str, Any]] = []
    for region, zones in sorted(grouped.items()):
        location = zones[0]["location"]
        city, subdivision, country, country_code = place_from_label(location, country_hint=google_country_hint(region))
        parent_id = f"google:cloud_region:{slug(region)}"
        records.append(base_record(
            source_key="google-compute", retrieved_at=retrieved_at,
            prefix="google", identifier=region, provider="Google Cloud", service="google_cloud",
            entity_type="cloud_region", collection="google_compute_regions_and_zones",
            source_record_id=region, name=region, site_code=region, lifecycle_status="operational",
            access_status="public", service_scope=["compute"], city=city, metro=city,
            subdivision=subdivision, country=country, country_code=country_code,
            location_precision="region",
            properties={"availability_zone_count": len(zones), "availability_zone_ids": sorted(row["zone"] for row in zones), "location_label": location},
        ))
        for row in zones:
            city, subdivision, country, country_code = place_from_label(row["location"], country_hint=google_country_hint(region))
            records.append(base_record(
                source_key="google-compute", retrieved_at=retrieved_at,
                prefix="google", identifier=row["zone"], provider="Google Cloud", service="google_cloud",
                entity_type="availability_zone", collection="google_compute_regions_and_zones",
                source_record_id=row["zone"], name=row["zone"], site_code=row["zone"],
                lifecycle_status="operational", access_status="public", service_scope=["compute"],
                city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
                location_precision="region", parent_record_id=parent_id,
                properties={
                    "cpu_platforms": row["cpus"], "low_co2": row["low_co2"],
                    "machine_types": row["machine_types"], "options": row["options"],
                    "location_label": row["location"],
                },
            ))
    report = {
        "region_count": len(grouped), "availability_zone_count": len(rows),
        "product_availability_joined": True,
    }
    if enrich:
        report.update(enrich_google(records, retrieved_at))
    return records, report


GOOGLE_ENRICHMENT_SOURCES = (
    "google-ai-zones", "google-gpu-zones", "gcping-endpoints", "gcping-methodology",
)


def enrichment_source(key: str, retrieved_at: str) -> dict[str, Any]:
    return {
        "source_url": SOURCES[key]["url"],
        "raw_source_ref": repo_ref(source_path(key, retrieved_at)),
        "source_sha256": sha256(source_path(key, retrieved_at)),
        "retrieved_at": retrieved_at,
        "source_scope": "observed" if key.startswith("gcping-") else "provider_declared",
    }


def google_table(key: str, retrieved_at: str, headers: list[str]) -> list[list[str]]:
    soup = BeautifulSoup(source_path(key, retrieved_at).read_bytes(), "html.parser")
    matches = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in rows[0].find_all(["th", "td"])]
        if cells == headers:
            matches.append(rows[1:])
    assert len(matches) == 1, f"Expected one {key} table with headers {headers}"
    result = []
    for tr in matches[0]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        assert len(cells) == len(headers), (key, cells)
        result.append(cells)
    assert result, f"Empty {key} directory"
    return result


def enrich_google(records: list[dict[str, Any]], retrieved_at: str) -> dict[str, Any]:
    regions = {row["site_code"]: row for row in records if row["entity_type"] == "cloud_region"}
    zones = {row["site_code"]: row for row in records if row["entity_type"] == "availability_zone"}
    standard_count = len(zones)
    methodology = BeautifulSoup(source_path("gcping-methodology", retrieved_at).read_bytes(), "html.parser").get_text(" ", strip=True)
    assert "Cloud Run" in methodology and "not an official Google project" in methodology, "GCPing methodology changed"
    for row in zones.values():
        row["properties"]["zone_kind"] = "standard"
    ai_rows = google_table("google-ai-zones", retrieved_at, [
        "AI zone", "AI zone location", "Google Cloud region", "Google Cloud region location", "Parent zone",
    ])
    for zone, location, region, region_location, parent in ai_rows:
        assert re.fullmatch(rf"{re.escape(region)}-ai\d+[a-z]", zone), zone
        assert zone not in zones and region in regions and parent in zones, zone
        assert zones[parent]["parent_record_id"] == regions[region]["record_id"], zone
        assert zone[-1] == parent[-1], zone
        city, subdivision, country, country_code = place_from_label(location, country_hint=google_country_hint(region))
        assert country_code, location
        record = base_record(
            source_key="google-ai-zones", retrieved_at=retrieved_at,
            prefix="google", identifier=zone, provider="Google Cloud", service="google_cloud",
            entity_type="availability_zone", collection="google_compute_ai_zones",
            source_record_id=zone, name=zone, site_code=zone, lifecycle_status="operational",
            access_status="restricted", service_scope=["compute", "ai_ml"], city=city, metro=city,
            subdivision=subdivision, country=country, country_code=country_code,
            location_precision="region", parent_record_id=regions[region]["record_id"],
            properties={
                "zone_kind": "ai", "location_label": location, "region_location_label": region_location,
                "parent_zone_id": parent, "parent_zone_record_id": zones[parent]["record_id"],
                "failure_independence": "shares_software_schedule_and_sometimes_infrastructure_with_parent_zone",
                "access_requirement": "enable_ai_zone_visibility_for_project",
            },
        )
        records.append(record)
        zones[zone] = record

    gpu_rows = google_table("google-gpu-zones", retrieved_at, ["Zone", "Location", "Zone type", "GPU machine type"])
    gpu_ids = set()
    for zone, location, kind, machines in gpu_rows:
        assert zone in zones and zone not in gpu_ids, zone
        expected_kind = "AI zone" if zones[zone]["properties"]["zone_kind"] == "ai" else "Standard"
        assert kind == expected_kind, (zone, kind)
        machine_types = sorted({clean_text(value) for value in machines.split("•") if clean_text(value)})
        assert machine_types, zone
        zones[zone]["properties"]["gpu_availability"] = {
            **enrichment_source("google-gpu-zones", retrieved_at),
            "location_label": location, "machine_types": machine_types,
            "availability_semantics": "listed_support_not_live_capacity_or_quota",
        }
        gpu_ids.add(zone)

    endpoints = json.loads(source_path("gcping-endpoints", retrieved_at).read_text(encoding="utf-8"))
    assert isinstance(endpoints, dict) and endpoints, "Empty GCPing catalog"
    unknown = []
    matched = set()
    for key, endpoint in sorted(endpoints.items()):
        assert endpoint["Region"] == key and endpoint["RegionName"], key
        assert re.fullmatch(r"https://[a-z0-9.-]+(?::\d+)?/?", endpoint["URL"]), endpoint
        if key == "global":
            continue
        if key not in regions:
            unknown.append(key)
            continue
        assert re.fullmatch(rf"https://{re.escape(key)}-[a-z0-9-]+\.a\.run\.app", endpoint["URL"]), endpoint
        regions[key]["properties"]["gcping"] = {
            **enrichment_source("gcping-endpoints", retrieved_at),
            "region_label": endpoint["RegionName"], "endpoint_url": endpoint["URL"],
            "endpoint_type": "cloud_run_https", "methodology_url": "https://gcping.com/",
            "official_google_product": False,
            "measurement_semantics": "caller_relative_https_request_response_time_not_icmp_or_inter_region_latency",
        }
        matched.add(key)
    for region, row in regions.items():
        children = [zone for zone, record in zones.items() if record["parent_record_id"] == row["record_id"]]
        ai_ids = sorted(zone for zone in children if zones[zone]["properties"]["zone_kind"] == "ai")
        row["properties"].update({
            "availability_zone_ids": sorted(children), "availability_zone_count": len(children),
            "standard_availability_zone_count": len(children) - len(ai_ids),
            "ai_zone_ids": ai_ids, "ai_zone_count": len(ai_ids),
            "gpu_zone_ids": sorted(gpu_ids.intersection(children)),
        })
    return {
        "availability_zone_count": len(zones), "standard_availability_zone_count": standard_count,
        "ai_zone_count": len(ai_rows), "gpu_availability_zone_count": len(gpu_ids),
        "gpu_unlisted_zone_ids": sorted(set(zones) - gpu_ids),
        "gpu_unlisted_semantics": "absence_from_gpu_table_does_not_establish_no_gpu_support",
        "gcping": {
            "catalog_entry_count": len(endpoints), "matched_region_count": len(matched),
            "unmatched_endpoint_region_ids": unknown, "regions_without_endpoint": sorted(set(regions) - matched),
            "global_endpoint": endpoints.get("global"),
            "global_semantics": "global_https_load_balancer_not_a_cloud_region_or_physical_site",
            "latency_measurements_collected": False,
        },
        "enrichment_sources": [enrichment_source(key, retrieved_at) for key in GOOGLE_ENRICHMENT_SOURCES],
    }


def azure_country(programmatic_name: str, geography: str) -> tuple[str | None, str | None]:
    overrides = {"eastasia": "Hong Kong", "southeastasia": "Singapore", "northeurope": "Ireland", "westeurope": "Netherlands"}
    return country_identity(overrides.get(programmatic_name, geography))


def parse_azure(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("azure-regions", retrieved_at).read_bytes(), "html.parser")
    table = next(table for table in soup.find_all("table") if len(table.find_all("tr")) == 58)
    records = []
    restricted_count = 0
    az_count = 0
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        assert len(cells) == 6
        values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        name, paired_region, physical_location, geography, programmatic_name = values[0], values[2], values[3], values[4], values[5]
        first_icons = " ".join(image.get("src", "") for image in cells[0].find_all("img"))
        restricted = "icon-region-restricted" in first_icons
        coming = "icon-region-coming-soon" in first_icons
        az_supported = any(image.get("alt") == "Yes" for image in cells[1].find_all("img"))
        restricted_count += restricted
        az_count += az_supported
        country, country_code = azure_country(programmatic_name, geography)
        records.append(base_record(
            source_key="azure-regions", retrieved_at=retrieved_at,
            prefix="azure", identifier=programmatic_name, provider="Microsoft Azure", service="azure_cloud",
            entity_type="cloud_region", collection="azure_public_cloud_regions",
            source_record_id=programmatic_name, name=name, site_code=programmatic_name,
            lifecycle_status="planned" if coming else "operational",
            access_status="restricted" if restricted else "public", service_scope=["public_cloud"],
            city=None, metro=None, subdivision=None, country=country, country_code=country_code,
            location_precision="region",
            properties={
                "availability_zone_support": az_supported,
                "geography": geography,
                "paired_region": None if paired_region == "N/A" else paired_region,
                "physical_location": physical_location,
                "synthetic_availability_zones_generated": False,
            },
        ))
    assert len(records) == 57 and restricted_count == 8 and az_count == 39
    return records, {
        "public_cloud_region_count": 57,
        "restricted_region_count": 8,
        "availability_zone_supported_region_count": 39,
        "availability_zone_records_generated": 0,
    }


def parse_oci(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("oci-regions", retrieved_at).read_bytes(), "html.parser")
    tables = soup.find_all("table")
    assert len(tables) == 1
    records = []
    realms = Counter()
    ad_counts = Counter()
    for tr in tables[0].find_all("tr")[1:]:
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        assert len(cells) == 6
        name, region_id, location, region_key, realm_key, ad_count = cells
        country_hint = "United States" if region_id.startswith("us-") else None
        city, subdivision, country, country_code = place_from_label(location, country_hint=country_hint)
        realms[realm_key] += 1
        ad_counts[ad_count] += 1
        records.append(base_record(
            source_key="oci-regions", retrieved_at=retrieved_at,
            prefix="oracle", identifier=region_id, provider="Oracle Cloud Infrastructure", service="oracle_cloud",
            entity_type="cloud_region", collection="oci_commercial_regions",
            source_record_id=region_id, name=name, site_code=region_id,
            lifecycle_status="operational", access_status="public", service_scope=["public_cloud"],
            city=city, metro=city, subdivision=subdivision, country=country, country_code=country_code,
            location_precision="region",
            properties={
                "availability_domain_count": int(ad_count),
                "availability_domain_records_generated": 0,
                "realm_key": realm_key,
                "region_key": region_key,
                "region_location": location,
                "tenancy_specific_availability_domain_names": True,
            },
        ))
    assert len(records) == 45
    return records, {
        "commercial_region_count": 45,
        "realm_counts": dict(sorted(realms.items())),
        "availability_domain_count_distribution": dict(sorted(ad_counts.items())),
        "availability_domain_records_generated": 0,
    }


IBM_REGION_COUNTRIES = {
    "us-south": "United States", "us-east": "United States", "br-sao": "Brazil", "ca-tor": "Canada",
    "eu-de": "Germany", "eu-gb": "United Kingdom", "eu-es": "Spain", "au-syd": "Australia",
    "jp-tok": "Japan", "in-che": "India", "ca-mon": "Canada", "in-mum": "India", "jp-osa": "Japan",
}

IBM_DC_COUNTRIES = {
    "DAL": "United States", "SJC": "United States", "WDC": "United States", "MON": "Canada",
    "SAO": "Brazil", "TOR": "Canada", "AMS": "Netherlands", "FRA": "Germany",
    "LON": "United Kingdom", "MAD": "Spain", "PAR": "France", "CHE": "India",
    "OSA": "Japan", "SNG": "Singapore", "SYD": "Australia", "TOK": "Japan",
}


def ibm_region_label(cell: Any, code: str) -> str:
    return clean_text(re.sub(rf"\s*\(\s*{re.escape(code)}\s*\)\s*$", "", cell.get_text(" ", strip=True)))


def parse_ibm(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("ibm-locations", retrieved_at).read_bytes(), "html.parser")
    tables = soup.find_all("table")
    assert len(tables) == 11
    regions: dict[str, dict[str, Any]] = {}
    for table in tables[:4]:
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            code_node = cells[0].find("code")
            assert code_node
            code = clean_text(code_node.get_text())
            label = ibm_region_label(cells[0], code)
            logical_zones = [clean_text(value) for value in cells[1].stripped_strings]
            assert len(logical_zones) == 3
            regions[code] = {"label": label, "logical_zones": logical_zones}
    assert len(regions) == 13
    records: list[dict[str, Any]] = []
    for code, region in sorted(regions.items()):
        country, country_code = country_identity(IBM_REGION_COUNTRIES[code])
        city = region["label"].split(" - ", 1)[0]
        records.append(base_record(
            source_key="ibm-locations", retrieved_at=retrieved_at,
            prefix="ibm", identifier=code, provider="IBM Cloud", service="ibm_cloud",
            entity_type="cloud_region", collection="ibm_multizone_regions_and_universal_zones",
            source_record_id=code, name=region["label"], site_code=code,
            lifecycle_status="operational", access_status="public", service_scope=["public_cloud"],
            city=city, metro=city, subdivision=None, country=country, country_code=country_code,
            location_precision="region",
            properties={
                "account_logical_zone_labels": region["logical_zones"],
                "account_logical_zone_mapping": "assigned_per_account_not_a_physical_identity",
            },
        ))
    universal_count = 0
    for table in tables[4:8]:
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            code_node = cells[0].find("code")
            assert code_node
            code = clean_text(code_node.get_text())
            label = ibm_region_label(cells[0], code)
            universal_zones = [clean_text(value) for value in cells[1].stripped_strings]
            data_centers = [clean_text(value) for value in cells[2].stripped_strings]
            pops = [clean_text(value) for value in cells[3].stripped_strings]
            assert len(universal_zones) == 3 or (code == "us-south" and len(universal_zones) == 4)
            assert len(data_centers) in {1, len(universal_zones)}
            if len(data_centers) == 1:
                data_centers *= len(universal_zones)
            country, country_code = country_identity(IBM_REGION_COUNTRIES[code])
            city = label.split(" - ", 1)[0]
            for zone, data_center in zip(universal_zones, data_centers):
                universal_count += 1
                records.append(base_record(
                    source_key="ibm-locations", retrieved_at=retrieved_at,
                    prefix="ibm", identifier=zone, provider="IBM Cloud", service="ibm_cloud",
                    entity_type="availability_zone", collection="ibm_multizone_regions_and_universal_zones",
                    source_record_id=zone, name=zone, site_code=zone,
                    lifecycle_status="operational", access_status="public", service_scope=["public_cloud"],
                    city=city, metro=city, subdivision=None, country=country, country_code=country_code,
                    location_precision="facility", parent_record_id=f"ibm:cloud_region:{slug(code)}",
                    properties={
                        "account_logical_zone_mapping": "assigned_per_account_not_asserted_for_this_universal_zone",
                        "associated_data_center_code": data_center,
                        "region_point_of_presence_codes": pops,
                        "universal_zone_name": zone,
                    },
                ))
    assert universal_count == 40 and len(records) == 53

    closure_path = source_path("ibm-closures", retrieved_at)
    closure_text = closure_path.read_text(encoding="utf-8")
    for required in ("CHE01", "15 June 2026", "10 December 2026", "10 June 2027"):
        assert required in closure_text
    classic: list[dict[str, Any]] = []
    for table in tables[8:11]:
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            assert len(cells) == 2
            name = clean_text(re.sub(r"\s*\[\d+\]\s*$", "", cells[0].get_text(" ", strip=True)))
            code = clean_text(cells[1].get_text(" ", strip=True))
            prefix = re.match(r"[A-Z]+", code)
            assert prefix and prefix.group(0) in IBM_DC_COUNTRIES
            country, country_code = country_identity(IBM_DC_COUNTRIES[prefix.group(0)])
            city = re.sub(r"\s+\d+$", "", name)
            government = code in {"DAL08", "WDC03"}
            closing = code == "CHE01"
            properties: dict[str, Any] = {
                "government_cloud": government,
                "provider_directory_class": "classic_infrastructure_data_center",
            }
            if closing:
                properties.update({
                    "closure_date": "2027-06-10",
                    "end_of_market_date": "2026-06-15",
                    "new_deployment_removed_date": "2026-12-10",
                    "closure_raw_source_ref": repo_ref(closure_path),
                    "closure_sha256": sha256(closure_path),
                    "closure_source_url": SOURCES["ibm-closures"]["url"],
                })
            classic.append(base_record(
                source_key="ibm-locations", retrieved_at=retrieved_at,
                prefix="ibm", identifier=code, provider="IBM Cloud", service="ibm_classic",
                entity_type="data_center", collection="ibm_classic_data_centers",
                source_record_id=code, name=name, site_code=code,
                lifecycle_status="operational",
                access_status="sales_restricted" if closing else "restricted" if government else "public",
                service_scope=["government_cloud"] if government else ["classic_infrastructure"],
                city=city, metro=city, subdivision=None, country=country, country_code=country_code,
                location_precision="facility", properties=properties,
            ))
    assert len(classic) == 42
    return records, {
        "region_count": 13, "universal_zone_count": 40,
        "account_logical_zone_slot_count": 39,
        "account_logical_zone_records_generated": 0,
    }, classic, {
        "classic_data_center_count": 42,
        "government_data_center_count": 2,
        "closing_data_center_count": 1,
    }


def parse_meta(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("meta-data-centers", retrieved_at).read_bytes(), "html.parser")
    articles = soup.select("article.card")
    assert len(articles) == 33
    records = []
    countries = Counter()
    year_count = 0
    for article in articles:
        eyebrow_node = article.select_one(".card__eyebrow-text")
        title_node = article.select_one(".card__title")
        excerpt_node = article.select_one(".card__excerpt")
        assert eyebrow_node and title_node and excerpt_node
        eyebrow = clean_text(eyebrow_node.get_text(" ", strip=True))
        title = clean_text(title_node.get_text(" ", strip=True))
        state = US_STATES.get(normalize_key(eyebrow))
        if state:
            country, country_code, subdivision = "United States", "US", state
        else:
            country, country_code = country_identity(eyebrow)
            subdivision = None
        assert country_code, eyebrow
        countries[country or eyebrow] += 1
        summary = clean_text(excerpt_node.get_text(" ", strip=True))
        summary_digits = re.sub(r"(?<=\d)\s+(?=\d)", "", summary)
        year_match = re.search(r"\b(19\d{2}|20\d{2})\s*break ground", summary_digits, re.IGNORECASE)
        break_ground_year = int(year_match.group(1)) if year_match else None
        year_count += break_ground_year is not None
        primary = article.select_one("a.card__primary-cta[href]")
        social_urls = sorted({link.get("href") for link in article.select("a.card__follow-us-cta[href]") if link.get("href")})
        identity = f"{country_code}-{subdivision or country}-{title}"
        records.append(base_record(
            source_key="meta-data-centers", retrieved_at=retrieved_at,
            prefix="meta", identifier=identity, provider="Meta", service="meta_data_centers",
            entity_type="data_center", collection="meta_data_center_directory",
            source_record_id=slug(identity), name=title, site_code=None,
            lifecycle_status="unknown", access_status="not_applicable", service_scope=["owned_data_center"],
            city=title, metro=title, subdivision=subdivision, country=country, country_code=country_code,
            location_precision="campus", confidence="medium",
            properties={
                "break_ground_year": break_ground_year,
                "directory_detail_url": primary.get("href").strip() if primary and primary.get("href") else None,
                "directory_summary": summary,
                "directory_scope": "meta_data_center_location",
                "lifecycle_not_inferred_from_break_ground_year": True,
                "social_urls": social_urls,
            },
        ))
    return records, {
        "directory_card_count": 33,
        "break_ground_year_count": year_count,
        "country_counts": dict(sorted(countries.items())),
        "lifecycle_policy": "unknown unless the directory explicitly states a current lifecycle",
    }


PARSERS: dict[str, Callable[..., Any]] = {
    "coreweave": parse_coreweave,
    "aws": parse_aws,
    "google": parse_google,
    "azure": parse_azure,
    "oci": parse_oci,
    "ibm": parse_ibm,
    "meta": parse_meta,
}


def main() -> None:
    args = parse_args()
    retrieval_tag(args.retrieved_at)
    selected = tuple(DATASET_SOURCES) if args.dataset == "all" else (args.dataset,)
    if args.google_enrichment and "google" not in selected:
        raise ValueError("--google-enrichment requires --dataset google or all")
    source_keys = {key for dataset in selected for key in DATASET_SOURCES[dataset]}
    if args.google_enrichment:
        source_keys.update(GOOGLE_ENRICHMENT_SOURCES)
    for key in sorted(source_keys):
        info = SOURCES[key]
        raw_path = source_path(key, args.retrieved_at)
        if args.fetch:
            fetch(str(info["url"]), raw_path)
        if not raw_path.exists():
            raise FileNotFoundError(f"raw snapshot missing: {raw_path}; run with --fetch")
        write_provenance(
            raw_path,
            source_url=str(info["url"]),
            retrieved_at=args.retrieved_at,
            media_type=str(info["media_type"]),
            source_published_at=info["published"],
            notes=(
                "GCPing is not an official Google product. Endpoint catalog and methodology only; "
                "no latency measurement or physical-location assertion. Source-specific terms may apply."
                if key.startswith("gcping-") else
                "Immutable official provider source snapshot used by scripts/update_hyperscalers.py; source-specific copyright and redistribution terms may apply."
            ),
        )
    summaries: dict[str, dict[str, Any]] = {}
    for dataset in selected:
        parsed = (
            parse_google(args.retrieved_at, enrich=True)
            if dataset == "google" and args.google_enrichment else PARSERS[dataset](args.retrieved_at)
        )
        outputs = ((dataset, parsed[0], parsed[1]),)
        if dataset == "ibm":
            outputs = (("ibm", parsed[0], parsed[1]), ("ibm-classic", parsed[2], parsed[3]))
        for output_key, records, extra in outputs:
            output_dir, layer_name, source_key = OUTPUTS[output_key]
            report = write_layer(
                records=records,
                output_dir=args.output_root / output_dir,
                layer_name=layer_name,
                retrieved_at=args.retrieved_at,
                source_url=str(SOURCES[source_key]["url"]),
                raw_path=source_path(source_key, args.retrieved_at),
                parser_name=f"update_hyperscalers.py:{output_key}",
                schema_path=args.schema,
                schema_version=SCHEMA_CONTRACT_VERSION,
                extra_report=extra,
            )
            if output_key == "google" and args.google_enrichment:
                tag = retrieval_tag(args.retrieved_at)
                geojson_path = args.output_root / output_dir / f"{layer_name}.{tag}.geojson"
                report["geojson_sha256"] = sha256(geojson_path)
                write_json(geojson_path.with_suffix(".report.json"), report)
            summaries[output_key] = report
    print(json.dumps({key: {"record_count": value["record_count"], "geometry_null": value["geometry_null"]} for key, value in summaries.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
