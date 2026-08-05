#!/usr/bin/env python3
"""Archive and assess provider-declared China edge/CDN coverage."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, fetch, repo_ref, retrieval_tag, sha256, write_json, write_provenance


SOURCES: dict[str, dict[str, str | None]] = {
    "wangsu": {
        "url": "https://online.wangsu.com/product/cdn",
        "path": "data/raw/china-edge/wangsu-cdn.{tag}.html",
        "published": None,
    },
    "alibaba": {
        "url": "https://help.aliyun.com/zh/cdn/product-overview/pop-distribution",
        "path": "data/raw/china-edge/alibaba-cdn-pop-distribution.{tag}.html",
        "published": None,
    },
    "tencent": {
        "url": "https://intl.cloud.tencent.com/products/cdn",
        "path": "data/raw/china-edge/tencent-cdn.{tag}.html",
        "published": None,
    },
    "huawei": {
        "url": "https://support.huaweicloud.com/intl/zh-cn/productdesc-cdn/cdn_01_0110.html",
        "path": "data/raw/china-edge/huawei-cdn-node-distribution.{tag}.html",
        "published": "2026-04-27",
    },
    "baidu": {
        "url": "https://intl.cloud.baidu.com/zh/doc/CDN/s/Ojwvydwwl-intl",
        "path": "data/raw/china-edge/baidu-cdn-advantages.{tag}.html",
        "published": "2025-08-21",
    },
    "volcano": {
        "url": "https://www.volcengine.com/product/CDN",
        "path": "data/raw/china-edge/volcano-cdn.{tag}.html",
        "published": None,
    },
    "tianyi": {
        "url": "https://www.ctyun.cn/document/10015932/10134360",
        "path": "data/raw/china-edge/tianyi-cdn-node-distribution.{tag}.html",
        "published": "2025-10-30",
    },
    "unicom": {
        "url": "https://support.cucloud.cn/document/127/590/149.html?arcid=269&id=149",
        "path": "data/raw/china-edge/unicom-cdn-introduction.{tag}.html",
        "published": "2026-01-16",
    },
    "baishan": {
        "url": "https://intl.baishancloud.com/",
        "path": "data/raw/china-edge/baishan-edge-cloud.{tag}.html",
        "published": None,
    },
}


MAINLAND_PROVINCES = [
    "Anhui", "Beijing", "Chongqing", "Fujian", "Gansu", "Guangdong", "Guangxi",
    "Guizhou", "Hainan", "Hebei", "Heilongjiang", "Henan", "Hubei", "Hunan",
    "Inner Mongolia", "Jiangsu", "Jiangxi", "Jilin", "Liaoning", "Ningxia",
    "Qinghai", "Shaanxi", "Shandong", "Shanghai", "Shanxi", "Sichuan", "Tianjin",
    "Tibet", "Xinjiang", "Yunnan", "Zhejiang",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def raw_path(key: str, retrieved_at: str) -> Path:
    return REPO_ROOT / str(SOURCES[key]["path"]).format(tag=retrieval_tag(retrieved_at))


def source_evidence(key: str, retrieved_at: str) -> dict[str, Any]:
    path = raw_path(key, retrieved_at)
    return {
        "raw_source_ref": repo_ref(path),
        "source_published_at": SOURCES[key]["published"],
        "source_sha256": sha256(path),
        "source_url": SOURCES[key]["url"],
    }


def provider_rows(retrieved_at: str) -> list[dict[str, Any]]:
    common_path = [
        "request a provider-approved site or IP allowlist when the product offers one",
        "collect reproducible DNS/BGP/TLS observations with timestamps and measurement scope",
        "join licensed PeeringDB/IX/facility evidence without treating it as provider ownership proof",
    ]
    rows: list[dict[str, Any]] = [
        {
            "provider": "Wangsu Science & Technology",
            "provider_class": "independent_cdn",
            "source_key": "wangsu",
            "declared_coverage": {"global_node_count_min": 2800, "countries_and_regions_min": 70, "carrier_count_min": 100},
            "published_granularity": "aggregate_global_fleet",
        },
        {
            "provider": "Alibaba Cloud CDN",
            "provider_class": "cloud_cdn",
            "source_key": "alibaba",
            "declared_coverage": {
                "global_node_count_min": 3200,
                "mainland_node_count_min": 2300,
                "outside_mainland_node_count_min": 900,
                "mainland_provincial_areas": MAINLAND_PROVINCES,
                "network_bandwidth_tbps": 180,
            },
            "published_granularity": "aggregate_fleet_plus_province_coverage",
        },
        {
            "provider": "Tencent Cloud CDN",
            "provider_class": "cloud_cdn",
            "source_key": "tencent",
            "declared_coverage": {
                "global_node_count_min": 3200,
                "mainland_node_count_min": 2300,
                "outside_mainland_node_count_min": 900,
                "countries_and_regions_min": 70,
                "network_bandwidth_tbps": 400,
            },
            "published_granularity": "aggregate_fleet",
        },
        {
            "provider": "Huawei Cloud CDN",
            "provider_class": "cloud_cdn",
            "source_key": "huawei",
            "declared_coverage": {
                "mainland_node_count_min": 2000,
                "outside_mainland_node_count_min": 800,
                "mainland_provincial_areas": MAINLAND_PROVINCES,
                "countries_and_regions_min": 130,
                "carrier_count_min": 1600,
                "network_bandwidth_tbps": 180,
            },
            "published_granularity": "aggregate_fleet_plus_province_coverage",
        },
        {
            "provider": "Baidu AI Cloud CDN",
            "provider_class": "cloud_cdn",
            "source_key": "baidu",
            "declared_coverage": {
                "mainland_node_count_min": 2500,
                "outside_mainland_node_count_min": 800,
                "mainland_provincial_areas": MAINLAND_PROVINCES,
                "outside_mainland_countries_and_regions_min": 70,
                "mainland_network_bandwidth_tbps": 150,
                "outside_mainland_network_bandwidth_tbps": 50,
            },
            "published_granularity": "aggregate_fleet_plus_province_coverage",
        },
        {
            "provider": "Volcano Engine CDN",
            "provider_class": "cloud_cdn",
            "source_key": "volcano",
            "declared_coverage": {"global_node_count_min": 3500, "outside_mainland_countries_and_regions_min": 70, "network_bandwidth_tbps_min": 150},
            "published_granularity": "aggregate_global_fleet",
        },
        {
            "provider": "China Telecom Tianyi Cloud CDN",
            "provider_class": "carrier_cdn",
            "source_key": "tianyi",
            "declared_coverage": {
                "mainland_node_count_min": 2000,
                "outside_mainland_node_count_min": 800,
                "mainland_provincial_areas": MAINLAND_PROVINCES,
                "network_bandwidth_tbps": 160,
            },
            "published_granularity": "aggregate_fleet_plus_province_coverage",
        },
        {
            "provider": "China Mobile Cloud CDN",
            "provider_class": "carrier_cdn",
            "source_key": None,
            "source_url": "https://ecloud.10086.cn/",
            "declared_coverage": {},
            "published_granularity": "no_stable_public_inventory_retrieved",
            "blocker": "The official product surface was not stably retrievable and no itemized public node directory was established.",
        },
        {
            "provider": "China Unicom Cloud CDN",
            "provider_class": "carrier_cdn",
            "source_key": "unicom",
            "declared_coverage": {"mainland_scope": "nationwide"},
            "published_granularity": "qualitative_nationwide_claim",
        },
        {
            "provider": "BaishanCloud",
            "provider_class": "independent_edge_cloud",
            "source_key": "baishan",
            "declared_coverage": {"global_edge_node_count_min": 1700, "covered_city_count_min": 300, "international_carrier_partners_min": 150, "redundancy_bandwidth_tbps": 80},
            "published_granularity": "aggregate_global_fleet",
        },
    ]
    for row in rows:
        key = row.pop("source_key")
        if key:
            row.update(source_evidence(key, retrieved_at))
        else:
            row.setdefault("raw_source_ref", None)
            row.setdefault("source_published_at", None)
            row.setdefault("source_sha256", None)
        row["canonical_location_generation"] = "gated_no_itemized_site_identifiers"
        row["lawful_enrichment_paths"] = common_path
    return rows


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
            media_type="text/html",
            source_published_at=source["published"],
            notes="Official public edge/CDN source retained for aggregate coverage assessment; not an itemized POP inventory. Redistribution terms require review.",
        )
    rows = provider_rows(args.retrieved_at)
    output = args.output_root / "data/china-edge" / f"provider-assessment.{tag}.json"
    write_json(output, {
        "assessment_date": args.retrieved_at,
        "canonical_location_records_generated": 0,
        "cohort_definition": "Ten high-priority mainland-China CDN/edge providers; this is a coverage cohort, not a claimed exact revenue ranking.",
        "coverage_semantics": "Province, country, city-count, bandwidth, and fleet-total claims describe service coverage only and do not identify physical POPs.",
        "excluded_source_classes": [
            "unauthorized or leaked inventories",
            "credential-gated exports obtained without provider authorization",
            "private customer or employee material without a redistribution basis",
        ],
        "providers": rows,
        "source_policy": "Provider-approved, licensed, public filing/tender, and reproducible active-measurement evidence only.",
    })
    print(json.dumps({"output": repo_ref(output), "provider_count": len(rows), "canonical_location_records_generated": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
