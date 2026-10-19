"""Source verification and serialization for the approved Russia enrichment."""
from __future__ import annotations

import json
from pathlib import Path
from bs4 import BeautifulSoup

from location_common import (REPO_ROOT, canonical_record, country_identity, jurisdiction_scope,
                             repo_ref, sha256, slug, write_json, write_layer)
from review_russia_enrichment import raw_path as review_raw_path

DATE, TAG = "2026-10-19", "20261019"
BASELINE = "data/raw/repository/manifest-before-russia.20261019.json"
EXTRA = {
    "selectel": "russia/selectel-locations.20261019.html",
    "advanced": "russia/cloudru-advanced-faq.20261019.html",
    "advanced_directory": "russia/cloudru-advanced-zones.20261019.html",
    "evolution": "russia/cloudru-evolution-vm.20261019.html",
    "evolution_overview": "russia/cloudru-evolution-overview.20261019.html",
    "ixcellerate": "russia/ixcellerate-scalability.20261019.html",
    "ripe": "ripe/delegated-ripencc-extended.20260606.bz2",
    "country_policy": "un/a-res-68-262.20140327.pdf",
    "yandex_routes": "yandex/announced-prefixes.20261019.json",
}
LOCATION_LAYERS = ("yandex/regions-and-zones", "yandex/cdn-cities",
                   "selectel/russian-hierarchy", "cloudru/advanced-regions-and-zones",
                   "cloudru/evolution-zones", "ixcellerate/data-centers")
NETWORK_LAYERS = ("yandex-prefixes", "yandex-routing")
LOCATION_SCHEMA = REPO_ROOT / "schema/location-v1.3.schema.json"


def read(path: str | Path):
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def raw_path(key: str) -> Path:
    return REPO_ROOT / "data/raw" / EXTRA[key] if key in EXTRA else review_raw_path(key)


def source(key: str) -> dict:
    path = raw_path(key)
    value = read(path.with_name(path.name + ".provenance.json"))
    if value["sha256"] != sha256(path) or value["raw_source_ref"] != repo_ref(path):
        raise ValueError(f"Source provenance mismatch: {key}")
    return value


def evidence(key: str) -> dict:
    value = source(key)
    return {"source_url": value["source_url"], "raw_source_ref": value["raw_source_ref"],
            "source_sha256": value["sha256"], "source_published_at": value.get("source_published_at"),
            "source_updated_at": value.get("source_updated_at"), "retrieved_at": value["retrieved_at"]}


def soup(key: str) -> BeautifulSoup:
    source(key)
    return BeautifulSoup(raw_path(key).read_bytes(), "html.parser")


def location(key: str, vendor: str, kind: str, identity: str, name: str,
             provider: str, service: str, *, country: str | None, city=None,
             parent=None, code=None, status="unknown", scope=None, properties=None) -> dict:
    item = source(key)
    label = {"RU": "Russia", "KZ": "Kazakhstan", "UA": "Ukraine"}.get(country, country)
    country_name, country_code = country_identity(label) if label else (None, None)
    if country and country_code is None:
        raise ValueError(f"Unrecognized country: {country}")
    return canonical_record(
        schema_version="1.3.0", record_id=f"{vendor}:{kind}:{slug(identity)}", aliases=[],
        provider=provider, service=service, entity_type=kind, parent_record_id=parent,
        jurisdiction_scope=jurisdiction_scope(country_code),
        access_status="public" if kind in {"cloud_region", "availability_zone", "cloud_resource_pool"} else "not_applicable",
        service_scope=scope or [], source_collection=f"{vendor}_{service}", source_record_id=code,
        name=name, site_code=code, lifecycle_status=status, source_scope="provider_declared",
        city=city, metro=city, subdivision=None, country=country_name, country_code=country_code,
        latitude=None, longitude=None, location_precision="city" if city else "region",
        coordinate_method="unknown", coordinate_crs=None, source_url=item["source_url"],
        raw_source_ref=item["raw_source_ref"], source_sha256=item["sha256"],
        source_published_at=item.get("source_published_at"), retrieved_at=item["retrieved_at"],
        first_seen=DATE, last_seen=DATE, confidence="high",
        properties={"source_updated_at": item.get("source_updated_at"), "facility_mapping_asserted": False,
                    **(properties or {})})


def publish_locations(root: Path, layer: str, rows: list[dict], key: str, **details) -> None:
    directory, name = layer.split("/")
    report = write_layer(records=rows, output_dir=root / "data" / directory,
        layer_name=name, retrieved_at=DATE, source_url=source(key)["source_url"],
        raw_path=raw_path(key), parser_name="update_russia_enrichment.py", schema_version="1.3.0",
        schema_path=LOCATION_SCHEMA,
        extra_report={"built_at": DATE, **details})
    # Reports must be byte-identical when generated outside the repository.
    path = f"data/{layer}.{TAG}.geojson"
    csv = path.replace(".geojson", ".csv")
    report.update(layer=layer, generated_files=[path], derived_files={"csv": {
        "path": csv, "source": path, "generator": f"make {csv}"}})
    write_json(root / f"data/{layer}.{TAG}.report.json", report)
