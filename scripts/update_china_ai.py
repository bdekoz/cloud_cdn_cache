#!/usr/bin/env python3
"""Serialize vendors, AI service coverage and scoped model-serving declarations."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from china_enrichment_common import (
    DATE, TAG, CATALOG, cells, clean, evidence, infra, labelled_id, script_json,
    source, source_bytes, soup, walk,
)
from location_common import REPO_ROOT, repo_ref, sha256, slug, write_json
from update_infrastructure import validate_collection


VENDOR_SOURCES = {
    "alibaba": "alibaba-directory", "tencent": "tencent-directory", "huawei": "huawei-global",
    "baidu": "baidu-bcc", "volcano": "seedance-official", "tianyi": "tianyi-vpc",
    "china-mobile": "miit-green-facilities-directory", "china-unicom": "unicom-ai-pools",
    "kingsoft": "kingsoft-kec", "jd": "jd-cvm", "bilibili": "bilibili-2025-report",
    "deepseek": "deepseek-identity", "moonshot": "kimi-endpoints", "fal": "fal-identity",
    "seedance2ai": "seedance2ai-identity", "byteplus": "byteplus-modelark",
    "ucloud": "ucloud-baremetal-md", "qiniu": "qiniu-resource-pools", "siliconflow": "siliconflow",
    "minimax": "minimax", "zai": "zai", "kuaishou": "kling", "gds": "gds-directory",
    "vnet": "vnet-q2", "chindata": "chindata-directory", "wangsu": "wangsu-cdn",
    "baishan": "baishan-edge", "dataport": "miit-green-facilities-directory",
    "runze": "miit-green-facilities-directory", "heying": "miit-green-facilities-directory",
    "meiliyun": "miit-green-facilities-directory",
}
BRANDS = {
    "qwen": ("Qwen", "alibaba-model-studio", "alibaba", "offered_by"),
    "hy": ("Tencent Hy / Hunyuan", "tencent-hy3", "tencent", "developed_by"),
    "seedance": ("Seedance", "seedance-official", "volcano", "developed_by"),
    "deepseek": ("DeepSeek", "deepseek-api", "deepseek", "offered_by"),
    "kimi": ("Kimi", "kimi-endpoints", "moonshot", "offered_by"),
    "glm": ("GLM", "zai", "zai", "offered_by"),
    "minimax": ("MiniMax", "minimax", "minimax", "offered_by"),
    "step": ("Step", "siliconflow", None, None),
    "kling": ("Kling AI", "kling", "kuaishou", "developed_by"),
}
CATEGORIES = {
    "vendor_identity": "An evidence-backed vendor/brand reference or unresolved named-operator candidate; not a physical infrastructure location.",
    "ai_service_region": "A named product region or model service pool, with access/storage and inference execution semantics kept distinct.",
    "ai_api_endpoint": "A documented API ingress URL, domain or workspace template; its location is not an inference facility.",
    "model_service_listing": "A provider's explicit model or model-family service listing, potentially scoped to a named pool; not GPU capacity or developer ownership.",
    "cloud_product_region": "A named cloud-product region with source labels and product availability; no manufactured provider region/AZ codes.",
    "ai_service_platform": "A provider-declared model/agent/inference platform with product scope and availability caveats; not a deployment region or physical facility.",
    "gpu_product_catalog": "Itemized GPU instance-family declarations; catalog membership does not establish installed GPU count or regional purchase availability.",
}


def vendor_id(key):
    return f"vendor:identity:{key}"


def brand_id(key):
    return f"vendor:brand:{key}"


def relation(kind, target):
    return {"relationship_type": kind, "target_record_id": target}


def registry():
    plan = json.loads((REPO_ROOT / f"data/china/enrichment-plan.{TAG}.json").read_text())
    rows = []
    for entry in plan["vendors"]:
        key = entry["vendor_id"]
        source_key = VENDOR_SOURCES[key]
        candidate = entry["vendor_class"] == "physical_facility_operator_candidate"
        props = {
            "vendor_id": key, "vendor_class": entry["vendor_class"],
            "identity_state": "named_operator_candidate" if candidate else "vendor_or_platform_reference",
            "resolved_legal_entity": None, "infrastructure_geography_not_established_by_identity": True,
            "cohort_classification": "global_inference_platform" if key == "fal" else "jurisdiction_unresolved" if key == "seedance2ai" else "china_related_vendor_or_offering",
            "source_capture_method": source(source_key)["capture_method"],
            "review_priority": entry["priority"], "unresolved": [],
        }
        countries = []
        if key == "fal":
            if "San Francisco" not in soup(source_key).get_text(" ", strip=True):
                raise ValueError("fal headquarters declaration missing")
            props.update(declared_headquarters="San Francisco", declared_headquarters_country="US")
            countries = ["US"]
        if key == "deepseek":
            entity = "Hangzhou DeepSeek Artificial Intelligence Co., Ltd."
            if entity not in soup(source_key).get_text(" ", strip=True):
                raise ValueError("DeepSeek controller identity missing")
            props.update(resolved_legal_entity=entity, identity_role="linked_service_data_controller")
        if key == "seedance2ai":
            props.update(bytedance_affiliation="explicitly_disclaimed_in_indexed_terms",
                         upstream_service_and_corporate_jurisdiction="not_verified",
                         current_direct_page_capture_available=False)
            props["unresolved"] = ["legal entity", "corporate jurisdiction", "upstream model provenance", "hosting geography"]
        if key == "tencent":
            props.update(model_brand_names=["Tencent Hy", "Hunyuan"], brand_update_evidence=evidence("tencent-hy3"))
        if key == "vnet":
            props["azure_operator_legal_entity_must_remain_separate"] = True
        if candidate:
            props["unresolved"] = ["legal/operator identity", "facility/campus aliases", "ownership", "current lifecycle"]
        row = infra(source_key, "vendor", "vendor_identity", key, entry["name"], entry["name"],
            "named_operator_candidate" if candidate else "vendor_reference", country_codes=countries,
            country_scope="declared_headquarters_only_not_infrastructure_location" if countries else "vendor_identity_only",
            source_scope="institution_declared" if source_key == "miit-green-facilities-directory" else "provider_declared",
            confidence="medium" if candidate or key == "seedance2ai" else "high", properties=props)
        row["record_id"] = vendor_id(key)
        rows.append(row)
    for key, name, source_key, role in [
        ("aws", "Amazon Web Services", "aws-china", "cloud_brand"),
        ("azure", "Microsoft Azure", "azure-china", "cloud_brand"),
        ("sinnet", "Beijing Sinnet Technology Co., Ltd. (Sinnet)", "aws-china", "china_region_operator"),
        ("nwcd", "Ningxia Western Cloud Data Technology Co., Ltd. (NWCD)", "aws-china", "china_region_operator"),
        ("azure21vianet", "Shanghai Blue Cloud Technology Co., Ltd. (21Vianet)", "azure-china-operator", "china_cloud_operator"),
        ("ctg", "China Telecom Global", "telecom-portfolio", "international_carrier"),
        ("sunevision", "SUNeVision / 新意网", "telecom-hkis1", "named_landing_station_and_colocation_operator"),
    ]:
        row = infra(source_key, "vendor", "vendor_identity", key, name, name, "vendor_reference",
            country_scope="operator_or_brand_identity_not_facility_geography", properties={
                "vendor_id": key, "identity_role": role, "resolved_legal_entity": name if "operator" in role else None,
                "infrastructure_geography_not_established_by_identity": True})
        row["record_id"] = vendor_id(key)
        rows.append(row)
    for key, (name, source_key, vendor, kind) in BRANDS.items():
        row = infra(source_key, "vendor", "vendor_identity", key, name, name, "model_brand_reference",
            country_scope="model_brand_not_hosting_location", relationships=[relation(kind, vendor_id(vendor))] if vendor else [],
            properties={"brand_id": key, "legal_entity_not_assumed_from_brand": True,
                        "developer_or_operator_unresolved": vendor is None})
        row["record_id"] = brand_id(key)
        rows.append(row)
    return rows


def model_studio():
    key = "alibaba-model-studio"
    tables = soup(key).find_all("table")
    table = next(t for t in tables if "Workspace-dedicated domain" in cells(t.find("tr")) and "Region ID" in cells(t.find("tr")))
    features = next(t for t in tables if cells(t.find("tr"))[0] == "Feature")
    feature_rows = [cells(r) for r in features.find_all("tr")]
    feature_map = {name: {r[0]: r[i] for r in feature_rows[1:]} for i, name in enumerate(feature_rows[0][1:], 1)}
    scope_map = {"cn-beijing": ["Chinese mainland"], "ap-southeast-1": ["International"],
                 "eu-central-1": ["Global", "EU"], "ap-northeast-1": ["Global", "Japan"],
                 "cn-hongkong": ["Global", "Hong Kong"], "us-east-1": ["Global", "US"]}
    countries = {"cn-beijing": "CN", "ap-southeast-1": "SG", "eu-central-1": "DE",
                 "ap-northeast-1": "JP", "cn-hongkong": "HK", "us-east-1": "US"}
    rows = []
    for tr in table.find_all("tr")[1:]:
        data = cells(tr)
        name, region_id = data[:2]
        region = infra(key, "alibaba", "ai_service_region", "model-studio-" + region_id, "Model Studio " + name,
            "Alibaba Cloud", "product_region", country_codes=[countries[region_id]],
            country_scope="declared_access_and_static_storage_region_not_exclusive_inference_execution", status="operational",
            relationships=[relation("offered_by", vendor_id("alibaba")), relation("access_cloud_region", f"alibaba:cloud_region:{region_id}")],
            properties={"service": "model_studio", "provider_region_id": region_id,
                        "inference_execution_scope_options": scope_map[region_id],
                        "access_and_storage_region_distinct_from_inference_scope": True,
                        "feature_support": feature_map[name], "api_keys_and_model_catalog_region_scoped": True,
                        "complete_model_catalog_not_asserted": True})
        rows.append(region)
        for role, value in zip(["workspace_dedicated", "dashscope", "trial"], data[2:5], strict=True):
            if "aliyuncs.com" not in value:
                continue
            rows.append(infra(key, "alibaba", "ai_api_endpoint", f"model-studio-{region_id}-{role}", value,
                "Alibaba Cloud", "endpoint_template" if "{" in value else "api_domain",
                country_scope="api_access_region_not_compute_location", status="operational",
                relationships=[relation("accesses_service_region", region["record_id"])], properties={
                    "domain": value, "endpoint_role": role, "is_template": "{" in value,
                    "execution_geography_not_established_by_hostname": True}))
    return rows


def byteplus():
    key = "byteplus-modelark"
    obj = script_json(key, "window._ROUTER_DATA")
    document = next(x for x in walk(obj) if isinstance(x, dict) and x.get("Title") == "Region availability" and isinstance(x.get("Content"), str))
    content = json.loads(document["Content"])
    inserts = [x["insert"] for x in walk(content) if isinstance(x, dict) and isinstance(x.get("insert"), str) and x["insert"] != "*"]
    text = "".join(inserts)
    if "some requests may be routed" not in text:
        raise ValueError("ModelArk routing caveat missing")
    rows = []
    for region_id, name, country, url in [
        ("ap-southeast-1", "Johor", "MY", "https://ark.ap-southeast.bytepluses.com/api/v3"),
        ("eu-west-1", "Dublin", "IE", "https://ark.eu-west.bytepluses.com/api/v3"),
    ]:
        if not all(v in text for v in [region_id, name, url]):
            raise ValueError(f"ModelArk region not established: {region_id}")
        row = infra(key, "byteplus", "ai_service_region", "modelark-" + region_id, "ModelArk " + name,
            "BytePlus", "product_region", country_codes=[country], status="operational",
            country_scope="declared_primary_inference_region_cross_region_routing_possible",
            relationships=[relation("offered_by", vendor_id("byteplus"))], properties={
                "provider_region_id": region_id, "service": "modelark", "region_label": name,
                "cross_region_inference_routing_possible": True, "api_keys_and_endpoints_region_scoped": True,
                "underlying_data_center_not_established": True, "source_document_id": document["DocumentID"]})
        rows.append(row)
        rows.append(infra(key, "byteplus", "ai_api_endpoint", "modelark-" + region_id, url, "BytePlus", "api_base_url",
            status="operational", relationships=[relation("accesses_service_region", row["record_id"])],
            properties={"base_url": url, "execution_geography_not_established_by_hostname": True}))
    return rows


def unicom():
    key = "unicom-ai-pools"
    documents = {x["id"]: x for x in walk(script_json(key, "var totalList"))
                 if isinstance(x, dict) and "id" in x and "content" in x and "title" in x}
    matrix, api = documents["7023"], documents["4974"]
    table = BeautifulSoup(matrix["content"], "html.parser").find("table")
    data = [cells(r) for r in table.find_all("tr")]
    pools = data[0][1:]
    rows, pool_ids = [], {}
    for label in pools:
        identifier = labelled_id("aisp", label)
        row = infra(key, "cucloud", "ai_service_region", identifier, label, "China Unicom Cloud", "named_service_pool",
            country_codes=["CN"], country_scope="declared_named_service_pool_not_facility_coordinate", status="operational",
            relationships=[relation("offered_by", vendor_id("china-unicom"))], properties={
                "service": "AISP", "provider_pool_id": None, "source_pool_label": label,
                "identity_method": "source_label_hash", "source_document_id": matrix["id"],
                "source_document_title": matrix["title"], "current_stock_not_established": True})
        row["source_updated_at"] = matrix["updateDate"][:10]
        rows.append(row)
        pool_ids[label] = row["record_id"]
    category = None
    for data_row in data[1:]:
        if len(data_row) == 1:
            category = data_row[0]
            continue
        if len(data_row) != len(pools) + 1:
            raise ValueError(f"AISP support matrix width changed: {data_row}")
        model = data_row[0]
        for label, support in zip(pools, data_row[1:], strict=True):
            if not support:
                continue
            if "支持" not in support or "不支持" in support:
                raise ValueError(f"Unreviewed AISP availability label: {support}")
            row = infra(key, "cucloud", "model_service_listing", labelled_id("aisp-model", label + ":" + model),
                f"{model} at {label}", "China Unicom Cloud", "model_at_named_pool", country_codes=["CN"],
                country_scope="provider_named_service_pool_not_gpu_capacity", status="operational",
                relationships=[relation("listed_in_service_pool", pool_ids[label])], properties={
                    "model_id": model, "model_category_label": category, "source_support_label": support,
                    "source_pool_label": label, "source_document_id": matrix["id"],
                    "installed_compute_and_current_sale_stock_not_asserted": True})
            row["source_updated_at"] = matrix["updateDate"][:10]
            rows.append(row)
    api_table = BeautifulSoup(api["content"], "html.parser").find("table")
    for tr in api_table.find_all("tr")[1:]:
        label, value = cells(tr)
        if not value.startswith("https://"):
            continue
        url = value.replace(" ", "")
        relationships = [relation("offered_by", vendor_id("china-unicom"))]
        if label in pool_ids:
            relationships.append(relation("accesses_service_region", pool_ids[label]))
        row = infra(key, "cucloud", "ai_api_endpoint", labelled_id("aisp-endpoint", label), url,
            "China Unicom Cloud", "api_domain", relationships=relationships, status="operational",
            properties={"base_url": url, "source_pool_label": label, "source_document_id": api["id"],
                        "pool_label_alias_unresolved": label not in pool_ids,
                        "execution_geography_not_established_by_hostname": True})
        row["source_updated_at"] = api["updateDate"][:10]
        rows.append(row)
    return rows


def hunyuan():
    rows = []
    for table in soup("hunyuan-ingress").find_all("table"):
        if "域名" not in table.get_text(" "):
            continue
        for tr in table.find_all("tr")[1:]:
            data = cells(tr)
            if len(data) != 2 or not data[1].endswith("tencentcloudapi.com"):
                continue
            label, domain = data
            rows.append(infra("hunyuan-ingress", "tencent", "ai_api_endpoint", slug(domain), domain,
                "Tencent Cloud", "api_domain", relationships=[relation("offered_by", vendor_id("tencent"))],
                properties={"domain": domain, "source_ingress_region_label": label,
                            "endpoint_role": "regional_api_ingress", "execution_geography_not_established": True,
                            "api_gateway_region_does_not_establish_product_region": True}))
    text = soup("hunyuan-chat").get_text(" ", strip=True)
    domain = "hunyuan.ai.tencentcloudapi.com"
    if domain not in text:
        raise ValueError("Current Hunyuan chat endpoint missing")
    rows.append(infra("hunyuan-chat", "tencent", "ai_api_endpoint", slug(domain), domain, "Tencent Cloud", "api_domain",
        relationships=[relation("offered_by", vendor_id("tencent"))], properties={
            "domain": domain, "endpoint_role": "chat_interface", "execution_geography_not_established": True}))
    return rows


def direct_endpoints():
    specs = [
        ("deepseek-api", "deepseek", "direct", "https://api.deepseek.com", "open_platform"),
        ("kimi-endpoints", "moonshot", "china-open", "https://api.moonshot.cn/v1", "china_open_platform"),
        ("kimi-endpoints", "moonshot", "overseas-open", "https://api.moonshot.ai/v1", "overseas_open_platform"),
        ("kimi-endpoints", "moonshot", "china-coding", "https://api.kimi.com/coding/", "china_coding_membership"),
        ("kimi-endpoints", "moonshot", "overseas-coding", "https://api.kimi.ai/coding/", "overseas_coding_membership"),
        ("zai", "zai", "open-platform", "https://api.z.ai/api/paas/v4/", "open_platform"),
        ("siliconflow-quickstart", "siliconflow", "open-platform", "https://api.siliconflow.com/v1", "open_platform"),
        ("fal-queue", "fal", "queue", "https://queue.fal.run", "asynchronous_queue"),
        ("minimax-quickstart", "minimax", "openai-compatible", "https://api.minimax.io/v1", "openai_compatible"),
        ("minimax-quickstart", "minimax", "anthropic-compatible", "https://api.minimax.io/anthropic", "anthropic_compatible"),
    ]
    rows = []
    for key, vendor, identifier, url, role in specs:
        if url.rstrip("/") not in soup(key).get_text("", strip=True):
            raise ValueError(f"Endpoint absent from source: {url}")
        rows.append(infra(key, vendor, "ai_api_endpoint", identifier, url, vendor, "api_base_url",
            relationships=[relation("offered_by", vendor_id(vendor))], status="operational", properties={
                "base_url": url, "endpoint_role": role, "execution_and_storage_country_not_inferred_from_domain": True}))
    return rows


def model_listings():
    rows = []
    for key, vendor, brands in [("siliconflow", "siliconflow", ["deepseek", "qwen", "glm", "kimi", "step", "minimax"]),
                               ("fal-identity", "fal", ["seedance", "qwen", "kling", "minimax"])]:
        text = soup(key).get_text(" ", strip=True).lower()
        for brand in brands:
            label = BRANDS[brand][0]
            token = "kling" if brand == "kling" else "step" if brand == "step" else label.lower()
            if token not in text:
                raise ValueError(f"Model family {label} not listed by {vendor}")
            rows.append(infra(key, vendor, "model_service_listing", brand, f"{label} listed by {vendor}", vendor,
                "model_family_service_listing", relationships=[relation("listed_by", vendor_id(vendor)), relation("model_brand", brand_id(brand))],
                properties={"model_family": label, "hosting_arrangement_not_established": True,
                            "training_or_inference_facility_not_asserted": True}))
    return rows


def ucloud_product_regions():
    text = source_bytes("ucloud-baremetal-md").decode()
    places = {"北京2": "CN", "乌兰察布": "CN", "上海2": "CN", "广州": "CN", "泉州": "CN", "香港": "HK", "台北": "TW", "伦敦": "GB"}
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        data = [clean(x) for x in line.strip().strip("|").split("|")]
        if len(data) != 2 or data[0] in {"地域", "---"}:
            continue
        label, zones = data
        country = next((code for token, code in places.items() if token in label), None)
        if not country:
            raise ValueError(f"Unreviewed UCloud product geography: {label}")
        rows.append(infra("ucloud-baremetal-md", "ucloud", "cloud_product_region", labelled_id("uphost", label),
            label, "UCloud", "named_product_region", country_codes=[country],
            country_scope="product_directory_geography_not_facility_location", status="operational",
            relationships=[relation("offered_by", vendor_id("ucloud"))], properties={
                "product": "UPHost bare metal", "provider_region_id": None,
                "source_region_label": label, "source_zone_labels": zones,
                "gpu_zone_explicit": "GPU" in zones, "identity_method": "source_label_hash",
                "provider_zone_ids_not_manufactured": True}))
    if len(rows) != 8:
        raise ValueError(f"UPHost product directory yielded {len(rows)} regions rather than its eight listed rows")
    return rows


def service_platforms():
    rows = []
    for key, vendor, identifier, name, properties in [
        ("baidu-qianfan", "baidu", "qianfan", "Baidu Qianfan", {"product_scope": ["model_services", "agent_development"], "api_endpoint_inventory_not_established_by_landing_page": True}),
        ("siliconflow", "siliconflow", "siliconflow", "SiliconFlow model service", {"managed_and_byoc_modes": ["managed_model_apis", "byoc"], "customer_byoc_geography_not_inferred_from_platform_identity": True}),
        ("minimax", "minimax", "minimax", "MiniMax API platform", {"modalities_in_catalog": ["language", "speech", "video", "image", "music", "file_management"], "catalog_is_not_uniform_customer_availability": True, "subscription_and_payg_key_scopes_distinct": True}),
        ("tencent-hy3", "tencent", "tokenhub", "Tencent Cloud TokenHub", {"model_brand": "Tencent Hy (formerly Hunyuan)", "international_access_announcement_not_execution_region_inventory": True, "historical_trial_end_date": "2026-08-31"}),
    ]:
        text = soup(key).get_text("", strip=True)
        required = "千帆" if vendor == "baidu" else "BYOC" if vendor == "siliconflow" else "MiniMax" if vendor == "minimax" else "TokenHub"
        if required not in text:
            raise ValueError(f"Service platform not established by {key}")
        rows.append(infra(key, vendor, "ai_service_platform", identifier, name, name, "service_platform",
            relationships=[relation("offered_by", vendor_id(vendor))], properties={**properties, "deployment_and_physical_facility_geography_not_established": True}))
    return rows


def gpu_catalog():
    key = "alibaba-gpu-catalog"
    headings = [clean(h.get_text(" ", strip=True)) for h in soup(key).find_all(["h2", "h3"])]
    families = []
    for heading in headings:
        tokens = re.findall(r"\b(?:sgn|vgn|gn)[0-9][a-z0-9-]*\b", heading)
        if tokens:
            families.append({"source_heading": heading, "family_labels": tokens})
    if not families:
        raise ValueError("No explicit GPU family headings in corrected catalog")
    return [infra(key, "alibaba", "gpu_product_catalog", "ecs-gpu-families", "Alibaba ECS GPU instance families",
        "Alibaba Cloud", "product_catalog", relationships=[relation("offered_by", vendor_id("alibaba"))],
        properties={"itemized_family_headings": families, "instance_specifications_not_installed_capacity": True,
                    "regional_purchase_availability_not_established_by_catalog": True,
                    "virtual_gpu_slices_distinct_from_physical_gpu_cards": True})]


def collection(rows, categories, note):
    return {"type": "InfrastructureEvidenceCollection", "schema_version": "1.0.0", "retrieved_at": DATE,
            "scope_note": note, "categories": categories, "records": sorted(rows, key=lambda r: r["record_id"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.output_root
    entities = registry()
    vendor_collection = collection(entities, {"vendor_identity": CATEGORIES["vendor_identity"]},
        "Vendor, operator and model-brand references are metadata, not infrastructure locations. Country fields denote explicit identity/headquarters context only.")
    validate_collection(vendor_collection)
    write_json(root / f"data/vendors/registry.{TAG}.json", vendor_collection)
    rows = model_studio() + byteplus() + unicom() + hunyuan() + direct_endpoints() + model_listings() + ucloud_product_regions() + service_platforms() + gpu_catalog()
    value = collection(rows, {k: v for k, v in CATEGORIES.items() if k != "vendor_identity"},
        "Product regions, service pools, model listings and API ingress are distinct assertions. Endpoint audience, domain or headquarters does not locate inference compute. GPU stock and physical facility ownership are not asserted.")
    external = {r["record_id"] for r in entities}
    for path in (root / "data/alibaba").glob(f"regions-and-zones.{TAG}.geojson"):
        external |= {r["properties"]["record_id"] for r in json.loads(path.read_text())["features"]}
    validate_collection(value, external_record_ids=external)
    write_json(root / f"data/infrastructure/china-ai-services.{TAG}.json", value)
    report = {"record_count": len(rows), "category_counts": dict(Counter(r["category"] for r in rows)),
              "vendor_registry_record_count": len(entities), "vendor_registry_excluded_from_infrastructure_totals": True,
              "source_catalog": {"path": repo_ref(CATALOG), "sha256": sha256(CATALOG)},
              "relationships_resolved_against": [f"data/vendors/registry.{TAG}.json", f"data/alibaba/regions-and-zones.{TAG}.geojson"],
              "explicit_gaps": ["Unicom Hohhot matrix/endpoint pool label alias unresolved", "Unicom Shanghai endpoint requires a customer-manager contact in the general API directory", "UCloud provider region/AZ IDs not published in UPHost label directory"]}
    write_json(root / f"data/infrastructure/china-ai-services.{TAG}.report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
