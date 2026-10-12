#!/usr/bin/env python3
"""Normalize China facility recognitions and dated portfolio/network declarations."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from china_enrichment_common import DATE, TAG, clean, evidence, infra, labelled_id, location, source, soup
from location_common import REPO_ROOT, repo_ref, sha256, write_json, write_layer
from update_china_ai import relation, vendor_id
from update_infrastructure import validate_collection

CATEGORIES = {
    "recognized_compute_facility": "A named building/facility entry in a government recognition directory; not proof of current operation, ownership, exact location or independent site identity.",
    "provider_infrastructure_portfolio": "A provider/filing aggregate for capacity, facilities or suppliers with explicit units and an as-of date when supplied.",
    "edge_network_portfolio": "An aggregate edge-network coverage declaration; fleet or city totals do not establish individual POP identities.",
    "compute_energy_collaboration": "A named compute/energy collaboration and its proposed work areas, distinct from commissioned facilities or contracted grid capacity.",
}
ASSOCIATIONS = {
    "中国电信": "tianyi", "中国移动": "china-mobile", "中国联通": "china-unicom", "北京联通": "china-unicom",
    "阿里": "alibaba", "抖音": "volcano", "快手": "kuaishou", "数据港": "dataport",
    "润泽": "runze", "合盈": "heying", "美利云": "meiliyun",
}


def miit_recognitions():
    key = "miit-green-facilities-directory"
    info = source(key)
    text = subprocess.check_output(["pdftotext", "-layout", str(REPO_ROOT / info["path"]), "-"], text=True)
    entries, current = [], None
    for line in text.splitlines():
        match = re.match(r"^\s*(\d{1,2})\s+(\S.*)$", line)
        if match:
            current = {"source_row": int(match.group(1)), "name": clean(match.group(2))}
            entries.append(current)
        elif current and line.strip() and not re.match(r"^(?:序号|[一二三四五六]、|\d+$)", line.strip()):
            current["name"] += " " + clean(line)
    if [e["source_row"] for e in entries] != list(range(1, 61)):
        raise ValueError("Final MIIT directory did not yield contiguous 1-60 entries")
    if "征求意见稿" in text:
        raise ValueError("Consultation draft cannot replace final recognition list")
    rows = []
    for entry in entries:
        label = entry["name"]
        matches = sorted({vendor for token, vendor in ASSOCIATIONS.items() if token in label})
        rows.append(infra(key, "miit", "recognized_compute_facility", labelled_id("recognition-2025", label),
            label, "Named facility operator unresolved", "recognition_directory_entry",
            country_codes=["CN"], country_scope="national_mainland_china_designation_directory",
            source_scope="institution_declared", parties=[{"name": "MIIT and co-signing institutions", "role": "recognizing_institution"}],
            relationships=[relation("source_name_mentions_vendor", vendor_id(v)) for v in matches], properties={
                "recognition_year": 2025, "list_status": "final", "source_row": entry["source_row"],
                "source_facility_label": label, "identity_method": "recognition_year_and_source_label_hash",
                "named_vendor_candidates": matches, "ownership_and_operator_role_not_established_by_name": True,
                "current_operation_and_physical_coordinates_not_established": True,
                "buildings_campuses_and_combined_entries_not_split": True}))
    return rows


def portfolios():
    rows = []
    text = soup("gds-directory").get_text(" ", strip=True)
    operating = [int(m.group(1)) for m in re.finditer(r"(\d+)\s*座\s*[0-9,]+\s*平方米\s*运营中的数据中心", text)]
    construction = [int(m.group(1)) for m in re.finditer(r"(\d+)\s*座\s*[0-9,]+\s*平方米\s*在建中的数据中心", text)]
    if not operating or not construction:
        raise ValueError("GDS portfolio units not found")
    rows.append(infra("gds-directory", "gds", "provider_infrastructure_portfolio", "directory", "GDS market portfolio",
        "GDS Holdings", "aggregate_portfolio", country_codes=["CN", "HK"],
        country_scope="declared_market_footprint_not_facility_identity", relationships=[relation("describes_vendor", vendor_id("gds"))], properties={
            "operational_data_centers_declared": sum(operating), "under_construction_data_centers_declared": sum(construction),
            "as_of": None, "undated_page_not_complete_current_inventory": True,
            "market_totals_not_converted_to_facility_rows": True}))
    info = source("vnet-q2")
    facts = json.loads((REPO_ROOT / info["path"]).read_text())["facts"]
    rows.append(infra("vnet-q2", "vnet", "provider_infrastructure_portfolio", "2026-q2", "VNET wholesale capacity Q2 2026",
        "VNET Group", "aggregate_portfolio", country_codes=["CN"], country_scope="provider_wholesale_portfolio_scope",
        relationships=[relation("describes_vendor", vendor_id("vnet"))], confidence="medium", properties={
            **{k: facts[k] for k in ["as_of", "wholesale_capacity_in_service_mw", "wholesale_capacity_utilized_mw"]},
            "capacity_not_converted_to_facility_or_gpu_counts": True, "capture_method": info["capture_method"]}))
    rows.append(infra("vnet-q2", "vnet", "compute_energy_collaboration", "catl", "VNET and CATL compute-energy collaboration",
        "VNET Group", "collaboration_agreement", status="planned",
        relationships=[relation("announced_by", vendor_id("vnet"))], confidence="medium",
        parties=[{"name": "VNET Group", "role": "collaboration_partner"}, {"name": facts["compute_energy_collaboration_partner"], "role": "collaboration_partner"}],
        properties={"declared_work_areas": facts["collaboration_areas"], "commissioned_assets_and_grid_capacity_not_established": True}))
    rows.append(infra("bilibili-2025-report", "bilibili", "provider_infrastructure_portfolio", "2025-telecom-suppliers",
        "Bilibili server and bandwidth suppliers 2025", "Bilibili", "supplier_portfolio",
        country_scope="corporate_filing_supplier_population_not_facility_locations",
        relationships=[relation("describes_vendor", vendor_id("bilibili"))], properties={
            "as_of": "2025-12-31", "telecom_service_provider_count": 116,
            "providers_with_at_least_ten_percent_expenditure": 4, "combined_expenditure_share_percent": 57,
            "printed_source_page": 126, "suppliers_are_not_data_centers": True,
            "obsolete_2022_server_totals_not_used": True}))
    for key, vendor, props in [
        ("wangsu-cdn", "wangsu", {"global_node_count_min": 2800, "countries_and_regions_min": 70, "carrier_count_min": 100}),
        ("baishan-edge", "baishan", {"global_edge_node_count_min": 1500, "countries_and_regions": 60,
                                     "covered_city_count_min": 290, "redundancy_bandwidth_tbps_min": 90,
                                     "international_carrier_partners_min": 170}),
    ]:
        text = soup(key).get_text(" ", strip=True)
        for number in props.values():
            if str(number) not in text:
                raise ValueError(f"Expected portfolio number {number} not in {key}")
        rows.append(infra(key, vendor, "edge_network_portfolio", "coverage", vendor + " edge portfolio", vendor,
            "aggregate_coverage_declaration", country_scope="global_marketing_fleet_not_itemized_sites",
            relationships=[relation("describes_vendor", vendor_id(vendor))], properties={
                **props, "as_of": None, "canonical_edge_locations_generated": 0,
                "changed_marketing_totals_do_not_establish_openings_or_closures": True}))
    return rows


def chindata_records():
    key = "chindata-directory"
    codes = sorted(set(re.findall(r"ChinaNorth\s+[A-Z]\d+", soup(key).get_text(" ", strip=True))))
    rows = []
    for code in codes:
        row = location(key, "chindata", "data_center", code, code, "Chindata", "chindata_colocation",
            country_code="CN", source_record_id=code, access="not_applicable", scope=["colocation"], properties={
                "directory_is_partial": True, "code_to_campus_alias_not_established": True,
                "directory_listing_does_not_establish_current_lifecycle": True})
        row["location_precision"] = "unknown"
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.output_root
    vendors = json.loads((root / f"data/vendors/registry.{TAG}.json").read_text())["records"]
    rows = miit_recognitions() + portfolios()
    value = {"type": "InfrastructureEvidenceCollection", "schema_version": "1.0.0", "retrieved_at": DATE,
             "scope_note": "Recognition entries, supplier populations, portfolio metrics and collaboration plans are unlike units. All geometry is null. Vendor name mentions do not establish ownership or an operator/tenant contract.",
             "categories": CATEGORIES, "records": sorted(rows, key=lambda r: r["record_id"])}
    validate_collection(value, external_record_ids={v["record_id"] for v in vendors})
    write_json(root / f"data/infrastructure/china-facilities-and-portfolios.{TAG}.json", value)
    report = {"record_count": len(rows), "category_counts": dict(Counter(r["category"] for r in rows)),
              "recognized_directory_entry_count": len([r for r in rows if r["category"] == "recognized_compute_facility"]),
              "known_recognitions_are_not_current_operational_site_inventory": True,
              "external_vendor_registry": f"data/vendors/registry.{TAG}.json",
              "unresolved_aliases": [{"provider": "Chindata", "named_campus": "Sangyuan", "directory_codes": [r["source_record_id"] for r in chindata_records()],
                                      "source": evidence("chindata-sangyuan"), "relationship": "not_established"}]}
    write_json(root / f"data/infrastructure/china-facilities-and-portfolios.{TAG}.report.json", report)
    records = chindata_records()
    info = source("chindata-directory")
    write_layer(records=records, output_dir=root / "data/chindata", layer_name="data-centers", retrieved_at=DATE,
        source_url=info["source_url"], raw_path=REPO_ROOT / info["path"], parser_name="update_china_facilities.py:chindata",
        schema_version="1.2.0", extra_report={"directory_completeness": "partial", "unresolved_campus_aliases": report["unresolved_aliases"]})
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
