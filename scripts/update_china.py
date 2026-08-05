#!/usr/bin/env python3
"""Generate provider-declared mainland-China cloud infrastructure layers."""

from __future__ import annotations

import argparse
import hashlib
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
    fetch,
    jurisdiction_scope,
    repo_ref,
    retrieval_tag,
    sha256,
    slug,
    write_json,
    write_layer,
    write_provenance,
)


SOURCES: dict[str, dict[str, str | None]] = {
    "baidu": {
        "url": "https://intl.cloud.baidu.com/zh/doc/BCC/s/0jwvyo603-intl",
        "path": "data/raw/baidu/bcc-service-domains.{tag}.html",
        "media_type": "text/html",
        "published": "2025-08-20",
    },
    "huawei": {
        "url": "https://support.huaweicloud.com/productdesc-cc/cc_01_0003.html",
        "path": "data/raw/huawei/cloud-connect-regions.{tag}.html",
        "media_type": "text/html",
        "published": "2026-01-29",
    },
    "huawei-iam": {
        "url": "https://support.huaweicloud.com/api-iam5/iam_02_1101.html",
        "path": "data/raw/huawei/iam-region-endpoints.{tag}.html",
        "media_type": "text/html",
        "published": "2026-04-24",
    },
    "huawei-rcp": {
        "url": "https://support.huaweicloud.com/usermanual-organizations/org_03_2028.html",
        "path": "data/raw/huawei/rcp-supported-regions.{tag}.html",
        "media_type": "text/html",
        "published": "2026-07-08",
    },
    "huawei-lts": {
        "url": "https://support.huaweicloud.com/intl/zh-cn/usermanual-lts/lts_03_0003.html",
        "path": "data/raw/huawei/lts-regions.{tag}.html",
        "media_type": "text/html",
        "published": "2026-02-11",
    },
    "volcano": {
        "url": "https://www.volcengine.com/api/doc/getDocDetail?LibraryID=6617&DocumentID=87001&lang=en",
        "path": "data/raw/volcano/regions-and-zones.{tag}.json",
        "media_type": "application/json",
        "published": "2025-09-26",
    },
    "kingsoft": {
        "url": "https://docs.ksyun.com/documents/6965",
        "path": "data/raw/kingsoft/kec-regions-and-zones.{tag}.html",
        "media_type": "text/html",
        "published": "2026-01-09",
    },
    "jd": {
        "url": "https://docs.jdcloud.com/cn/virtual-machines/regions-and-availabilityzones",
        "path": "data/raw/jd/cvm-regions-and-zones.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
    "tianyi": {
        "url": "https://www.ctyun.cn/document/10026755/10196575",
        "path": "data/raw/tianyi/vpc-resource-pools.{tag}.html",
        "media_type": "text/html",
        "published": "2026-06-24",
    },
    "unicom": {
        "url": "https://www.cucloud.cn/product/ecs.html",
        "path": "data/raw/unicom/ecs-product.{tag}.html",
        "media_type": "text/html",
        "published": None,
    },
}

DATASETS = ("baidu", "huawei", "volcano", "kingsoft", "jd", "tianyi")
SOURCE_DEPENDENCIES = {
    "baidu": ("baidu",),
    "huawei": ("huawei", "huawei-iam", "huawei-rcp", "huawei-lts"),
    "volcano": ("volcano",),
    "kingsoft": ("kingsoft",),
    "jd": ("jd",),
    "tianyi": ("tianyi",),
}

CITY_NAMES = {
    "北京": "Beijing",
    "保定": "Baoding",
    "广州": "Guangzhou",
    "苏州": "Suzhou",
    "香港": "Hong Kong",
    "中国香港": "Hong Kong",
    "武汉": "Wuhan",
    "成都": "Chengdu",
    "上海": "Shanghai",
    "乌兰察布": "Ulanqab",
    "深圳": "Shenzhen",
    "贵阳": "Guiyang",
    "芜湖": "Wuhu",
    "庆阳": "Qingyang",
    "宁夏": None,
    "海东": "Haidong",
    "杭州": "Hangzhou",
    "合肥": "Hefei",
    "九江": "Jiujiang",
    "南京": "Nanjing",
    "长沙": "Changsha",
    "郴州": "Chenzhou",
    "佛山": "Foshan",
    "福州": "Fuzhou",
    "海口": "Haikou",
    "南宁": "Nanning",
    "厦门": "Xiamen",
    "兰州": "Lanzhou",
    "乌鲁木齐": "Urumqi",
    "西安": "Xi'an",
    "西宁": "Xining",
    "中卫": "Zhongwei",
    "重庆": "Chongqing",
    "昆明": "Kunming",
    "拉萨": "Lhasa",
    "晋中": "Jinzhong",
    "辽阳": "Liaoyang",
    "石家庄": "Shijiazhuang",
    "南昌": "Nanchang",
    "呼和浩特": "Hohhot",
    "青岛": "Qingdao",
    "沈阳": "Shenyang",
    "太原": "Taiyuan",
    "郑州": "Zhengzhou",
    "宿迁": "Suqian",
    "大同": "Datong",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("all", *DATASETS), default="all")
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def source_path(key: str, retrieved_at: str) -> Path:
    return REPO_ROOT / str(SOURCES[key]["path"]).format(tag=retrieval_tag(retrieved_at))


def provider_record(
    *,
    prefix: str,
    identifier: str,
    provider: str,
    service: str,
    entity_type: str,
    collection: str,
    source_record_id: str | None,
    name: str,
    city: str | None,
    country_code: str,
    source_key: str,
    retrieved_at: str,
    properties: dict[str, Any],
    parent_record_id: str | None = None,
    site_code: str | None = None,
    access_status: str = "public",
    service_scope: list[str] | None = None,
    aliases: list[str] | None = None,
    subdivision: str | None = None,
    confidence: str = "high",
) -> dict[str, Any]:
    raw_path = source_path(source_key, retrieved_at)
    country = "Hong Kong" if country_code == "HK" else "China"
    return canonical_record(
        schema_version=SCHEMA_VERSION,
        record_id=f"{prefix}:{entity_type}:{slug(identifier)}",
        aliases=sorted(set(aliases or [])),
        provider=provider,
        service=service,
        entity_type=entity_type,
        parent_record_id=parent_record_id,
        jurisdiction_scope=jurisdiction_scope(country_code),
        access_status=access_status,
        service_scope=service_scope or [],
        source_collection=collection,
        source_record_id=source_record_id,
        name=name,
        site_code=site_code,
        lifecycle_status="operational",
        source_scope="provider_declared",
        city=city,
        metro=city,
        subdivision=subdivision,
        country=country,
        country_code=country_code,
        latitude=None,
        longitude=None,
        location_precision="city" if city else "region",
        coordinate_method="unknown",
        coordinate_crs=None,
        source_url=str(SOURCES[source_key]["url"]),
        raw_source_ref=repo_ref(raw_path),
        source_sha256=sha256(raw_path),
        source_published_at=SOURCES[source_key]["published"],
        retrieved_at=retrieved_at,
        first_seen=retrieved_at,
        last_seen=retrieved_at,
        confidence=confidence,
        properties=properties,
    )


def parse_baidu(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("baidu", retrieved_at).read_bytes(), "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("Baidu BCC region table not found")
    records: list[dict[str, Any]] = []
    regions = []
    for row in table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) != 4:
            continue
        source_name, endpoint, protocol, zone_text = cells
        zones = re.findall(r"cn-[a-z]+-[a-z]", zone_text)
        if not zones:
            raise ValueError(f"Baidu zones missing for {source_name}")
        region_ids = {re.sub(r"-[a-z]$", "", zone) for zone in zones}
        if len(region_ids) != 1:
            raise ValueError(f"Baidu zone prefixes disagree for {source_name}: {zones}")
        region_id = next(iter(region_ids))
        country_code = "HK" if source_name == "香港" else "CN"
        city = CITY_NAMES[source_name]
        region_record_id = f"baidu:cloud_region:{slug(region_id)}"
        records.append(provider_record(
            prefix="baidu", identifier=region_id, provider="Baidu AI Cloud", service="baidu_cloud",
            entity_type="cloud_region", collection="baidu_bcc_service_domains", source_record_id=endpoint,
            name=source_name, city=city, country_code=country_code, source_key="baidu",
            retrieved_at=retrieved_at, site_code=region_id, service_scope=["compute"], aliases=[source_name],
            properties={
                "api_endpoint": endpoint,
                "declared_zone_count": len(zones),
                "identity_basis": "common prefix of provider-published ZoneIDs",
                "protocol": protocol,
                "source_name": source_name,
            },
        ))
        for zone_id in zones:
            records.append(provider_record(
                prefix="baidu", identifier=zone_id, provider="Baidu AI Cloud", service="baidu_cloud",
                entity_type="availability_zone", collection="baidu_bcc_service_domains",
                source_record_id=zone_id, name=zone_id, city=city, country_code=country_code,
                source_key="baidu", retrieved_at=retrieved_at, parent_record_id=region_record_id,
                site_code=zone_id, service_scope=["compute"],
                properties={"api_endpoint": endpoint, "parent_region_id": region_id, "source_region_name": source_name},
            ))
        regions.append((region_id, country_code, len(zones)))
    return records, {
        "region_count": len(regions),
        "availability_zone_count": sum(value[2] for value in regions),
        "mainland_region_count": sum(value[1] == "CN" for value in regions),
        "mainland_availability_zone_count": sum(value[2] for value in regions if value[1] == "CN"),
        "hong_kong_kept_separate": True,
    }


def _table_region_crosswalk(path: Path) -> dict[str, str]:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    result: dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all(["th", "td"])]
            if len(cells) >= 2 and re.fullmatch(r"(?:cn|ap)-[a-z]+-[0-9]+", cells[1]):
                result[cells[0]] = cells[1]
    return result


