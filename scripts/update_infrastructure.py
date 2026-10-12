#!/usr/bin/env python3
"""Normalize reviewed connectivity infrastructure without closing the category vocabulary."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, FormatChecker

from location_common import REPO_ROOT, country_identity, repo_ref, sha256, slug, write_json, write_provenance

DATE, TAG = "2026-10-11", "20261011"
SCHEMA = REPO_ROOT / "schema/infrastructure-evidence.schema.json"
SOURCES = {
    "ofcom": ("ofcom-ngso", "web.json", "https://www.ofcom.org.uk/spectrum/space-and-satellites/non-geo-fss", "2024-03-01", "2026-07-31", "regulator_declared"),
    "pni": ("starlink-pops", "json", "https://starlink.com/api/support/v2/topics/45d1d256-171e-0f67-4895-5d248fa63b66", "2026-03-27", "2026-04-02", "provider_declared"),
    "starlink": ("starlink-updates", "js", "https://starlink.com/assets-new/page-BNqKtGsY2.js", "2026-10-06", None, "provider_declared"),
    "stargaze": ("starlink-stargaze", "html", "https://docs.space-safety.starlink.com/docs/tutorial-basics/stargaze/", None, None, "provider_declared"),
    "tea": ("rostelecom-tea-next", "html", "https://www.company.rt.ru/press/news/d480081/", "2026-10-06", None, "provider_declared"),
    "anadyr": ("rostelecom-anadyr-restored", "html", "https://www.company.rt.ru/press/news_fill/far_east/d479069/", "2026-07-16", None, "provider_declared"),
    "backbone": ("rostelecom-backbone", "html", "https://www.company.rt.ru/en/about/net/magistr/", None, None, "provider_declared"),
    "petal": ("meta-petal", "html", "https://about.fb.com/news/2026/09/announcing-petal-meta-petabit-transoceanic-cable/", "2026-09-21", None, "provider_declared"),
    "google": ("google-americas-connect", "html", "https://cloud.google.com/blog/products/infrastructure/introducing-americas-connect/", "2026-08-11", None, "provider_declared"),
    "corridor": ("de-cix-cabo-verde", "html", "https://www.de-cix.net/en/about-de-cix/media/press-releases/de-cix-and-cabo-verde-telecom-plan-new-south-atlantic-interconnection-corridor", "2026-09-29", None, "provider_declared"),
    "chile": ("esa-optical-chile", "html", "https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Ground_station_in_Chile_ready_to_connect_to_space_via_laser", "2026-03-10", None, "institution_declared"),
    "quantum": ("esa-quantum-luxembourg", "html", "https://resilience.esa.int/archives/news/first-of-its-kind-optical-ground-station-commissioned-in-luxembourg-to-demonstrate-international-quantum-secure-communications", "2026-07-26", None, "institution_declared"),
    "onest": ("esa-onest", "html", "https://resilience.esa.int/archives/projects/onest", None, "2026-02-26", "institution_declared"),
    "d2d": ("amazon-globalstar", "html", "https://press.aboutamazon.com/2026/4/amazon-to-acquire-globalstar-and-expand-amazon-leo-satellite-network", "2026-04-14", None, "provider_declared"),
    "acix": ("de-cix-acix", "html", "https://www.de-cix.net/en/about-de-cix/media/press-releases/africa-congo-internet-exchange-acix-becomes-first-distributed-ix-in-drc-with-support-from-de-cix", "2026-05-19", None, "provider_declared"),
}
CATEGORIES = {
    "satellite_network_authorization": "A regulator-listed network licence; not a constellation inventory or ground-site count.",
    "satellite_gateway_authorization": "A regulator-listed gateway licence; distinct from observed operation, ownership or unique campuses.",
    "network_interconnect_presence": "A provider-listed private interconnect directory entry, which can group multiple host facilities.",
    "leo_satellite_constellation": "A named low-Earth-orbit communications system, not a row per spacecraft.",
    "orbital_compute_constellation": "A named planned orbital computing system; plans do not establish launched compute sites.",
    "space_situational_awareness_system": "A named space-traffic sensing/coordination system; orbital sensors are not ground stations.",
    "optical_ground_station": "A specifically described optical satellite ground station or trial facility.",
    "quantum_optical_ground_station": "An optical ground station commissioned for quantum-network experimentation.",
    "optical_quantum_network_testbed": "A named optical/quantum network testbed that can include simulated infrastructure.",
    "direct_to_device_satellite_constellation": "A named direct-to-device satellite system or deployment plan.",
    "submarine_cable_system": "A named submarine fiber system, not a surveyed path, landing building or lit-capacity measurement.",
    "submarine_cable_branch": "A specifically announced branch of a named cable system.",
    "terrestrial_fiber_link": "A named terrestrial fiber system; cities and design capacity are not a surveyed alignment.",
    "terrestrial_fiber_backbone_network": "An operator's backbone network declaration with bounded aggregate claims.",
    "interconnection_corridor": "A connectivity collaboration/corridor, distinct from one new physical cable.",
    "subsea_connectivity_program": "A named programme grouping cable systems; not an additional cable asset.",
    "distributed_internet_exchange": "A named distributed traffic-exchange service, distinct from each host building or member network.",
}


def source_path(key: str) -> Path:
    stem, extension, *_ = SOURCES[key]
    return REPO_ROOT / f"data/raw/infrastructure/{stem}.{TAG}.{extension}"


def source_text(key: str) -> str:
    path = source_path(key)
    if key == "ofcom":
        payload = json.loads(path.read_text())
        assert payload["capture_method"] == "web_tool_response"
        value = re.sub(r"L\d+(?:@P\d+)?\s*:\s*", "", payload["response"])
        return re.sub(r"cite\d+†(.*?)", r"\1", value)
    return re.sub(r"\s+", " ", BeautifulSoup(path.read_bytes(), "html.parser").get_text(" ", strip=True))


def record(key: str, category: str, identifier: str, name: str, provider: str, unit: str,
           countries: list[str], status: str, properties: dict, *, prefix: str | None = None,
           country_scope: str = "explicit_source_geography", parties: list[dict] | None = None,
           relationships: list[dict] | None = None, confidence: str = "high") -> dict:
    _, _, url, published, updated, scope = SOURCES[key]
    return {
        "record_id": f"{prefix or slug(provider).replace('-', '')}:{category}:{identifier}",
        "category": category, "unit": unit, "name": name, "provider": provider,
        "parties": parties if parties is not None else [{"name": provider, "role": "announcing_party"}],
        "country_codes": sorted(countries), "country_scope": country_scope,
        "lifecycle_status": status, "source_scope": scope, "source_url": url,
        "raw_source_ref": repo_ref(source_path(key)), "source_sha256": sha256(source_path(key)),
        "source_published_at": published, "source_updated_at": updated, "retrieved_at": DATE,
        "confidence": confidence, "geometry": None, "spatial_representation": "none",
        "relationships": relationships or [], "properties": properties,
    }


def parse_ofcom() -> list[dict]:
    text = source_text("ofcom")
    assert "Last updated: 31 July 2026" in text
    network = text.split("Existing NGSO network earth station licences", 1)[1].split("Existing NGSO gateway earth station licence", 1)[0]
    gateways = text.split("Existing NGSO gateway earth station licence", 1)[1].split("## Applications received", 1)[0]
    rows = []
    for segment, category, width in ((network, "satellite_network_authorization", 3), (gateways, "satellite_gateway_authorization", 5)):
        for line in segment.splitlines():
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) != width or not re.fullmatch(r"\d{7}", cells[1]):
                continue
            licensee = re.sub(r"\s*\(PDF[^)]*\)", "", cells[0]).strip()
            legal_licensee = licensee
            properties = {"license_number": cells[1], "date_first_issued_label": cells[2],
                          "date_first_issued": datetime.strptime(cells[2], "%d %B %Y").date().isoformat(),
                          "authorization_status": "listed_existing_license", "operation_not_inferred_from_license": True}
            relationships = []
            if width == 5:
                properties.update({"associated_network_licensee": cells[3], "associated_network_license_number": cells[4] if cells[4] != "N/A" else None})
                if cells[4] != "N/A":
                    relationships.append({"relationship_type": "associated_network_authorization", "target_record_id": f"ofcom:satellite_network_authorization:{cells[4]}"})
                match = re.search(r"\(([^)]+)\)$", licensee)
                assert match, licensee
                properties["station_locality_label"] = match.group(1)
                legal_licensee = licensee[:match.start()].strip()
            rows.append(record("ofcom", category, cells[1], licensee, legal_licensee, "authorization", ["GB"], "unknown", properties,
                               prefix="ofcom", country_scope="authorization_jurisdiction_not_service_coverage", relationships=relationships,
                               parties=[{"name": legal_licensee, "role": "licensee"}]))
    assert Counter(row["category"] for row in rows) == {"satellite_network_authorization": 9, "satellite_gateway_authorization": 7}
    return rows


def parse_starlink_interconnect() -> tuple[list[dict], dict]:
    payload = json.loads(source_path("pni").read_text())
    assert payload["isValid"] and not payload["errors"]
    article = payload["content"]
    assert article["title"] == "Point of Presence Locations" and article["referenceId"] == "45d1d256-171e-0f67-4895-5d248fa63b66"
    assert article["modifiedDate"].startswith("2026-04-02")
    table = [line for line in article["bodyMarkdown"].splitlines() if line.startswith("| ")]
    assert [value.strip() for value in table[0].strip("|").split("|")] == ["Facility Name", "Country", "City", "Address"]
    rows = []
    for line in table[2:]:
        cells = [value.strip() for value in line.strip("|").split("|")]
        assert len(cells) == 4 and all(cells), line
        facility, country, city, address = cells
        country = "United States" if country == "United States of America" else country
        _, code = country_identity(country)
        assert code, country
        rows.append(record("pni", "network_interconnect_presence", f"{slug(facility)}-{code.lower()}", facility, "Starlink", "directory_entry", [code], "unknown", {
            "facility_label": facility, "city_label": city, "country_label": country, "address_as_published": address,
            "article_reference_id": article["referenceId"],
            "service_scope": "private_network_interconnect", "eligibility_context": "host_facility_in_customer_home_pop_geography",
            "facility_ownership_not_asserted": True, "ground_station_presence_not_asserted": True,
            "grouped_facility_labels_not_expanded": True,
        }, prefix="starlink", country_scope="listed_host_facility_country",
        parties=[{"name": "Starlink", "role": "interconnect_service_provider"}], confidence="medium"))
    assert len(rows) == 49
    return rows, {"article_created_at": article["createdDate"], "article_modified_at": article["modifiedDate"],
                  "article_included_countries": article["includedCountries"], "article_excluded_countries": article["excludedCountries"],
                  "metadata_semantics": "article audience settings are not facility lifecycle or country authorization", "listed_country_count": len({row["country_codes"][0] for row in rows})}


def parse_named_systems() -> list[dict]:
    rows = []
    updates = source_path("starlink").read_text()
    assert "October 6, 2026" in updates and "first 26 Starlink V3 satellites" in updates and "up to 1 million Starmind AI satellites" in updates
    rows.append(record("starlink", "leo_satellite_constellation", "starlink", "Starlink", "SpaceX / Starlink", "system", [], "operational", {
        "source_page_url": "https://starlink.com/updates", "satellites_in_orbit_claim": {"comparison": "more_than", "value": 11000},
        "first_v3_satellites_deployed_claim": 26, "deployment_period": "2026-09", "planned_satellites_upper_bound": 100000,
        "metrics_are_provider_claims_not_independent_orbital_inventory": True,
    }, prefix="spacex", country_scope="global_system_not_country_site_inventory"))
    rows.append(record("starlink", "orbital_compute_constellation", "starmind", "Starmind AI satellite plan", "SpaceX", "planned_system", [], "planned", {
        "source_page_url": "https://starlink.com/updates", "planned_satellites_upper_bound": 1000000,
        "launched_compute_sites_not_established": True, "planning_metric_not_operational_capacity": True,
    }, prefix="spacex", country_scope="global_plan_not_ground_site_inventory"))
    assert "star trackers on Starlink satellites" in source_text("stargaze")
    rows.append(record("stargaze", "space_situational_awareness_system", "stargaze", "Stargaze", "Starlink", "system", [], "operational", {
        "sensor_location_scope": "onboard_starlink_satellites", "not_a_ground_sensor_site_inventory": True,
        "provider_processing_claim_transits_per_day": {"comparison": "more_than", "value": 30000000},
    }, prefix="starlink", country_scope="orbital_system"))
    chile = source_text("chile")
    assert "passed acceptance testing" in chile and "Western Australia" in chile
    for identifier, country, name, phase in (("chile", "CL", "SSC Space optical ground station (Chile)", "commissioning"), ("western-australia", "AU", "SSC Space optical ground facility (Western Australia)", "unknown")):
        rows.append(record("chile", "optical_ground_station", identifier, name, "SSC Space", "site", [country], phase,
                           {"published_locality_scope": identifier, "precision": "country_or_region_only",
                            "source_phase": "passed_acceptance_ready_for_operations" if country == "CL" else "began_testing_2025",
                            "commercial_service_not_inferred": True}, prefix="ssc", confidence="medium"))
    quantum = source_text("quantum")
    assert "Windhof" in quantum and "26 Jul 2026" in quantum and "Post-Quantum Cryptography" in quantum
    rows.append(record("quantum", "quantum_optical_ground_station", "windhof", "INT-UQKD optical ground station, Windhof", "INT-UQKD consortium", "site", ["LU"], "commissioning", {
        "city_label": "Windhof", "source_phase": "commissioned_for_quantum_network_tests", "technologies": ["QKD", "PQC"],
        "commercial_quantum_network_not_asserted": True,
    }, prefix="intuqkd", parties=[{"name": "HITEC", "role": "builder"}, {"name": "Starion Luxembourg", "role": "consortium_lead"}, {"name": "ESA", "role": "programme_partner"}]))
    assert "26/02/2026" in source_text("onest") and "simulated Optical Ground Stations" in source_text("onest")
    rows.append(record("onest", "optical_quantum_network_testbed", "6b-128", "ONEST", "ESA ARTES / ONEST consortium", "project", [], "in_development", {
        "activity_code": "6B.128", "source_status": "ongoing_critical_design_review", "includes_real_and_simulated_stations": True,
        "simulated_stations_not_normalized_as_physical_sites": True,
    }, prefix="esa", country_scope="project_participants_not_station_geography"))
    assert "Beginning in 2028" in source_text("d2d") and "expected to close in 2027" in source_text("d2d")
    rows.append(record("d2d", "direct_to_device_satellite_constellation", "amazon-leo-d2d", "Amazon Leo direct-to-device plan", "Amazon Leo", "planned_system", [], "planned", {
        "planned_deployment_start_year": 2028, "globalstar_transaction_expected_close_year": 2027,
        "transaction_status": "announced_definitive_agreement_subject_to_conditions", "completed_acquisition_not_asserted": True,
    }, prefix="amazon", country_scope="global_plan_not_licensed_service_territory"))
    petal = source_text("petal")
    assert "2029" in petal and "7,000 km" in petal and "1 petabit" in petal
    rows.append(record("petal", "submarine_cable_system", "petal", "Petal", "Meta", "system", ["FR", "US"], "planned", {
        "planned_ready_for_service_year": 2029, "approximate_length_km_claim": 7000, "design_capacity_petabits_per_second_claim": 1,
        "technology": "multi_core_fiber", "capacity_semantics": "design_not_lit_or_measured",
        "surveyed_route_not_published_in_captured_source": True,
    }, prefix="meta", country_scope="named_system_endpoint_countries", parties=[{"name": "Meta", "role": "project_lead"}, {"name": "NEC", "role": "supplier"}, {"name": "Sumitomo Electric Industries", "role": "supplier"}, {"name": "Orange", "role": "planned_french_landing_partner"}]))
    tea = source_text("tea")
    assert "06.10.2026" in tea and "96 темных волокон" in tea and "завершил строительство" in tea
    rows.append(record("tea", "terrestrial_fiber_link", "tea-next", "TEA NEXT", "Rostelecom / Atlas", "system", ["RU"], "operational", {
        "source_phase": "construction_completed_and_launched", "dark_fiber_count_claim": 96,
        "capacity_scenarios_tbps_claim": [384, 768], "additional_capacity_scenario": "more_than_1_pbps_depending_on_dwdm",
        "capacity_semantics": "technology_dependent_design_not_lit_capacity",
        "moscow_kyakhta_round_trip_delay_ms_upper_bound_claim": 65, "latency_is_provider_claim_not_measurement": True,
        "border_connection_countries_named": ["CN", "MN"], "surveyed_alignment_not_established": True,
    }, prefix="rostelecom", country_scope="published_physical_route_country_border_exits_are_separate"))
    assert "16.07.2026" in source_text("anadyr") and "телеком-услуг в полном объеме" in source_text("anadyr")
    rows.append(record("anadyr", "submarine_cable_system", "petropavlovsk-kamchatsky-anadyr", "Petropavlovsk-Kamchatsky–Anadyr", "Rostelecom", "system", ["RU"], "operational", {
        "source_phase": "full_service_restoration_reported", "service_restored_at": "2026-07-16",
        "endpoint_localities": ["Petropavlovsk-Kamchatsky", "Anadyr"], "operational_status_is_dated_operator_assertion": True,
    }, prefix="rostelecom", country_scope="named_system_endpoint_country"))
    assert "Over 350 access points" in source_text("backbone") and "17 international cable systems" in source_text("backbone")
    rows.append(record("backbone", "terrestrial_fiber_backbone_network", "rostelecom-backbone", "Rostelecom backbone network", "Rostelecom", "network", ["RU"], "unknown", {
        "access_points_claim": {"comparison": "more_than", "value": 350}, "international_cable_participation_count_claim": 17,
        "source_publication_date_unknown": True, "aggregate_counts_not_expanded_into_site_or_cable_records": True,
    }, prefix="rostelecom", country_scope="russia_confirmed_international_country_membership_unspecified", confidence="medium"))
    assert "Letter of Intent" in source_text("corridor") and "29 September 2026" in source_text("corridor")
    rows.append(record("corridor", "interconnection_corridor", "south-atlantic", "South Atlantic interconnection corridor", "DE-CIX / CVTelecom", "project", ["BR", "CV", "PT"], "planned", {
        "source_phase": "letter_of_intent", "named_metro_endpoints": ["Lisbon", "São Paulo"],
        "new_physical_cable_or_specific_gateway_not_asserted": True,
    }, prefix="decix", country_scope="announced_corridor_countries_not_surveyed_route"))
    google = source_text("google")
    assert "August 11, 2026" in google and all(name in google for name in ("Alisios", "Canoa", "OlaLuz", "Firmina"))
    programme_id = "google:subsea_connectivity_program:americas-connect"
    rows.append(record("google", "subsea_connectivity_program", "americas-connect", "Americas Connect", "Google", "program", [], "in_development", {
        "programme_not_additional_cable_asset": True, "existing_systems_named": ["Curie", "Nuvem", "Sol", "Firmina"],
    }, prefix="google", country_scope="programme_includes_multiple_existing_and_planned_systems"))
    for name, codes, endpoints in (("Alisios", ["CL", "DO", "PA"], ["Dominican Republic", "Panama", "Chile"]),
                                   ("Canoa", ["BM", "DO"], ["Dominican Republic", "Bermuda"]),
                                   ("OlaLuz", ["DO", "US"], ["Dominican Republic", "Florida"])):
        rows.append(record("google", "submarine_cable_system", slug(name), name, "Google", "system", codes, "planned", {
            "source_phase": "announced_new_system", "published_endpoint_labels": endpoints, "landing_buildings_or_route_geometry_not_established": True,
        }, prefix="google", country_scope="named_system_endpoint_countries",
        relationships=[{"relationship_type": "part_of_program", "target_record_id": programme_id}]))
    rows.append(record("google", "submarine_cable_branch", "firmina-dominican-republic", "Firmina Dominican Republic branch", "Google", "segment", ["DO"], "planned", {
        "parent_system_name": "Firmina", "branch_endpoint_named": "Dominican Republic", "parent_system_not_duplicated_as_new_asset": True,
    }, prefix="google", country_scope="newly_named_branch_endpoint_only",
    relationships=[{"relationship_type": "part_of_program", "target_record_id": programme_id}]))
    assert "19 May 2026" in source_text("acix") and "FIH1" in source_text("acix")
    rows.append(record("acix", "distributed_internet_exchange", "acix", "Africa Congo Internet Exchange (ACIX)", "ACIX", "service", ["CD"], "operational", {
        "metro_label": "Kinshasa", "source_phase": "expanded_to_additional_host_facility",
        "additional_host_facility_label": "OADC Texaf Kinshasa FIH1", "exchange_not_a_provider_owned_data_center": True,
    }, prefix="acix", parties=[{"name": "Internet pour tous", "role": "programme_partner"}, {"name": "UNITED S.A.", "role": "programme_partner"}, {"name": "DE-CIX", "role": "technology_partner"}]))
    return rows


def validate_collection(collection: dict, *, external_record_ids: set[str] | None = None) -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()), format_checker=FormatChecker())
    validator.validate(collection)
    ids = {row["record_id"] for row in collection["records"]}
    if len(ids) != len(collection["records"]):
        raise ValueError("Duplicate infrastructure record ID")
    for row in collection["records"]:
        if row["category"] not in collection["categories"]:
            raise ValueError(f"Undefined category {row['category']}")
        if row["source_sha256"] != sha256(REPO_ROOT / row["raw_source_ref"]):
            raise ValueError(f"Source checksum mismatch for {row['record_id']}")
        for relationship in row["relationships"]:
            if relationship["target_record_id"] not in ids | (external_record_ids or set()):
                raise ValueError(f"Unresolved relationship in {row['record_id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    for key, (_, extension, url, published, _, _) in SOURCES.items():
        write_provenance(source_path(key), source_url=url, retrieved_at=DATE, source_published_at=published,
                         media_type={"html": "text/html", "json": "application/json", "js": "application/javascript", "web.json": "application/json"}[extension],
                         notes="Public evidence snapshot; web.json explicitly contains a web-reader extraction rather than original HTTP HTML. Geometry, ownership, operation and exhaustive coverage require separate support. Source-specific terms apply.")
    pni_rows, pni_metadata = parse_starlink_interconnect()
    records = sorted(parse_ofcom() + pni_rows + parse_named_systems(), key=lambda row: row["record_id"])
    collection = {"type": "InfrastructureEvidenceCollection", "schema_version": "1.0.0", "retrieved_at": DATE,
                  "scope_note": "Global bounded public-source evidence with open categories and unlike units. Not a site, spacecraft, cable-length or operating-capacity total; counts remain separate from location and network evidence inventories.",
                  "categories": CATEGORIES, "records": records}
    validate_collection(collection)
    directory = args.output_root / "data/infrastructure"
    output = directory / f"connectivity.{TAG}.json"
    write_json(output, collection)
    report = {"schema_version": "1.0.0", "retrieved_at": DATE, "record_count": len(records), "canonical_sha256": sha256(output),
              "category_counts": dict(sorted(Counter(row["category"] for row in records).items())),
              "unit_counts": dict(sorted(Counter(row["unit"] for row in records).items())),
              "lifecycle_counts": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
              "geometry_null_count": sum(row["geometry"] is None for row in records), "starlink_interconnect_metadata": pni_metadata,
              "generated_files": [repo_ref(output)],
              "derived_files": {"csv": {"path": repo_ref(output.with_suffix(".csv")), "source": repo_ref(output), "generator": f"make {repo_ref(output.with_suffix('.csv'))}"}},
              "sources": [{"key": key, "raw_source_ref": repo_ref(source_path(key)), "source_url": info[2], "source_sha256": sha256(source_path(key)), "source_published_at": info[3], "source_updated_at": info[4]} for key, info in sorted(SOURCES.items())],
              "limits": ["No exact facility coordinates, surveyed fiber alignments or invented links.", "PNI rows can group host facilities and are not Starlink-owned ground stations.", "Current UK licence listings do not prove live operation; gateway authorizations can share a locality.", "Source publication/update dates differ from the October retrieval date.", "Forward-looking capacities, spacecraft plans and acquisitions remain plans, not current deployed inventory."],
              "source_gaps": [
                  {"category": "russian_satellite_teleport", "source_url": "https://www.rscc.ru/infrastructure/teleports/", "result": "raw HTTPS capture failed certificate-chain validation; reader directory/site requests also failed", "normalized_record_count": 0},
                  {"category": "global_submarine_route_geometry", "source_url": "https://www2.telegeography.com/license-geocoded-map-data", "result": "geocoded dataset requires source-specific licence; public map routes are schematic; no bulk route geometry imported", "normalized_geometry_count": 0},
              ]}
    write_json(output.with_suffix(".report.json"), report)
    write_json(directory / f"russia-connectivity.{TAG}.json", {**collection, "scope_note": "Derived view of explicit RU country assertions; multinational coverage and unspecified countries are not inferred. Excluded from infrastructure evidence totals.", "records": [row for row in records if "RU" in row["country_codes"]]})
    print(json.dumps({"infrastructure_evidence_records": len(records), "categories": len(CATEGORIES), "pni_entries": len(pni_rows)}))


if __name__ == "__main__":
    main()
