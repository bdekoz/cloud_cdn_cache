#!/usr/bin/env python3
"""Named China-linked cables, station declarations and carrier service evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

from china_enrichment_common import DATE, TAG, infra, source, soup
from location_common import REPO_ROOT, write_json
from update_china_ai import relation, vendor_id
from update_infrastructure import validate_collection

CATEGORIES = {
    "submarine_cable_system": "A named submarine cable declaration; design capacity and landing milestones are not surveyed routes or measured lit capacity.",
    "cable_landing_station": "A specifically named/code-identified station declaration with source-specific operator role; a shared locality does not establish the same facility.",
    "network_interconnect_presence": "A named interconnection site in a provider statement; this is not proof of facility ownership or current operation.",
    "terrestrial_fiber_link": "A declared backhaul/fiber connection between named endpoints; route alignment and current live state require separate evidence.",
    "carrier_backbone_portfolio": "An aggregate carrier-network declaration with explicit scope and publication/as-of dates; totals do not identify individual nodes or owned cables.",
    "quantum_secured_wan_service": "A provider-described quantum/encrypted WAN service, distinct from independently verified quantum hardware or a physical fiber inventory.",
}


def declarations():
    rows = []
    alc_text = soup("telecom-alc").get_text(" ", strip=True)
    if not all(s in alc_text for s in ["6,200", "325", "13 leading operators", "first self-built"]):
        raise ValueError("ALC source milestones or units changed")
    alc = infra("telecom-alc", "ctg", "submarine_cable_system", "alc", "Asia Link Cable (ALC)", "China Telecom Global", "system",
        country_codes=["CN", "HK", "SG", "PH", "VN", "BN", "MY"], status="in_development",
        country_scope="explicit_source_endpoint_countries_and_territories",
        parties=[{"name": "China Telecom", "role": "largest_investor_and_project_leader"}],
        relationships=[relation("announced_by", vendor_id("ctg"))], properties={
            "landing_milestone_date": "2026-05-14", "length_km_approx": 6200,
            "design_capacity_tbps_gt": 325, "consortium_operator_count_declared": 13,
            "future_operator_bandwidth_tbps_gt": 100,
            "full_commercial_operation_not_established_by_landing_announcement": True,
            "landing_localities": ["Hong Kong", "Hainan"], "surveyed_alignment_not_published": True})
    rows.append(alc)
    station = infra("telecom-alc", "ctg", "cable_landing_station", "chung-hom-kok", "China Telecom Chung Hom Kok cable landing station",
        "China Telecom", "named_station_declaration", country_codes=["HK"], country_scope="named_station_locality",
        relationships=[relation("cable_landing_milestone", alc["record_id"])], properties={
            "locality": "Chung Hom Kok, Hong Kong", "provider_self_built_claim": True,
            "historical_landing_milestone_not_current_lifecycle_proof": True,
            "not_merged_with_hkis1_by_shared_locality": True})
    rows.append(station)
    adc_text = soup("telecom-adc").get_text(" ", strip=True)
    if not all(s in adc_text for s in ["9988", "160", "20Tb/s"]):
        raise ValueError("ADC source design metrics changed")
    adc = infra("telecom-adc", "ctg", "submarine_cable_system", "adc", "Asia Direct Cable (ADC)", "China Telecom Global", "system",
        country_codes=["CN", "HK", "JP", "SG"], country_scope="explicit_named_geographies_partial_endpoint_list", status="operational",
        relationships=[relation("announced_by", vendor_id("ctg"))], properties={
            "source_phase": "commissioning_launch_event", "event_date": "2025-03-24",
            "length_km_declared": 9988, "system_design_capacity_tbps_gt": 160,
            "design_capacity_per_fiber_pair_tbps": 20, "design_capacity_not_measured_lit_capacity": True,
            "partial_country_list_not_exhaustive_route_inventory": True})
    rows.append(adc)
    hkis = infra("telecom-hkis1", "sunevision", "cable_landing_station", "hkis-1", "HKIS-1", "SUNeVision", "station_code_declaration",
        country_codes=["HK"], country_scope="named_station_locality", relationships=[relation("declared_operator", vendor_id("sunevision")), relation("landing_system", adc["record_id"])],
        properties={"source_station_code": "HKIS-1", "locality": "Chung Hom Kok, Hong Kong",
                    "source_phase": "ADC Hong Kong landing announcement 2023", "carrier_and_cloud_neutral_claim": True,
                    "current_lifecycle_not_established_by_2023_release": True,
                    "not_merged_with_china_telecom_self_built_station": True})
    rows.append(hkis)
    for label, identifier in [("MEGA-i", "mega-i"), ("MEGA Plus", "mega-plus")]:
        if label not in soup("telecom-hkis1").get_text(" ", strip=True):
            raise ValueError(f"Interconnection label missing: {label}")
        rows.append(infra("telecom-hkis1", "sunevision", "network_interconnect_presence", identifier, label,
            "SUNeVision", "named_interconnection_site", country_codes=["HK"],
            country_scope="named_hong_kong_interconnection_facility_not_coordinate",
            relationships=[relation("declared_operator", vendor_id("sunevision"))], properties={
                "site_name": label, "source_phase": "2023 joint provider announcement",
                "facility_coordinates_and_current_ownership_not_established": True}))
    rows.append(infra("telecom-hkis1", "sunevision", "terrestrial_fiber_link", "hkis1-mega-campus", "HKIS-1 to MEGA Campus/MEGA-i backhaul",
        "SUNeVision", "declared_backhaul_connection", country_codes=["HK"], country_scope="named_connection_endpoints",
        relationships=[relation("endpoint", hkis["record_id"]), relation("endpoint", "sunevision:network_interconnect_presence:mega-i")],
        properties={"published_endpoint_labels": ["HKIS-1", "MEGA Campus", "MEGA-i"],
                    "current_live_state_and_surveyed_route_not_established": True}))
    info = source("unicom-csr-2025")
    text = subprocess.check_output(["pdftotext", "-layout", str(REPO_ROOT / info["path"]), "-"], text=True, stderr=subprocess.DEVNULL)
    if not all(s in text for s in ["SEA-H2X", "L2 Cable Landing Station", "74T", "57T"]):
        raise ValueError("Unicom CSR cable/portfolio declarations missing")
    sea = infra("unicom-csr-2025", "cucloud", "submarine_cable_system", "sea-h2x", "South East Asia-Hainan-Hong Kong (SEA-H2X)",
        "China Unicom", "system", country_codes=["CN", "HK", "SG", "MY", "TH", "PH"],
        country_scope="explicit_source_named_endpoint_geographies", relationships=[relation("announced_by", vendor_id("china-unicom"))],
        parties=[{"name": "China Unicom", "role": "investment_participant"}], properties={
            "source_report_year": 2025, "source_phase": "Hong Kong landing and channel description",
            "current_ready_for_service_date_not_established": True, "surveyed_alignment_not_published": True})
    rows.append(sea)
    rows.append(infra("unicom-csr-2025", "cucloud", "cable_landing_station", "tseung-kwan-o-l2", "China Unicom Hong Kong Tseung Kwan O L2 cable landing station",
        "China Unicom", "station_code_declaration", country_codes=["HK"], country_scope="source_named_station_locality",
        relationships=[relation("landing_system", sea["record_id"])], properties={
            "source_station_code": "L2", "locality": "Tseung Kwan O, Hong Kong", "source_report_year": 2025,
            "current_lifecycle_and_facility_coordinates_not_established": True}))
    rows.append(infra("unicom-csr-2025", "cucloud", "carrier_backbone_portfolio", "2025-belt-and-road", "China Unicom international infrastructure portfolio 2025",
        "China Unicom", "aggregate_network_portfolio", country_scope="international_report_scope_with_mainland_cross_border_component",
        relationships=[relation("describes_vendor", vendor_id("china-unicom"))], properties={
            "as_of_reporting_year": 2025, "physical_pops_declared": 63,
            "published_capacity_labels": {"subsea_configured_capacity": "74T", "asia_africa_europe_channels": "12T", "mainland_cross_border_terrestrial": "57T"},
            "source_capacity_unit_label_retained": "T", "aggregate_nodes_and_capacity_not_site_or_fiber_identities": True}))
    quantum_text = soup("telecom-quantum-sdwan").get_text(" ", strip=True)
    if not all(s in quantum_text for s in ["commercially operational", "China-Egypt", "quantum encryption"]):
        raise ValueError("Quantum SD-WAN source scope changed")
    rows.append(infra("telecom-quantum-sdwan", "ctg", "quantum_secured_wan_service", "china-egypt", "China Telecom Global cross-border quantum SD-WAN",
        "China Telecom Global", "service_product", country_codes=["CN", "EG"], country_scope="declared_service_connection_geographies",
        status="operational", relationships=[relation("offered_by", vendor_id("ctg"))], properties={
            "provider_commercial_operation_claim": True, "source_endpoint_labels": ["China-Egypt TEDA Suez Economic and Trade Cooperation Zone", "corporate headquarters in China"],
            "quantum_capabilities_not_independently_verified": True, "physical_quantum_or_fiber_route_not_asserted": True}))
    text = soup("telecom-portfolio").get_text(" ", strip=True)
    if not all(s in text for s in ["259", "304", "185"]):
        raise ValueError("CTG portfolio totals changed")
    rows.append(infra("telecom-portfolio", "ctg", "carrier_backbone_portfolio", "global-directory", "China Telecom Global network portfolio",
        "China Telecom Global", "aggregate_network_portfolio", country_scope="global_marketing_portfolio_not_itemized_locations",
        relationships=[relation("describes_vendor", vendor_id("ctg"))], properties={
            "international_nodes_declared": 259, "published_transmission_bandwidth_label": "304T", "international_sea_and_land_cables_declared": 185,
            "as_of": None, "cable_participation_or_ownership_scope_not_established": True,
            "marketing_totals_do_not_establish_site_identifiers": True}))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    rows = declarations()
    registry = json.loads((args.output_root / f"data/vendors/registry.{TAG}.json").read_text())["records"]
    value = {"type": "InfrastructureEvidenceCollection", "schema_version": "1.0.0", "retrieved_at": DATE,
             "scope_note": "Named cable systems, station declarations, historical backhaul, carrier portfolio aggregates and service products are unlike units. Source dates remain explicit; no route geometry or inferred physical coordinates.",
             "categories": CATEGORIES, "records": sorted(rows, key=lambda r: r["record_id"])}
    validate_collection(value, external_record_ids={r["record_id"] for r in registry})
    write_json(args.output_root / f"data/infrastructure/china-carrier-links.{TAG}.json", value)
    report = {"record_count": len(rows), "category_counts": dict(Counter(r["category"] for r in rows)),
              "all_geometry_null": True, "same_locality_stations_not_merged": ["China Telecom Chung Hom Kok", "SUNeVision HKIS-1"],
              "external_vendor_registry": f"data/vendors/registry.{TAG}.json"}
    write_json(args.output_root / f"data/infrastructure/china-carrier-links.{TAG}.report.json", report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