def parse_huawei(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("huawei", retrieved_at).read_bytes(), "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("Huawei region table not found")
    names: list[str] = []
    in_mainland = False
    for row in table.find_all("tr")[1:]:
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        if cells[0] == "中国大陆":
            in_mainland = True
            names.append(cells[1])
            continue
        if cells[0] == "亚太":
            break
        if in_mainland:
            names.append(cells[0])
    names = [re.sub(r"\s+您在控制台.*$", "", name) for name in names]
    crosswalk: dict[str, str] = {}
    auxiliary = []
    for key in ("huawei-iam", "huawei-rcp", "huawei-lts"):
        path = source_path(key, retrieved_at)
        crosswalk.update(_table_region_crosswalk(path))
        auxiliary.append({"raw_source_ref": repo_ref(path), "sha256": sha256(path), "source_url": SOURCES[key]["url"]})
    missing = [name for name in names if name not in crosswalk]
    if missing:
        raise ValueError(f"Huawei RegionID crosswalk missing: {missing}")
    source_city = {
        "华北-北京一": "北京", "华北-北京四": "北京", "华北-乌兰察布一": "乌兰察布",
        "华东-上海一": "上海", "华东-上海二": "上海", "华南-广州": "广州",
        "华南-深圳": "深圳", "西南-贵阳一": "贵阳", "华东二": "芜湖",
    }
    records = []
    for name in names:
        region_id = crosswalk[name]
        chinese_city = source_city[name]
        records.append(provider_record(
            prefix="huawei", identifier=region_id, provider="Huawei Cloud", service="huawei_cloud",
            entity_type="cloud_region", collection="huawei_cloud_connect_regions",
            source_record_id=region_id, name=name, city=CITY_NAMES[chinese_city], country_code="CN",
            source_key="huawei", retrieved_at=retrieved_at, site_code=region_id,
            service_scope=["cloud_connect"], aliases=[name],
            properties={
                "region_id_crosswalk_sources": auxiliary,
                "source_city_name": chinese_city,
                "source_name": name,
                "scope_warning": "Membership comes from the Cloud Connect supported-region page; product availability can differ.",
            },
        ))
    return records, {
        "mainland_region_count": len(records),
        "availability_zone_count": None,
        "availability_zone_status": "not generated; no unauthenticated universal AZ inventory was established",
        "auxiliary_region_id_sources": auxiliary,
        "service_scope": "cloud_connect",
    }


def _operation_text(value: dict[str, Any]) -> list[str]:
    result = []
    for operation in value.get("ops", []):
        inserted = operation.get("insert")
        if isinstance(inserted, str):
            cleaned = inserted.strip()
            if cleaned and cleaned != "*":
                result.append(cleaned)
    return result


def parse_volcano(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(source_path("volcano", retrieved_at).read_text(encoding="utf-8"))
    result = payload.get("Result") or {}
    content = json.loads(result["Content"])
    grouped: dict[str, list[str]] = defaultdict(list)
    for key, value in content["data"].items():
        match = re.match(r"^(xr[0-9a-z]+)xc1", key)
        if match:
            grouped[match.group(1)].extend(_operation_text(value))
    rows = []
    for values in grouped.values():
        joined = "\n".join(values)
        region_match = re.search(r"\b(cn-(?:beijing|shanghai|guangzhou|hongkong))\b", joined)
        zones = sorted(set(re.findall(r"\bcn-(?:beijing|shanghai|guangzhou|hongkong)-[a-z]\b", joined)))
        if not region_match or not zones:
            continue
        region_id = region_match.group(1)
        count = next((int(value) for value in values if re.fullmatch(r"\d+", value)), None)
        rows.append((region_id, count, zones, values))
    rows.sort()
    source_names = {
        "cn-beijing": ("华北2（北京）", "北京", "CN"),
        "cn-shanghai": ("华东2（上海）", "上海", "CN"),
        "cn-guangzhou": ("华南1（广州）", "广州", "CN"),
        "cn-hongkong": ("中国香港", "香港", "HK"),
    }
    records = []
    discrepancies = []
    for region_id, declared, zones, values in rows:
        name, chinese_city, country_code = source_names[region_id]
        city = CITY_NAMES[chinese_city]
        if declared != len(zones):
            discrepancies.append({"region_id": region_id, "declared_zone_count": declared, "explicit_zone_id_count": len(zones)})
        region_record_id = f"volcano:cloud_region:{slug(region_id)}"
        records.append(provider_record(
            prefix="volcano", identifier=region_id, provider="Volcano Engine", service="volcano_cloud",
            entity_type="cloud_region", collection="volcano_regions_and_zones", source_record_id=region_id,
            name=name, city=city, country_code=country_code, source_key="volcano", retrieved_at=retrieved_at,
            site_code=region_id, service_scope=["auto_scaling"], aliases=[name],
            properties={
                "declared_zone_count": declared,
                "explicit_zone_id_count": len(zones),
                "publication_status": "general_availability",
                "source_document_id": result.get("DocumentID"),
                "source_library": result.get("LibraryCode"),
                "source_name": name,
            },
        ))
        for zone_id in zones:
            records.append(provider_record(
                prefix="volcano", identifier=zone_id, provider="Volcano Engine", service="volcano_cloud",
                entity_type="availability_zone", collection="volcano_regions_and_zones", source_record_id=zone_id,
                name=zone_id, city=city, country_code=country_code, source_key="volcano",
                retrieved_at=retrieved_at, parent_record_id=region_record_id, site_code=zone_id,
                service_scope=["auto_scaling"],
                properties={"parent_region_id": region_id, "publication_status": "general_availability"},
            ))
    return records, {
        "region_count": len(rows),
        "availability_zone_count_from_explicit_ids": sum(len(row[2]) for row in rows),
        "availability_zone_count_declared": sum(row[1] or 0 for row in rows),
        "source_count_discrepancies": discrepancies,
        "offline_predecessor_document": "LibraryID 6534 / DocumentID 1131814 now returns document-is-not-online",
    }


def parse_kingsoft(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("kingsoft", retrieved_at).read_bytes(), "html.parser")
    table = next((table for table in soup.find_all("table") if "地域及代码" in table.get_text(" ")), None)
    if table is None:
        raise ValueError("Kingsoft region table not found")
    source_city = {
        "cn-beijing-6": "北京", "cn-beijing-fin": "北京", "cn-shanghai-2": "上海",
        "cn-shanghai-fin": "上海", "cn-guangzhou-1": "广州", "cn-northwest-1": "庆阳",
        "cn-northwest-3": "宁夏", "cn-northwest-4": "海东",
    }
    records = []
    regions = []
    for row in table.find_all("tr")[1:]:
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all("td")]
        if len(cells) != 2:
            continue
        region_text, zone_text = cells
        region_match = re.search(r"\b((?:cn|ap)-[a-z0-9-]+)\b", region_text)
        if not region_match or not region_match.group(1).startswith("cn-"):
            continue
        region_id = region_match.group(1)
        zones = re.findall(r"\bcn-[a-z0-9-]+[a-z]\b", zone_text)
        dedicated = "金融" in region_text
        chinese_city = source_city[region_id]
        city = CITY_NAMES[chinese_city]
        access = "dedicated" if dedicated else "public"
        scope = ["compute", "financial_cloud"] if dedicated else ["compute"]
        region_record_id = f"kingsoft:cloud_region:{slug(region_id)}"
        records.append(provider_record(
            prefix="kingsoft", identifier=region_id, provider="Kingsoft Cloud", service="kingsoft_cloud",
            entity_type="cloud_region", collection="kingsoft_kec_regions_and_zones", source_record_id=region_id,
            name=region_text, city=city, country_code="CN", source_key="kingsoft", retrieved_at=retrieved_at,
            site_code=region_id, access_status=access, service_scope=scope, aliases=[region_text],
            properties={"declared_zone_count": len(zones), "specialized_financial_region": dedicated, "source_city_name": chinese_city},
        ))
        for zone_id in zones:
            records.append(provider_record(
                prefix="kingsoft", identifier=zone_id, provider="Kingsoft Cloud", service="kingsoft_cloud",
                entity_type="availability_zone", collection="kingsoft_kec_regions_and_zones", source_record_id=zone_id,
                name=zone_id, city=city, country_code="CN", source_key="kingsoft", retrieved_at=retrieved_at,
                parent_record_id=region_record_id, site_code=zone_id, access_status=access, service_scope=scope,
                properties={"parent_region_id": region_id, "specialized_financial_region": dedicated},
            ))
        regions.append((region_id, dedicated, len(zones)))
    return records, {
        "mainland_region_count": len(regions),
        "availability_zone_count": sum(value[2] for value in regions),
        "financial_region_count": sum(value[1] for value in regions),
        "financial_zone_count": sum(value[2] for value in regions if value[1]),
        "excluded_non_mainland_regions": ["ap-singapore-1"],
    }


def parse_jd(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    html = source_path("jd", retrieved_at).read_text(encoding="utf-8")
    match = re.search(r'dn\.content=("(?:\\.|[^"\\])*")', html)
    if not match:
        raise ValueError("JD Cloud embedded documentation content not found")
    markdown = json.loads(match.group(1))
    grouped: dict[str, dict[str, Any]] = {}
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        region_match = re.search(r"\b(cn-(?:north|east|south)-\d+)\b", " ".join(cells))
        zone_match = re.search(r"\b(cn-(?:north|east|south)-\d+[a-z])\b", " ".join(cells))
        if not region_match or not zone_match:
            continue
        region_id, zone_id = region_match.group(1), zone_match.group(1)
        city_cn = cells[-1]
        region_label = next(cell for cell in cells if region_id in cell)
        grouped.setdefault(region_id, {"name": region_label, "city_cn": city_cn, "zones": []})["zones"].append(zone_id)
    records = []
    for region_id, region in sorted(grouped.items()):
        city = CITY_NAMES[region["city_cn"]]
        region_record_id = f"jd:cloud_region:{slug(region_id)}"
        records.append(provider_record(
            prefix="jd", identifier=region_id, provider="JD Cloud", service="jd_cloud",
            entity_type="cloud_region", collection="jd_cvm_regions_and_zones", source_record_id=region_id,
            name=region["name"], city=city, country_code="CN", source_key="jd", retrieved_at=retrieved_at,
            site_code=region_id, service_scope=["compute"], aliases=[region["name"]],
            properties={"declared_zone_count": len(region["zones"]), "source_city_name": region["city_cn"]},
        ))
        for zone_id in sorted(set(region["zones"])):
            records.append(provider_record(
                prefix="jd", identifier=zone_id, provider="JD Cloud", service="jd_cloud",
                entity_type="availability_zone", collection="jd_cvm_regions_and_zones", source_record_id=zone_id,
                name=zone_id, city=city, country_code="CN", source_key="jd", retrieved_at=retrieved_at,
                parent_record_id=region_record_id, site_code=zone_id, service_scope=["compute"],
                properties={"parent_region_id": region_id},
            ))
    return records, {
        "mainland_region_count": len(grouped),
        "availability_zone_count": sum(len(set(value["zones"])) for value in grouped.values()),
        "parser_surface": "server-rendered Nuxt state containing Markdown",
        "console_availability_warning": True,
    }


def _pool_place(pool_name: str) -> tuple[str | None, str | None, str | None]:
    if pool_name == "西南2-贵州" or pool_name.startswith("贵州"):
        return None, "Guizhou", "贵州"
    if pool_name.startswith("宁夏"):
        return None, "Ningxia", "宁夏"
    if pool_name.startswith("内蒙"):
        return None, "Inner Mongolia", "内蒙"
    for chinese, english in sorted(CITY_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        if english and pool_name.startswith(chinese):
            return english, None, chinese
    return None, None, None


def _pool_identifier(pool_name: str) -> str:
    return "vpc-" + hashlib.sha256(pool_name.encode("utf-8")).hexdigest()[:16]


def _pool_block(block: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for match in re.finditer(r"(华东|华南|西北|西南|北方)地区：\s*([^\n]+)", block):
        group, names = match.groups()
        result.extend((group, name.strip()) for name in names.split("/") if name.strip())
    return result


def parse_tianyi(retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    soup = BeautifulSoup(source_path("tianyi", retrieved_at).read_bytes(), "html.parser")
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    start = text.find("地域资源池是没有可用区概念的资源池")
    if start < 0:
        raise ValueError("Tianyi resource-pool definition not found")
    section = text[start:]
    regional_match = re.search(r"地域资源池包含以下资源池：\s*(.*?)\s*可用区资源池包含以下资源池：", section, re.S)
    az_match = re.search(r"可用区资源池包含以下资源池：\s*(.*?)\s*具体区别如下：", section, re.S)
    if not regional_match or not az_match:
        raise ValueError("Tianyi resource-pool lists not found")
    pools = [("regional", *value) for value in _pool_block(regional_match.group(1))]
    pools += [("az_capable", *value) for value in _pool_block(az_match.group(1))]
    records = []
    group_names = {"华东": "east", "华南": "south", "西北": "northwest", "西南": "southwest", "北方": "north"}
    for architecture, group, pool_name in pools:
        city, subdivision, place_basis = _pool_place(pool_name)
        records.append(provider_record(
            prefix="ctyun", identifier=_pool_identifier(pool_name), provider="China Telecom Tianyi Cloud",
            service="ctyun_cloud", entity_type="cloud_resource_pool", collection="ctyun_vpc_resource_pools",
            source_record_id=pool_name, name=pool_name, city=city, subdivision=subdivision, country_code="CN",
            source_key="tianyi", retrieved_at=retrieved_at, service_scope=["vpc"], aliases=[pool_name],
            properties={
                "pool_architecture": architecture,
                "region_group": group_names[group],
                "region_group_source": group,
                "source_place_basis": place_basis,
                "zone_children_generated": False,
            },
        ))
    regional_count = sum(row[0] == "regional" for row in pools)
    az_count = sum(row[0] == "az_capable" for row in pools)
    return records, {
        "resource_pool_count": len(records),
        "regional_resource_pool_count": regional_count,
        "availability_zone_capable_resource_pool_count": az_count,
        "availability_zone_records_generated": 0,
        "identity_method": "SHA-256 of the provider-published Chinese pool label; no provider ID is published on this page",
        "scope_warning": "This is a VPC product inventory. Other Tianyi products can expose different resource-pool sets.",
    }


PARSERS: dict[str, Callable[[str], tuple[list[dict[str, Any]], dict[str, Any]]]] = {
    "baidu": parse_baidu,
    "huawei": parse_huawei,
    "volcano": parse_volcano,
    "kingsoft": parse_kingsoft,
    "jd": parse_jd,
    "tianyi": parse_tianyi,
}

OUTPUTS = {
    "baidu": ("data/baidu", "regions-and-zones", "baidu"),
    "huawei": ("data/huawei", "mainland-regions", "huawei"),
    "volcano": ("data/volcano", "regions-and-zones", "volcano"),
    "kingsoft": ("data/kingsoft", "mainland-regions-and-zones", "kingsoft"),
    "jd": ("data/jd", "mainland-regions-and-zones", "jd"),
    "tianyi": ("data/tianyi", "vpc-resource-pools", "tianyi"),
}


def write_provider_assessment(output_root: Path, retrieved_at: str, summaries: dict[str, dict[str, Any]]) -> None:
    tag = retrieval_tag(retrieved_at)
    providers = [
        {"provider": "Alibaba Cloud", "tier": "market_leader", "generation_status": "generated_existing_and_mainland_view", "source_url": "https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones"},
        {"provider": "Huawei Cloud", "tier": "market_leader", "generation_status": "generated_region_only", "source_url": SOURCES["huawei"]["url"]},
        {"provider": "Tencent Cloud", "tier": "market_leader", "generation_status": "generated_existing_and_mainland_view", "source_url": "https://intl.cloud.tencent.com/document/product/416/64284?lang=en"},
        {"provider": "China Telecom Tianyi Cloud", "tier": "top_five_operator_cloud", "generation_status": "generated_vpc_resource_pools", "source_url": SOURCES["tianyi"]["url"]},
        {"provider": "China Mobile Cloud", "tier": "top_five_operator_cloud", "generation_status": "gated_no_itemized_authoritative_inventory", "source_url": "https://ecloud.10086.cn/", "blocker": "The public site did not yield a stable itemized region, zone, or resource-pool directory during this audit."},
        {"provider": "Baidu AI Cloud", "tier": "coverage_priority", "generation_status": "generated_bcc_regions_and_zones", "source_url": SOURCES["baidu"]["url"]},
        {"provider": "Volcano Engine", "tier": "coverage_priority", "generation_status": "generated_current_live_document", "source_url": SOURCES["volcano"]["url"]},
        {"provider": "China Unicom Cloud", "tier": "coverage_priority", "generation_status": "gated_no_itemized_authoritative_inventory", "source_url": SOURCES["unicom"]["url"], "blocker": "The public ECS product page is a client-rendered shell and does not expose a consolidated authoritative inventory."},
        {"provider": "Kingsoft Cloud", "tier": "coverage_priority", "generation_status": "generated_kec_regions_and_zones", "source_url": SOURCES["kingsoft"]["url"]},
        {"provider": "JD Cloud", "tier": "coverage_priority", "generation_status": "generated_cvm_regions_and_zones", "source_url": SOURCES["jd"]["url"]},
    ]
    write_json(output_root / "data/china" / f"provider-assessment.{tag}.json", {
        "assessment_date": retrieved_at,
        "market_definition": "Mainland-China public cloud infrastructure; positions six through ten are a coverage-priority cohort, not a claimed exact market-share order.",
        "market_evidence": [
            "https://www.businesswire.com/news/home/20260209034854/en/Omdia-Mainland-Chinas-cloud-infrastructure-market-accelerates-to-24-growth-in-Q3-2025",
            "https://www.idc.com/resource-center/blog/%E5%85%AC%E6%9C%89%E4%BA%91iaas%E5%B8%82%E5%9C%BA%E5%A2%9E%E9%80%9F%E9%87%8D%E5%9B%9E20%E7%9A%84%E8%83%8C%E5%90%8E%EF%BC%9A-ai-%E7%BA%A2%E5%88%A9%E8%8A%B1%E8%90%BD%E8%B0%81%E5%AE%B6%EF%BC%9F/",
        ],
        "providers": providers,
        "generated_summaries": {key: {"record_count": value["record_count"], "geometry_null": value["geometry_null"]} for key, value in summaries.items()},
        "generation_gate": "No canonical location is emitted from an aggregate marketing count, endpoint guess, or undocumented console label.",
    })


def main() -> None:
    args = parse_args()
    retrieval_tag(args.retrieved_at)
    selected = DATASETS if args.dataset == "all" else (args.dataset,)
    source_keys = {key for dataset in selected for key in SOURCE_DEPENDENCIES[dataset]}
    if args.dataset == "all":
        source_keys.add("unicom")
    for key in sorted(source_keys):
        config = SOURCES[key]
        path = source_path(key, args.retrieved_at)
        if args.fetch:
            fetch(str(config["url"]), path)
        if not path.exists():
            raise FileNotFoundError(f"raw snapshot missing: {path}; run with --fetch")
        write_provenance(
            path,
            source_url=str(config["url"]),
            retrieved_at=args.retrieved_at,
            media_type=str(config["media_type"]),
            source_published_at=config["published"],
            notes="Immutable official provider snapshot used by scripts/update_china.py. Redistribution rights for provider documentation require review.",
        )
    summaries: dict[str, dict[str, Any]] = {}
    for dataset in selected:
        records, extra = PARSERS[dataset](args.retrieved_at)
        output_dir, layer_name, source_key = OUTPUTS[dataset]
        report = write_layer(
            records=records,
            output_dir=args.output_root / output_dir,
            layer_name=layer_name,
            retrieved_at=args.retrieved_at,
            source_url=str(SOURCES[source_key]["url"]),
            raw_path=source_path(source_key, args.retrieved_at),
            parser_name=f"update_china.py:{dataset}",
            schema_path=args.schema,
            extra_report=extra,
        )
        summaries[dataset] = report
        if dataset in {"baidu", "volcano"}:
            mainland = [record for record in records if record["jurisdiction_scope"] == "mainland_china"]
            mainland_report = write_layer(
                records=mainland,
                output_dir=args.output_root / output_dir,
                layer_name="mainland-regions-and-zones",
                retrieved_at=args.retrieved_at,
                source_url=str(SOURCES[source_key]["url"]),
                raw_path=source_path(source_key, args.retrieved_at),
                parser_name=f"update_china.py:{dataset}:mainland",
                schema_path=args.schema,
                extra_report={
                    "derived_from_layer": f"{output_dir}/{layer_name}",
                    "jurisdiction_filter": "mainland_china",
                    "cloud_region_count": sum(record["entity_type"] == "cloud_region" for record in mainland),
                    "availability_zone_count": sum(record["entity_type"] == "availability_zone" for record in mainland),
                },
            )
            summaries[f"{dataset}-mainland"] = mainland_report
    write_provider_assessment(args.output_root, args.retrieved_at, summaries)
    print(json.dumps({key: {"record_count": value["record_count"], "geometry_null": value["geometry_null"]} for key, value in summaries.items()}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
