"""Source and record helpers for the October China implementation."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from babel import Locale

from location_common import (
    REPO_ROOT, SCHEMA_CONTRACT_VERSION, canonical_record, country_identity,
    jurisdiction_scope, repo_ref, sha256, slug,
)

DATE, TAG = "2026-10-11", "20261011"
CATALOG = REPO_ROOT / f"data/raw/china-enrichment/catalog.{TAG}.json"


def sources() -> dict[str, dict]:
    return {s["source_id"]: s for s in json.loads(CATALOG.read_text())["sources"]}


def source(key: str) -> dict:
    item = sources()[key]
    if item["result"] != "retrieved":
        raise ValueError(f"No retained source for {key}: {item.get('error')}")
    path = REPO_ROOT / item["path"]
    if sha256(path) != item["sha256"]:
        raise ValueError(f"Source digest changed: {key}")
    return item


def source_bytes(key: str) -> bytes:
    item = source(key)
    path = REPO_ROOT / item["path"]
    content = path.read_bytes()
    return gzip.decompress(content) if content.startswith(b"\x1f\x8b") else content


def soup(key: str) -> BeautifulSoup:
    return BeautifulSoup(source_bytes(key), "html.parser")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\ufeff", "").replace("\u200b", "")).strip()


def cells(row) -> list[str]:
    return [clean(td.get_text(" ", strip=True)) for td in row.find_all(["td", "th"], recursive=False)]


def evidence(key: str, **extra: Any) -> dict:
    item = source(key)
    return {
        "source_id": key, "source_url": item["source_url"],
        "raw_source_ref": item["path"], "source_sha256": item["sha256"],
        "source_published_at": item.get("source_published_at"),
        "source_updated_at": item.get("source_updated_at"),
        "retrieved_at": DATE, "capture_method": item["capture_method"], **extra,
    }


def location(key: str, prefix: str, entity_type: str, identifier: str, name: str,
             provider: str, service: str, *, country_code: str | None = None,
             city: str | None = None, source_record_id: str | None = None,
             parent: str | None = None, access: str = "public", status: str = "unknown",
             scope: list[str] | None = None, properties: dict | None = None,
             aliases: list[str] | None = None) -> dict:
    item = source(key)
    code = country_code
    country = Locale.parse("en").territories.get(code, code) if code else None
    return canonical_record(
        schema_version=SCHEMA_CONTRACT_VERSION, record_id=f"{prefix}:{entity_type}:{slug(identifier)}",
        aliases=sorted(set(aliases or [])), provider=provider, service=service,
        entity_type=entity_type, parent_record_id=parent,
        jurisdiction_scope=jurisdiction_scope(code), access_status=access,
        service_scope=scope or [], source_collection=f"{prefix}_{service}_directory",
        source_record_id=source_record_id, name=name, site_code=source_record_id,
        lifecycle_status=status, source_scope="provider_declared", city=city,
        metro=city, subdivision=None, country=country, country_code=code,
        latitude=None, longitude=None, location_precision="region",
        coordinate_method="unknown", coordinate_crs=None,
        source_url=item["source_url"], raw_source_ref=item["path"], source_sha256=item["sha256"],
        source_published_at=item.get("source_published_at"), retrieved_at=DATE,
        first_seen=DATE, last_seen=DATE, confidence="high",
        properties={"source_updated_at": item.get("source_updated_at"), **(properties or {})},
    )


def labelled_id(collection: str, label: str) -> str:
    """Stable source-label identity without manufacturing a provider code."""
    return collection + "-" + hashlib.sha256(clean(label).encode()).hexdigest()[:16]


def infra(key: str, prefix: str, category: str, identifier: str, name: str,
          provider: str, unit: str, *, country_codes: list[str] | None = None,
          country_scope: str = "source_geography_not_established", status: str = "unknown",
          source_scope: str = "provider_declared", parties: list[dict] | None = None,
          relationships: list[dict] | None = None, properties: dict | None = None,
          confidence: str = "high") -> dict:
    item = source(key)
    return {
        "record_id": f"{prefix}:{category}:{identifier}", "category": category,
        "unit": unit, "name": name, "provider": provider,
        "parties": parties or [{"name": provider, "role": "declaring_party"}],
        "country_codes": sorted(set(country_codes or [])), "country_scope": country_scope,
        "lifecycle_status": status, "source_scope": source_scope,
        "source_url": item["source_url"], "raw_source_ref": item["path"],
        "source_sha256": item["sha256"], "source_published_at": item.get("source_published_at"),
        "source_updated_at": item.get("source_updated_at"), "retrieved_at": DATE,
        "confidence": confidence, "geometry": None, "spatial_representation": "none",
        "relationships": relationships or [], "properties": properties or {},
    }


def script_json(key: str, assignment: str) -> Any:
    text = source_bytes(key).decode("utf-8")
    match = re.search(re.escape(assignment) + r"\s*=\s*", text)
    if not match:
        raise ValueError(f"No {assignment} assignment in {key}")
    # Parse literal JSON only. Never evaluate upstream scripts.
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
