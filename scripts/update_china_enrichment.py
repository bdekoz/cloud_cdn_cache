#!/usr/bin/env python3
"""Implement source-scoped China cloud updates from retained public snapshots."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path

from china_enrichment_common import (
    DATE, TAG, CATALOG, cells, clean, evidence, location, source, source_bytes,
    sources, soup,
)
from location_common import REPO_ROOT, repo_ref, sha256, slug, write_json, write_layer


def table_with(key, column):
    matches = [t for t in soup(key).find_all("table") if column in clean(t.find("tr").get_text(" ", strip=True))]
    if not matches:
        raise ValueError(f"No {column} table in {key}")
    return matches


ALI_COUNTRIES = {
    "cn": "CN", "ap-southeast-1": "SG", "ap-southeast-3": "MY",
    "ap-southeast-5": "ID", "ap-southeast-6": "PH", "ap-southeast-7": "TH",
    "ap-southeast-8": "MY", "ap-northeast-1": "JP", "ap-northeast-2": "KR",
    "us-west-1": "US", "us-east-1": "US", "eu-central-1": "DE",
    "eu-west-1": "GB", "eu-west-2": "FR", "me-east-1": "AE",
    "me-central-1": "SA", "na-south-1": "MX", "sa-east-1": "BR",
}
TENCENT_COUNTRIES = {
    "ap-hongkong": "HK", "ap-singapore": "SG", "ap-johorbahru": "MY",
    "ap-jakarta": "ID", "ap-seoul": "KR", "ap-tokyo": "JP", "ap-osaka": "JP",
    "ap-bangkok": "TH", "me-saudi-arabia": "SA", "sa-saopaulo": "BR",
    "na-queretaro": "MX", "na-siliconvalley": "US", "na-ashburn": "US",
    "eu-frankfurt": "DE",
}


def parse_cloud_directory(vendor):
    key = vendor + "-directory"
    tables = table_with(key, "Zone ID" if vendor == "alibaba" else "AZ ID")
    rows, region = [], None
    scopes = Counter()
    for table_index, table in enumerate(tables):
        heading = table.find_previous(["h2", "h3", "h4"])
        label = clean(heading.get_text(" ", strip=True)) if heading else ""
        section = "financial_cloud" if "Finance" in label else "government_cloud" if "Gov" in label else "public_cloud"
        for tr in table.find_all("tr")[1:]:
            data = cells(tr)
            if not data:
                continue
            if not data[-1] and not any(data):
                continue
            region_id = data[1] if len(data) >= 5 and data[1] else None
            if region_id:
                name = data[0]
                if vendor == "tencent":
                    section = "financial_cloud" if region_id.endswith("-fsi") else "automotive_cloud" if region_id.endswith("-adc") else "public_cloud"
                code = ("HK" if region_id == "cn-hongkong" else "CN" if region_id.startswith("cn-") else ALI_COUNTRIES.get(region_id)) if vendor == "alibaba" else TENCENT_COUNTRIES.get(region_id, "CN" if table_index == 0 else None)
                if not code:
                    raise ValueError(f"Unreviewed geography: {region_id}")
                country_source = "explicit named locality in provider directory; normalized country identity"
                match = re.search(r"\(([^)]+)\)", name)
                city = clean(match.group(1).split(" - ")[0]) if match else None
                if vendor == "tencent":
                    if region_id == "ap-hongkong":
                        city = "Hong Kong"
                    elif section != "public_cloud":
                        city = next((c for c in ["Beijing", "Shanghai", "Shenzhen", "Zhongwei"] if c in name), None)
                if city is None and vendor == "alibaba":
                    city = "Singapore" if code == "SG" else None
                if section in {"financial_cloud", "government_cloud"} and vendor == "alibaba":
                    place = data[2]
                    place_match = re.search(r"\(([^)]+)\)", place)
                    city = place_match.group(1) if place_match else place
                closing, preview = "Closing Down" in name, "Preview" in name
                # A closure announcement is not proof that closure is complete.
                status = "unknown" if closing or preview else "operational"
                access = "unknown" if closing else "restricted" if section != "public_cloud" else "public"
                declared = int(data[3] if len(data) == 6 else data[2])
                region = location(key, vendor, "cloud_region", region_id, name,
                    "Alibaba Cloud" if vendor == "alibaba" else "Tencent Cloud", vendor + "_cloud",
                    country_code=code, city=city, source_record_id=region_id,
                    status=status, access=access, scope=[section], properties={
                        "declared_zone_count": declared, "country_identity_basis": country_source,
                        "closure_announced": closing, "closure_completed_not_asserted": closing,
                        "publication_status": "preview" if preview else "closing_down" if closing else "listed",
                        "partner_region": "Partner Region" in name,
                        "customer_dedication_not_asserted": section != "public_cloud",
                    })
                rows.append(region)
                scopes[section] += 1
            if region is None:
                raise ValueError("Orphan availability zone in directory")
            zone_name, zone_id = data[-2:]
            if not zone_id.startswith(("cn-", "ap-", "eu-", "us-", "me-", "na-", "sa-")):
                raise ValueError(f"Invalid provider zone ID: {zone_id}")
            restricted = "*" in zone_name
            access = "sales_restricted" if restricted and region["access_status"] == "public" else region["access_status"]
            rows.append(location(key, vendor, "availability_zone", zone_id,
                zone_name.replace("*", "").strip(), region["provider"], vendor + "_cloud",
                country_code=region["country_code"], city=region["city"], source_record_id=zone_id,
                parent=region["record_id"], status=region["lifecycle_status"], access=access,
                scope=region["service_scope"], properties={
                    "parent_region_id": region["source_record_id"], "sales_restricted": restricted,
                    "publication_status": region["properties"]["publication_status"],
                    "closure_completed_not_asserted": region["properties"]["closure_completed_not_asserted"],
                }))
    old_path = REPO_ROOT / f"data/{vendor}/regions-and-zones.20260804.geojson"
    previous = json.loads(old_path.read_text())["features"]
    old_ids = {r["properties"]["record_id"] for r in previous}
    new_ids = {r["record_id"] for r in rows}
    listed_count = len(rows)
    missing = []
    for feature in previous:
        old = copy.deepcopy(feature["properties"])
        if old["record_id"] in new_ids:
            continue
        old.update(latitude=None, longitude=None, coordinate_method="unknown", coordinate_crs=None,
                   lifecycle_status="unknown", access_status="unknown")
        old["properties"].update(latest_directory_listing="not_listed", missing_listing_is_not_retirement_proof=True,
                                 listing_review=evidence(key))
        rows.append(old)
        missing.append(old["record_id"])
    conflicts = []
    if vendor == "alibaba":
        conflicts.append({"region_id": "ap-southeast-8", "itemized_zone_count": 2,
                          "marketing_declared_zone_count": 3, "status": "unresolved",
                          "marketing_source": evidence("alibaba-marketing"),
                          "synthetic_zone_generated": False})
    corroboration = None
    if vendor == "tencent":
        chinese_ids = set()
        for table in soup("tencent-cvm-cn").find_all("table"):
            if "地域 ID" not in clean(table.find("tr").get_text(" ", strip=True)):
                continue
            for tr in table.find_all("tr")[1:]:
                for cell in cells(tr):
                    if re.fullmatch(r"(?:ap|eu|na|sa|me)-[a-z0-9-]+", cell):
                        chinese_ids.add(cell)
        english_ids = {r["source_record_id"] for r in rows if r["record_id"] in new_ids}
        corroboration = {"source": evidence("tencent-cvm-cn"),
                         "explicit_id_count": len(chinese_ids),
                         "ids_only_in_chinese_directory": sorted(chinese_ids - english_ids),
                         "ids_only_in_english_directory": sorted(english_ids - chinese_ids)}
    return rows, {"currently_listed_record_count": listed_count,
                  "retained_predecessor_ids_not_listed": missing,
                  "added_record_ids": sorted(new_ids - old_ids),
                  "scope_region_counts": dict(scopes), "source_conflicts": conflicts,
                  "chinese_directory_corroboration": corroboration,
                  "enrichment_sources": [evidence("alibaba-marketing", source_scope="provider_declared")] if vendor == "alibaba" else []}


HUAWEI_PLACES = {
    "Beijing": ("Beijing", "CN"), "Shanghai": ("Shanghai", "CN"), "Guangzhou": ("Guangzhou", "CN"),
    "Shenzhen": ("Shenzhen", "CN"), "Guiyang": ("Guiyang", "CN"), "Ulanqab": ("Ulanqab", "CN"),
    "Qingdao": ("Qingdao", "CN"), "Hong Kong": ("Hong Kong", "HK"), "Singapore": ("Singapore", "SG"),
    "Bangkok": ("Bangkok", "TH"), "Jakarta": ("Jakarta", "ID"), "Manila": ("Manila", "PH"),
    "Istanbul": ("Istanbul", "TR"), "Johannesburg": ("Johannesburg", "ZA"),
    "Mexico City": ("Mexico City", "MX"), "Sao Paulo": ("São Paulo", "BR"),
    "Santiago": ("Santiago", "CL"), "Riyadh": ("Riyadh", "SA"), "Cairo": ("Cairo", "EG"),
    "Dublin": ("Dublin", "IE"), "Paris": ("Paris", "FR"), "Abu Dhabi": ("Abu Dhabi", "AE"),
    "Buenos Aires": ("Buenos Aires", "AR"),
    "Kuala Lumpur": ("Kuala Lumpur", "MY"),
}


def huawei_place(label):
    for token, value in HUAWEI_PLACES.items():
        if token in label:
            return value
    if label.startswith("CN"):
        return None, "CN"
    raise ValueError(f"Unreviewed Huawei geography: {label}")


def parse_huawei():
    records = {}
    for key, scope in [("huawei-identity-policy", "iam_identity_policies"),
                       ("huawei-iam-global", "iam_api_endpoint"), ("huawei-rfs", "resource_formation")]:
        for table in table_with(key, "Region"):
            if not any("Region Code" in clean(tr.get_text(" ")) or "Region ID" in clean(tr.get_text(" ")) for tr in table.find_all("tr")[:2]):
                continue
            for tr in table.find_all("tr")[1:]:
                data = cells(tr)
                if len(data) < 2:
                    continue
                index = next((i for i, value in enumerate(data) if re.fullmatch(r"[a-z]{2}-[a-z0-9-]+", value)), None)
                if index is None:
                    continue
                region_id, label = data[index], data[index - 1]
                city, code = huawei_place(label)
                membership = evidence(key, service_scope=scope, source_region_label=label)
                if len(data) > index + 1:
                    membership["endpoint"] = data[index + 1]
                if region_id not in records:
                    records[region_id] = location(key, "huawei", "cloud_region", region_id, label,
                        "Huawei Cloud", "huawei_cloud", source_record_id=region_id, city=city,
                        country_code=code, scope=[], access="restricted" if "InvitationOnly" in label else "unknown",
                        properties={"universal_product_availability_not_asserted": True,
                                    "membership_sources": [], "availability_zone_ids_not_published": True})
                row = records[region_id]
                if label != row["name"]:
                    row["aliases"] = sorted(set(row["aliases"] + [label]))
                if scope not in row["service_scope"]:
                    row["service_scope"].append(scope)
                row["properties"]["membership_sources"].append(membership)
    # Reconcile the provider's Cloud Connect and trust selectors only by explicit
    # matching labels. Unknown selector labels remain source gaps, not new regions.
    label_index = {r["name"]: r for r in records.values()}
    missing_labels = []
    for key, scope in [("huawei-cloud-connect", "cloud_connect"), ("huawei-trust", "trust_region_selector")]:
        text = soup(key).get_text(" ", strip=True)
        for label, row in label_index.items():
            if label in text:
                row["properties"]["membership_sources"].append(evidence(key, service_scope=scope, source_region_label=label))
                if scope not in row["service_scope"]:
                    row["service_scope"].append(scope)
        if key == "huawei-cloud-connect":
            for tr in soup(key).find("table").find_all("tr")[1:]:
                data = cells(tr)
                label = data[-1].split(" When ")[0]
                if label not in label_index:
                    missing_labels.append({"source_id": key, "label": label})
    # Preserve historical memberships with original dates rather than relabeling
    # an older Cloud Connect declaration as a current universal catalog.
    predecessor = json.loads((REPO_ROOT / "data/huawei/mainland-regions.20260804.geojson").read_text())["features"]
    for feature in predecessor:
        old = feature["properties"]
        identifier = old["source_record_id"]
        if identifier not in records:
            retained = copy.deepcopy(old)
            retained.update(latitude=None, longitude=None, coordinate_method="unknown", coordinate_crs=None,
                            lifecycle_status="unknown")
            retained["properties"].update(latest_directory_listing="not_established", historical_membership_retained=True)
            records[identifier] = retained
        else:
            row = records[identifier]
            row["first_seen"] = old["first_seen"]
            row["properties"]["historical_membership"] = {
                "source_url": old["source_url"], "raw_source_ref": old["raw_source_ref"],
                "source_sha256": old["source_sha256"], "retrieved_at": old["retrieved_at"],
                "service_scope": old["service_scope"],
            }
    for row in records.values():
        row["service_scope"] = sorted(set(row["service_scope"]))
    return list(records.values()), {
        "global_marketing_declared_regions": 34, "global_marketing_declared_azs": 103,
        "aggregate_source": evidence("huawei-global"), "unmapped_selector_labels": missing_labels,
        "availability_zones_generated": 0,
        "enrichment_sources": [evidence(k, source_scope="provider_declared") for k in [
            "huawei-identity-policy", "huawei-iam-global", "huawei-rfs", "huawei-cloud-connect", "huawei-trust", "huawei-global"]],
        "scope_note": "Union of itemized product-region memberships; not universal product support or a physical data-center directory.",
    }


def parse_azure_china():
    rows = []
    table = table_with("azure-china", "Programmatic name")[0]
    for tr in table.find_all("tr")[1:]:
        data = cells(tr)
        if len(data) != 6:
            raise ValueError("Malformed Azure China row")
        name, _, pair, place, geography, identifier = data
        az_support = any(img.get("alt") == "Yes" for img in tr.find_all("img"))
        rows.append(location("azure-china", "azurechina", "cloud_region", identifier,
            name.rstrip("*"), "Microsoft Azure operated by 21Vianet", "azure_china",
            source_record_id=identifier, country_code="CN", status="operational",
            access="restricted" if "*" in name else "public", scope=["azure_china"], properties={
                "partition": "AzureChinaCloud", "operator": "Shanghai Blue Cloud Technology Co., Ltd. (21Vianet)",
                "operator_evidence": evidence("azure-china-operator"), "brand": "Microsoft Azure",
                "paired_region_id": pair, "geography": geography, "source_physical_location": place,
                "availability_zone_support": az_support, "synthetic_availability_zones_generated": False,
            }))
    return rows, {"availability_zone_records_generated": 0, "partition": "AzureChinaCloud"}


QINIU_PLACES = {
    "青岛": ("Qingdao", "CN"), "北京": ("Beijing", "CN"), "张家口": ("Zhangjiakou", "CN"),
    "呼和浩特": ("Hohhot", "CN"), "乌兰察布": ("Ulanqab", "CN"), "杭州": ("Hangzhou", "CN"),
    "上海": ("Shanghai", "CN"), "深圳": ("Shenzhen", "CN"), "广州": ("Guangzhou", "CN"),
    "成都": ("Chengdu", "CN"), "香港": ("Hong Kong", "HK"), "新加坡": ("Singapore", "SG"),
    "吉隆坡": ("Kuala Lumpur", "MY"), "雅加达": ("Jakarta", "ID"), "东京": ("Tokyo", "JP"),
    "迪拜": ("Dubai", "AE"), "弗吉尼亚": ("Virginia", "US"), "硅谷": ("Silicon Valley", "US"),
    "法兰克福": ("Frankfurt", "DE"),
}


def parse_qiniu():
    rows, gaps = [], []
    tables = table_with("qiniu-resource-pools", "Region ID")
    for pool, table in zip(["1", "3"], tables, strict=True):
        parent = location("qiniu-resource-pools", "qiniu", "cloud_resource_pool", "pool-" + pool,
            "QVM resource pool " + pool, "Qiniu Cloud", "qiniu_qvm", source_record_id=pool,
            scope=["qvm"], status="operational", properties={"pool_id": pool, "pool_isolation_explicit": True})
        rows.append(parent)
        parent["jurisdiction_scope"] = "global" if pool == "1" else "mainland_china"
        for tr in table.find_all("tr")[1:]:
            data = cells(tr)
            tokens = re.findall(r"\b(?:cn|ap|me|us|eu|grand)-[a-z0-9-]+\b", " ".join(data))
            if len(tokens) != 1:
                gaps.append({"pool_id": pool, "source_cells": data, "reason": "no provider region ID in row"})
                continue
            identifier = tokens[0]
            # A merged Ulanqab cell contains both label and ID. Preserve that
            # explicit ID without assigning adjacent-row labels to Tokyo.
            label = clean(data[-1].replace(identifier, "")) if identifier != data[-1] else data[-2] if len(data) >= 2 else ""
            city, country = None, None
            for token, place in QINIU_PLACES.items():
                if token in label:
                    city, country = place
                    break
            props = {"pool_id": pool, "provider_region_id": identifier,
                     "underlying_host_not_inferred_from_region_id": True,
                     "source_cells": data, "product_scope": "QVM"}
            if country is None:
                props["source_label_alignment_unresolved"] = True
                gaps.append({"pool_id": pool, "region_id": identifier, "source_cells": data,
                             "reason": "region token is explicit but no geographic label on its row"})
            rows.append(location("qiniu-resource-pools", "qiniu", "cloud_region", f"pool-{pool}-{identifier}",
                label if city else f"QVM pool {pool}: {identifier}", "Qiniu Cloud", "qiniu_qvm",
                source_record_id=identifier, parent=parent["record_id"], country_code=country, city=city,
                scope=["qvm"], status="operational", properties=props))
    return rows, {"source_alignment_gaps": gaps, "availability_zones_generated": 0}


def refresh_existing_china(key):
    import update_china as legacy
    mapped = {"baidu": "baidu-bcc", "volcano": "volcano-directory", "tianyi": "tianyi-vpc", "kingsoft": "kingsoft-kec", "jd": "jd-cvm"}[key]
    info = source(mapped)
    original = dict(legacy.SOURCES[key])
    legacy.SOURCES[key].update(url=info["source_url"], path=info["path"], published=info.get("source_published_at"))
    try:
        rows, report = getattr(legacy, "parse_" + key)(DATE)
    finally:
        legacy.SOURCES[key] = original
    for row in rows:
        row["schema_version"] = "1.2.0"
        row["properties"]["source_updated_at"] = info.get("source_updated_at")
    return rows, report


def parse_jd_current():
    import update_china as legacy
    html = source_bytes("jd-cvm").decode()
    candidates = []
    for match in re.finditer(r'(?:\b[A-Za-z_$][A-Za-z0-9_$]*\.content=|\bcontent:)("(?:\\.|[^"\\])*")', html):
        if "cn-north-1a" not in match.group(1):
            continue
        content = json.loads(match.group(1))
        if "cn-north-1a" in content and "|" in content:
            candidates.append(content)
    if len(candidates) != 1:
        raise ValueError(f"Expected one JD region document, got {len(candidates)}")
    grouped = {}
    for line in candidates[0].splitlines():
        if not line.startswith("|"):
            continue
        data = [s.strip() for s in line.strip("|").split("|")]
        region = re.search(r"\bcn-(?:north|east|south)-\d+\b", line)
        zone = re.search(r"\bcn-(?:north|east|south)-\d+[a-z]\b", line)
        if region and zone:
            grouped.setdefault(region.group(), {"city_cn": data[-1], "zones": [], "label": next(c for c in data if region.group() in c)})["zones"].append(zone.group())
    rows = []
    for identifier, info in sorted(grouped.items()):
        city = legacy.CITY_NAMES[info["city_cn"]]
        parent = location("jd-cvm", "jd", "cloud_region", identifier, info["label"], "JD Cloud", "jd_cloud",
            source_record_id=identifier, country_code="CN", city=city, scope=["compute"], status="operational",
            properties={"source_city_name": info["city_cn"], "declared_zone_count": len(set(info["zones"]))})
        rows.append(parent)
        for zone in sorted(set(info["zones"])):
            rows.append(location("jd-cvm", "jd", "availability_zone", zone, zone, "JD Cloud", "jd_cloud",
                source_record_id=zone, country_code="CN", city=city, parent=parent["record_id"], scope=["compute"], status="operational",
                properties={"parent_region_id": identifier}))
    return rows, {"parser_surface": "Literal Markdown from Nuxt content assignment; variable names are not stable", "console_availability_warning": True}


def parse_volcano_current():
    key = "volcano-directory"
    result = json.loads(source_bytes(key))["Result"]
    markdown = result["MDContent"].replace("\\-", "-")
    rows, discrepancies = [], []
    places = {"cn-beijing": ("Beijing", "CN"), "cn-shanghai": ("Shanghai", "CN"),
              "cn-guangzhou": ("Guangzhou", "CN"), "cn-hongkong": ("Hong Kong", "HK"),
              "ap-southeast-1": ("Johor", "MY"), "ap-southeast-3": ("Jakarta", "ID")}
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        data = [clean(c) for c in line.strip().strip("|").split("|")]
        if len(data) != 6 or not re.fullmatch(r"(?:cn|ap)-[a-z0-9-]+", data[3]):
            continue
        label, source_city, declared, identifier, zone_text, state = data
        if identifier not in places:
            raise ValueError(f"Unreviewed Volcano region geography: {identifier}")
        city, country = places[identifier]
        zones = sorted(set(re.findall(r"\b" + re.escape(identifier) + r"(?:-[a-z]|[a-z])\b", zone_text)))
        if not zones:
            raise ValueError(f"No explicit zones for Volcano {identifier}")
        if int(declared) != len(zones):
            discrepancies.append({"region_id": identifier, "declared_zone_count": int(declared), "explicit_zone_id_count": len(zones)})
        parent = location(key, "volcano", "cloud_region", identifier, label + (" " + source_city if source_city else ""),
            "Volcano Engine", "volcano_cloud", country_code=country, city=city, source_record_id=identifier,
            status="operational" if state == "商用" else "unknown", scope=["auto_scaling"], properties={
                "declared_zone_count": int(declared), "explicit_zone_id_count": len(zones),
                "source_publication_status": state, "source_document_id": result["DocumentID"],
                "source_city_label": source_city, "universal_product_availability_not_asserted": True})
        rows.append(parent)
        for zone in zones:
            rows.append(location(key, "volcano", "availability_zone", zone, zone, "Volcano Engine", "volcano_cloud",
                country_code=country, city=city, source_record_id=zone, parent=parent["record_id"],
                status=parent["lifecycle_status"], scope=["auto_scaling"], properties={"parent_region_id": identifier}))
    return rows, {"source_count_discrepancies": discrepancies,
                  "parser_surface": "Published MDContent in official document API; both cn- and ap- region namespaces retained",
                  "first_published_at": result["FirstPublishedTime"], "source_document_updated_at": result["UpdatedTime"]}


def enrich_aws_china():
    previous = json.loads((REPO_ROOT / "data/aws/regions-and-zones.20260805.geojson").read_text())["features"]
    text = soup("aws-china").get_text(" ", strip=True)
    names = {
        "cn-north-1": "Beijing Sinnet Technology Co., Ltd. (Sinnet)",
        "cn-northwest-1": "Ningxia Western Cloud Data Technology Co., Ltd. (NWCD)",
    }
    for token in ["Beijing Sinnet Technology", "Ningxia Western Cloud Data Technology"]:
        if token not in text:
            raise ValueError(f"AWS China operator source missing {token}")
    rows = []
    for feature in previous:
        row = copy.deepcopy(feature["properties"])
        row.update(latitude=None, longitude=None)
        if row["source_record_id"] in names and row["entity_type"] == "cloud_region":
            row["properties"].update(operator=names[row["source_record_id"]],
                operator_evidence=evidence("aws-china"), operator_role="china_region_service_operator",
                physical_facility_ownership_not_asserted=True,
                stable_availability_zone_ids_not_established_by_operator_page=True)
        rows.append(row)
    return rows, {"enrichment_sources": [evidence("aws-china", source_scope="provider_declared")],
                  "scope_note": "August hierarchy retained; October operator evidence joins only the two China-region rows. Other rows are not freshly retrieved."}


def legacy_reconciliation(root):
    entries = []
    specs = [
        ("alibaba", "data/alibaba_cloud_data_centers_2.geojson", "legacy_unreconciled"),
        ("tencent", "data/tencent_cloud_data_centers.geojson", "legacy_unreconciled"),
        ("alibaba", "data/quarantine/alibaba_cloud_data_centers_3.geojson", "quarantined"),
        ("baidu", "data/quarantine/baidu_cloud_data_centers_2.geojson", "quarantined"),
    ]
    for vendor, path, role in specs:
        current = json.loads((root / f"data/{vendor}/regions-and-zones.{TAG}.geojson").read_text())["features"]
        index = {f["properties"]["source_record_id"]: f["properties"] for f in current}
        labels = {}
        for f in current:
            p = f["properties"]
            if p["entity_type"] == "cloud_region":
                labels.setdefault(p["name"], []).append(p["record_id"])
        rows = []
        for ordinal, feature in enumerate(json.loads((REPO_ROOT / path).read_text())["features"], 1):
            p = feature["properties"]
            identifier = p.get("region_id")
            if vendor == "tencent" and p.get("region") and p.get("availability_zone"):
                identifier = str(p["region"]) + "-" + str(p["availability_zone"])
            targets = [index[identifier]["record_id"]] if identifier in index else labels.get(p.get("region"), [])
            rows.append({"legacy_row_for_audit_only": ordinal, "legacy_label": p.get("name") or p.get("zone_name"),
                         "legacy_claimed_region": p.get("region"), "provider_id_candidate": identifier,
                         "candidate_current_record_ids": targets,
                         "match_state": "candidate_id_or_exact_label_match" if targets else "no_explicit_current_identity_match",
                         "geometry_and_capacity_not_inherited": True, "canonical_alias_not_automatically_created": True,
                         "quarantine_exclusion_retained": role == "quarantined"})
        entries.append({"path": path, "sha256": sha256(REPO_ROOT / path), "role": role, "records": rows,
                        "candidate_match_count": sum(bool(r["candidate_current_record_ids"]) for r in rows)})
    write_json(root / f"data/china/legacy-reconciliation.{TAG}.json", {
        "retrieved_at": DATE, "inputs": entries, "canonical_records_generated": 0,
        "scope_note": "Candidate identity matches do not grant provenance to historical geometry, speculative capacity, or unsupported entities. Quarantined inputs remain excluded; aliases require separate review."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.output_root
    summaries = {}
    specs = [
        ("alibaba", "regions-and-zones", "alibaba-directory", lambda: parse_cloud_directory("alibaba")),
        ("tencent", "regions-and-zones", "tencent-directory", lambda: parse_cloud_directory("tencent")),
        ("huawei", "regions", "huawei-identity-policy", parse_huawei),
        ("microsoft", "china-cloud-regions", "azure-china", parse_azure_china),
        ("qiniu", "resource-pools-and-regions", "qiniu-resource-pools", parse_qiniu),
        ("aws", "regions-and-zones", "aws-china", enrich_aws_china),
    ]
    for key in ["baidu", "volcano", "tianyi", "kingsoft", "jd"]:
        layer = "vpc-resource-pools" if key == "tianyi" else "mainland-regions-and-zones" if key in {"kingsoft", "jd"} else "regions-and-zones"
        source_key = {"baidu": "baidu-bcc", "volcano": "volcano-directory", "tianyi": "tianyi-vpc", "kingsoft": "kingsoft-kec", "jd": "jd-cvm"}[key]
        parse = parse_jd_current if key == "jd" else parse_volcano_current if key == "volcano" else lambda key=key: refresh_existing_china(key)
        specs.append((key, layer, source_key, parse))
    for provider, layer, source_key, parse in specs:
        rows, extra = parse()
        if not rows:
            raise ValueError(f"No rows parsed for {provider}")
        info = source(source_key)
        report = write_layer(records=rows, output_dir=root / "data" / provider, layer_name=layer,
            retrieved_at=DATE, source_url=info["source_url"], raw_path=REPO_ROOT / info["path"],
            parser_name=f"update_china_enrichment.py:{provider}", schema_version="1.2.0", extra_report=extra)
        summaries[f"{provider}/{layer}"] = {"record_count": len(rows), "entity_types": dict(Counter(r["entity_type"] for r in rows))}
        if provider in {"alibaba", "tencent", "baidu", "volcano", "huawei"}:
            mainland = [r for r in rows if r["jurisdiction_scope"] == "mainland_china"]
            general = [r for r in mainland if not set(r["service_scope"]) & {"financial_cloud", "government_cloud", "automotive_cloud"}]
            name = "mainland-regions" if provider == "huawei" else "mainland-regions-and-zones"
            write_layer(records=general, output_dir=root / "data" / provider, layer_name=name,
                retrieved_at=DATE, source_url=info["source_url"], raw_path=REPO_ROOT / info["path"],
                parser_name=f"update_china_enrichment.py:{provider}:mainland", schema_version="1.2.0",
                extra_report={"view_of": f"{provider}/{layer}", "jurisdiction_filter": "mainland_china"})
            if provider in {"alibaba", "tencent"}:
                specialized = [r for r in mainland if r not in general]
                write_layer(records=specialized, output_dir=root / "data" / provider,
                    layer_name="mainland-specialized-regions-and-zones", retrieved_at=DATE,
                    source_url=info["source_url"], raw_path=REPO_ROOT / info["path"],
                    parser_name=f"update_china_enrichment.py:{provider}:specialized", schema_version="1.2.0",
                    extra_report={"view_of": f"{provider}/{layer}", "jurisdiction_filter": "mainland_china", "access_scope": "specialized"})
    write_json(root / f"data/china/cloud-enrichment.{TAG}.report.json", {
        "retrieved_at": DATE, "layers": summaries, "source_catalog": {"path": repo_ref(CATALOG), "sha256": sha256(CATALOG)},
        "geometry_note": "No coordinates were supplied by these directory sources; all refreshed geometry is null.",
    })
    legacy_reconciliation(root)
    print(json.dumps(summaries, sort_keys=True))


if __name__ == "__main__":
    main()
