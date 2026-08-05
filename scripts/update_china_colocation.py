#!/usr/bin/env python3
"""Archive and assess China colocation portfolios separately from public cloud."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from location_common import (
    REPO_ROOT,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    canonical_record,
    fetch,
    repo_ref,
    retrieval_tag,
    sha256,
    slug,
    write_json,
    write_layer,
    write_provenance,
)


SOURCES: dict[str, dict[str, str | None]] = {
    "gds": {
        "url": "https://www.gds-services.com/about_4.html",
        "path": "data/raw/china-colocation/gds-data-centers.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "vnet": {
        "url": "https://ir.vnet.com/static-files/8b1feb05-698c-4de3-8693-4cc85803b868",
        "path": "data/raw/china-colocation/vnet-2025-20f.{tag}.pdf",
        "media_type": "application/pdf",
        "published": "2026-04-16",
    },
    "chindata": {
        "url": "https://www.chindatagroup.com/global.html",
        "path": "data/raw/china-colocation/chindata-locations.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "chindata-sangyuan": {
        "url": "https://www.chindatagroup.com/media/news/533.html",
        "path": "data/raw/china-colocation/chindata-sangyuan.{tag}.html",
        "media_type": "text/html",
        "published": "2026-07-02",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def raw_path(key: str, retrieved_at: str) -> Path:
    return REPO_ROOT / str(SOURCES[key]["path"]).format(tag=retrieval_tag(retrieved_at))


def evidence(key: str, retrieved_at: str) -> dict[str, Any]:
    path = raw_path(key, retrieved_at)
    return {
        "raw_source_ref": repo_ref(path),
        "source_published_at": SOURCES[key]["published"],
        "source_sha256": sha256(path),
        "source_url": SOURCES[key]["url"],
    }


def chindata_records(retrieved_at: str) -> tuple[list[dict[str, Any]], list[str]]:
    path = raw_path("chindata", retrieved_at)
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    codes = sorted(set(re.findall(r"ChinaNorth\s+[A-Z]\d+", soup.get_text(" ", strip=True))))
    if codes != ["ChinaNorth H01", "ChinaNorth H02", "ChinaNorth H04", "ChinaNorth W01"]:
        raise ValueError(f"unexpected Chindata directory codes: {codes}")
    records = []
    for code in codes:
        records.append(canonical_record(
            schema_version=SCHEMA_VERSION,
            record_id=f"chindata:data_center:{slug(code)}",
            aliases=[],
            provider="Chindata",
            service="chindata_colocation",
            entity_type="data_center",
            parent_record_id=None,
            jurisdiction_scope="mainland_china",
            access_status="not_applicable",
            service_scope=["colocation", "infrastructure_service", "managed_service"],
            source_collection="chindata_current_location_directory",
            source_record_id=code,
            name=code,
            site_code=code,
            lifecycle_status="operational",
            source_scope="provider_declared",
            city=None,
            metro=None,
            subdivision=None,
            country="China",
            country_code="CN",
            latitude=None,
            longitude=None,
            location_precision="unknown",
            coordinate_method="unknown",
            coordinate_crs=None,
            source_url=str(SOURCES["chindata"]["url"]),
            raw_source_ref=repo_ref(path),
            source_sha256=sha256(path),
            source_published_at=None,
            retrieved_at=retrieved_at,
            first_seen=retrieved_at,
            last_seen=retrieved_at,
            confidence="high",
            properties={
                "completeness": "partial_current_directory",
                "country_context_only": True,
                "published_location_detail": None,
                "scope_warning": "The directory exposes a current code but no parseable city or facility address; no location was inferred from the code.",
            },
        ))
    return records, codes


def assessment_rows(retrieved_at: str, codes: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "operator": "GDS Holdings",
            "operator_class": "carrier_and_cloud_neutral_colocation",
            **evidence("gds", retrieved_at),
            "published_portfolio": {
                "operational_data_centers": 51,
                "under_construction_data_centers": 16,
                "operational_by_market": {"beijing_tianjin_hebei": 20, "southwest": 2, "yangtze_river_delta": 19, "greater_bay_area": 10},
                "market_locations": ["Beijing", "Langfang", "Zhangbei", "Huailai", "Chengdu", "Shanghai", "Kunshan", "Changshu", "Shenzhen", "Guangzhou", "Huizhou", "Hong Kong"],
            },
            "canonical_generation_status": "gated_aggregate_counts_and_market_footprints_only",
            "next_step": "Obtain a provider-approved facility directory or extract stable facility IDs from current filings without converting market totals into sites.",
        },
        {
            "operator": "VNET Group",
            "operator_class": "carrier_and_cloud_neutral_colocation",
            **evidence("vnet", retrieved_at),
            "published_portfolio": {
                "as_of": "2025-12-31",
                "wholesale_capacity_in_service_mw": 889,
                "retail_cabinets_in_service": 49863,
                "network_pops": 224,
                "wholesale_market_capacity_mw": {"greater_beijing_area": 578, "yangtze_river_delta": 311},
                "retail_self_built_cabinets_approx": {"greater_beijing_area": 25900, "yangtze_river_delta": 9300, "greater_bay_area": 6600, "other": 4300},
            },
            "canonical_generation_status": "gated_aggregate_capacity_and_market_footprints_only",
            "next_step": "Track annual-report portfolio tables and request a provider-approved self-built facility list; keep partnered sites distinct from owned/self-built sites.",
        },
        {
            "operator": "Chindata",
            "operator_class": "hyperscale_data_center_operator",
            **evidence("chindata", retrieved_at),
            "corroborating_source": evidence("chindata-sangyuan", retrieved_at),
            "published_portfolio": {
                "location_clusters": ["Greater Beijing", "Yangtze River Delta", "Greater Bay Area", "Qingyang, Gansu", "Zhongwei, Ningxia", "Ulanqab, Inner Mongolia", "Yichang, Hubei"],
                "current_directory_codes": codes,
                "named_current_campus_example": "Sangyuan Cloud Computing Campus near Beijing",
            },
            "canonical_generation_status": "generated_four_current_directory_codes_with_null_geometry",
            "next_step": "Resolve code-to-campus aliases only when an official source explicitly supplies the mapping; then add provider coordinates or reviewed facility evidence.",
        },
    ]


def main() -> None:
    args = parse_args()
    tag = retrieval_tag(args.retrieved_at)
    for key, source in SOURCES.items():
        path = raw_path(key, args.retrieved_at)
        if args.fetch:
            fetch(str(source["url"]), path)
        if not path.exists():
            raise FileNotFoundError(f"raw snapshot missing: {path}; run with --fetch")
        write_provenance(
            path,
            source_url=str(source["url"]),
            retrieved_at=args.retrieved_at,
            media_type=str(source["media_type"]),
            source_published_at=source["published"],
            notes="Official public colocation source retained for separate operator assessment. Redistribution terms require review.",
        )
    records, codes = chindata_records(args.retrieved_at)
    report = write_layer(
        records=records,
        output_dir=args.output_root / "data/chindata",
        layer_name="data-centers",
        retrieved_at=args.retrieved_at,
        source_url=str(SOURCES["chindata"]["url"]),
        raw_path=raw_path("chindata", args.retrieved_at),
        parser_name="update_china_colocation.py:chindata",
        schema_path=args.schema,
        extra_report={
            "completeness": "partial_current_directory",
            "directory_code_count": len(codes),
            "facility_location_count": 0,
            "scope_warning": "Current codes are real provider directory entries, but the captured HTML exposes no city/address mapping.",
        },
    )
    assessment_path = args.output_root / "data/china-colocation" / f"operator-assessment.{tag}.json"
    write_json(assessment_path, {
        "assessment_date": args.retrieved_at,
        "canonical_location_records_generated": len(records),
        "market_separation": "Colocation and hyperscale data-center operators sell physical space, power, interconnection, and managed infrastructure; their facilities are not cloud regions, availability zones, or CDN POPs.",
        "operators": assessment_rows(args.retrieved_at, codes),
        "source_policy": "Official public, licensed, filing/tender, and reproducible observation evidence only; unauthorized or leaked inventories are excluded.",
    })
    print(json.dumps({"assessment": repo_ref(assessment_path), "chindata": {"record_count": report["record_count"], "geometry_null": report["geometry_null"]}}, sort_keys=True))


if __name__ == "__main__":
    main()
