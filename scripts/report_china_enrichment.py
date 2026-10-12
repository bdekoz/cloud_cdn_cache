#!/usr/bin/env python3
"""Record the approved China implementation without changing its baseline audit."""

import argparse
import json
from collections import Counter
from pathlib import Path

from china_enrichment_common import CATALOG, DATE, TAG
from location_common import REPO_ROOT, sha256, write_json


def build(root):
    cloud = json.loads((root / f"data/china/cloud-enrichment.{TAG}.report.json").read_text())
    paths = [f"data/{name}.{TAG}.geojson" for name in cloud["layers"]]
    paths += [f"data/chindata/data-centers.{TAG}.geojson"]
    paths += [f"data/infrastructure/{name}.{TAG}.json" for name in (
        "china-ai-services", "china-facilities-and-portfolios", "china-carrier-links")]
    paths += [f"data/network/china-vendor-evidence.{TAG}.json", f"data/vendors/registry.{TAG}.json"]
    outputs, source_refs = [], set()
    for path in paths:
        document = json.loads((root / path).read_text())
        rows = [f["properties"] for f in document["features"]] if "features" in document else document["records"]
        field = "entity_type" if "features" in document else "evidence_type" if "network/" in path else "category"
        source_refs.update(row["raw_source_ref"] for row in rows)
        outputs.append({"path": path, "sha256": sha256(root / path), "record_count": len(rows),
                        "record_types": dict(sorted(Counter(row[field] for row in rows).items()))})
    catalog = json.loads(CATALOG.read_text())
    reconciliation = f"data/china/legacy-reconciliation.{TAG}.json"
    legacy = json.loads((root / reconciliation).read_text())
    output_counts = {o["path"]: o["record_count"] for o in outputs}
    chinese_cloud_count = sum(cloud["layers"][f"{v}/{layer}"]["record_count"] for v, layer in (
        ("alibaba", "regions-and-zones"), ("tencent", "regions-and-zones"), ("huawei", "regions"),
        ("baidu", "regions-and-zones"), ("volcano", "regions-and-zones"),
        ("kingsoft", "mainland-regions-and-zones"), ("jd", "mainland-regions-and-zones"),
        ("tianyi", "vpc-resource-pools")))
    baseline = json.loads((REPO_ROOT / f"data/china/vendor-coverage-assessment.{TAG}.json").read_text())
    # Baseline audit records are immutable; implementation totals come from outputs.
    baseline_cloud_count = sum(d["record_count"] for d in baseline["datasets"]
                               if d["role"] == "canonical_layer" and d["path"].split("/")[1] in {
                                   "alibaba", "tencent", "huawei", "baidu", "volcano", "kingsoft", "jd", "tianyi"})
    return {
        "retrieved_at": DATE,
        "baseline_audit": f"data/china/vendor-coverage-assessment.{TAG}.json",
        "baseline_audit_preserved": True,
        "approved_plan": f"data/china/enrichment-plan.{TAG}.json",
        "source_catalog": {"path": "data/raw/china-enrichment/" + CATALOG.name,
                           "sha256": sha256(CATALOG), "source_count": len(catalog["sources"]),
                           "capture_methods": dict(sorted(Counter(s["capture_method"] for s in catalog["sources"]).items()))},
        "outputs": outputs,
        "coverage_units": {
            "refreshed_chinese_cloud_vendor_records": chinese_cloud_count,
            "qiniu_product_records": cloud["layers"]["qiniu/resource-pools-and-regions"]["record_count"],
            "azure_china_regions": cloud["layers"]["microsoft/china-cloud-regions"]["record_count"],
            "new_location_records_net": chinese_cloud_count - baseline_cloud_count + cloud["layers"]["qiniu/resource-pools-and-regions"]["record_count"] + cloud["layers"]["microsoft/china-cloud-regions"]["record_count"],
            "ai_service_assertions": output_counts[f"data/infrastructure/china-ai-services.{TAG}.json"],
            "facility_and_portfolio_assertions": output_counts[f"data/infrastructure/china-facilities-and-portfolios.{TAG}.json"],
            "carrier_assertions": output_counts[f"data/infrastructure/china-carrier-links.{TAG}.json"],
            "network_assertions": output_counts[f"data/network/china-vendor-evidence.{TAG}.json"],
            "vendor_and_brand_references": output_counts[f"data/vendors/registry.{TAG}.json"],
            "units_are_separate_not_equivalent_physical_assets": True,
        },
        "implemented_tracks": [
            "Public-cloud directory refresh, global Huawei product-region union, Azure China and Qiniu",
            "Legacy/quarantine candidate identity reconciliation with no coordinate or capacity inheritance",
            "Vendor/operator/model-brand registry and explicit AI access, storage, execution and model-listing scopes",
            "Government final facility recognition list and dated/undated portfolio evidence",
            "Named carrier cables, landing stations, backhaul and emerging WAN service declarations",
            "Bounded public DNS/TLS/HEAD observations, sampled routing and APNIC/PeeringDB context",
        ],
        "legacy_reconciliation": {"path": reconciliation, "sha256": sha256(root / reconciliation),
                                  "canonical_records_generated": 0,
                                  "input_rows": sum(len(i["records"]) for i in legacy["inputs"]),
                                  "candidate_matched_rows": sum(i["candidate_match_count"] for i in legacy["inputs"])},
        "remaining_gaps": [
            "No consolidated public ECS region/AZ inventory for China Mobile or China Unicom; Unicom AI pools are product-scoped.",
            "Huawei product-region union is not universal availability or an AZ directory; Qianfan geography remains unresolved.",
            "Alibaba Johor marketing/list discrepancy, Volcano declared/listed AZ discrepancies and Qiniu Tokyo row alignment remain explicit.",
            "Tencent Shanghai financial AZ 1 is not listed in the captured current directory; retained August evidence does not prove closure.",
            "No defensible facility coordinates, installed GPUs, regional GPU stock, or model-specific execution sites from these sources.",
            "Seedance2.ai legal entity, jurisdiction and upstream hosting remain unresolved; direct current terms capture unavailable.",
            "VNET Q2 facts are indexed first-party evidence with a direct HTTP 403 gap; undated GDS/edge portfolios are not current site lists.",
            "MIIT recognition entries and Chindata codes still require facility/campus/operator alias and current-lifecycle resolution.",
            "API frontend observations and sampled network registrations do not establish inference hosting or exhaustive global availability.",
            "Carrier routes are not surveyed alignments; dated landing/design/commissioning claims require later lifecycle evidence.",
        ],
        "source_use_note": "The catalog includes corroborating and contextual sources plus explicitly marked unused document shells. Output primary references alone do not enumerate nested supporting evidence.",
        "primary_output_raw_source_count": len(source_refs),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    path = args.output_root / f"data/china/enrichment-implementation.{TAG}.json"
    report = build(args.output_root)
    write_json(path, report)
    print(json.dumps(report["coverage_units"], sort_keys=True))


if __name__ == "__main__":
    main()
