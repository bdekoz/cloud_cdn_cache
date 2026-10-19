#!/usr/bin/env python3
"""Retain cache-host follow-up evidence without converting CDN candidates into sites."""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import ipaddress
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup

from location_common import REPO_ROOT, repo_ref, sha256, write_json
from network_common import canonical_network_record, write_network_layer
from update_infrastructure import validate_collection
from update_network import utc_datetime
from update_apple_tv import csv_target

DATE, TAG = "2026-10-19", "20261019"
RAW = REPO_ROOT / "data/raw/apple-aec-followup"
CATALOG = RAW / f"catalog.{TAG}.json"
BASELINE = REPO_ROOT / f"data/raw/repository/manifest-before-apple-aec-followup.{TAG}.json"
INFRA = f"data/infrastructure/apple-aec-followup.{TAG}.json"
REVIEW = f"data/apple/aec-followup.{TAG}.json"
COUNTRIES = {"ae": "United Arab Emirates", "au": "Australia", "hu": "Hungary", "in": "India", "ru": "Russia", "ua": "Ukraine"}


def read(path):
    return json.loads(path.read_text())


@lru_cache
def sources():
    entries = read(CATALOG)["sources"]
    for s in entries:
        if s.get("path"):
            assert sha256(REPO_ROOT / s["path"]) == s["sha256"], s["source_id"]
            assert read(REPO_ROOT / (s["path"] + ".provenance.json")) == s
    assert len({s["source_id"] for s in entries}) == len(entries)
    return {s["source_id"]: s for s in entries}


def source(key):
    s = sources()[key]
    assert s["result"] == "retrieved", key
    return s


def evidence(key):
    s = source(key)
    return dict(source_url=s["source_url"], raw_source_ref=s["path"], source_sha256=s["sha256"],
                retrieved_at=s["retrieved_at"], source_published_at=s.get("source_published_at"),
                source_updated_at=s.get("source_updated_at"))


def soup(key):
    return BeautifulSoup((REPO_ROOT / source(key)["path"]).read_text(), "html.parser")


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def table_rows(table):
    return [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]


def candidates():
    records = []
    comparison_path = REPO_ROOT / f"data/observations/cdn-asn-comparison.{TAG}.json"
    comparison = {r["asn"]: r for r in read(comparison_path)["records"]}
    for cc, country in COUNTRIES.items():
        key = "netify-apple-" + cc
        for table in soup(key).find_all("table"):
            rows = table_rows(table)
            headers = rows[0]
            assert headers in (["ASN Label", "ASN", "IP Count", "Sample IP"],
                               ["Network", "City", "Category", "IP Count", "Sample IP"],
                               ["Network", "City", "Category", "IP Count", "Sample ASN Route"]), headers
            section = table.find_previous("h2").get_text(" ", strip=True)
            for values in rows[1:]:
                assert len(headers) == len(values)
                fields = dict(zip(headers, values, strict=True))
                network = fields.get("Network") or fields["ASN Label"]
                city = fields.get("City") or None
                asn = int(fields["ASN"].removeprefix("AS")) if "ASN" in fields else None
                address = fields.get("Sample IP")
                address = address if address and address != "-" else None
                prefix = fields.get("Sample ASN Route")
                if address:
                    ipaddress.ip_address(address)
                if prefix:
                    ipaddress.ip_network(prefix, strict=True)
                kind = ("other_asn_candidate" if asn else "apple_network_scope_only" if "Sample ASN Route" in fields
                        else "isp_partner_candidate" if fields["Category"] == "ISP/Telco" else "hosting_classification_not_aec_evidence")
                locality_key = city or (str(asn) if asn else "unknown")
                identifier = f"apple:cdn-candidate:netify-{cc}-{slug(network)}-{slug(locality_key)}"
                record = dict(candidate_id=identifier, country_code=cc.upper(), country_label=country,
                    country_scope="publisher_page_label_not_verified_location", network_label=network,
                    city_label=city, asn=asn, publisher_network_category=fields.get("Category"),
                    ip_count=int(fields["IP Count"].replace(",", "")), sample_ip=address, sample_prefix=prefix,
                    candidate_kind=kind, source_section=section, evidence=evidence(key),
                    captured_at=source(key)["captured_at"], publisher_observed_at=None,
                    aec_deployment_verified=False, apple_tv_delivery_verified=False,
                    geometry=None, location_admission="held", ip_count_is_not_appliance_count=True)
                if asn:
                    old = comparison.get(asn)
                    record["earlier_apple_asn_observation"] = dict(
                        record_id=old["provider_record_ids"]["apple"] if old else None,
                        path=repo_ref(comparison_path), sha256=sha256(comparison_path),
                        semantics="Earlier TLS-presence observation; neither AEC identity nor a physical location is established.")
                records.append(record)
    assert len({r["candidate_id"] for r in records}) == len(records)
    return sorted(records, key=lambda r: r["candidate_id"])


def host_row(key, identifier, category, host, properties):
    return dict(record_id="apple:aec-followup:" + identifier, category=category, unit="assertion",
        name="Apple cache follow-up: " + host, provider="Apple",
        parties=[dict(name="Apple", role="content_provider"), dict(name=host, role="declaring_host_or_exchange")],
        country_codes=[], country_scope="cache_location_not_established", lifecycle_status="unknown",
        source_scope="provider_declared", **evidence(key), confidence="high", geometry=None,
        spatial_representation="none", relationships=[], properties=dict(
            physical_site_count_not_asserted=True, apple_tv_delivery_established=False, locality=None, **properties))


def hosts():
    history = soup("giganet-hu-history")
    sentence = history.find(string=re.compile("Netflix és Apple cache telepítése"))
    assert sentence and sentence.find_previous("h3").get_text(strip=True) == "2024"
    infrastructure = soup("giganet-hu-infrastructure").get_text(" ", strip=True)
    assert "budapesti és nyíregyházi infrastruktúra" in infrastructure
    content = soup("ixaustralia-content").get_text(" ", strip=True)
    assert "Locally hosted caches" in content and "Apple, Google" in content
    policy = soup("lucix-route-policy").get_text(" ", strip=True)
    assert "Special <peer-as> values:" in policy and "Apple Edge Cache (AEC) = 31128" in policy
    return [host_row("giganet-hu-history", "giganet-hu", "cache_host_declaration", "Giganet Internet Szolgaltato",
                dict(claim_year=2024, reported_installation=True, aec_program_identity_explicit=False,
                     mapping_disposition="held_no_unique_cache_city", current_operation_not_verified=True,
                     infrastructure_cities_not_cache_assignments=["Budapest", "Nyiregyhaza"],
                     infrastructure_evidence=evidence("giganet-hu-infrastructure"),
                     same_name_ukrainian_operator_not_joined=True, bix_pilot_site_identity_not_established=True)),
            host_row("ixaustralia-content", "ixaustralia-hosting", "cache_host_declaration", "IX Australia",
                dict(reported_hosting=True, aec_program_identity_explicit=False,
                     mapping_disposition="held_hosted_caches_without_placement", individual_cache_sites_not_listed=True)),
            host_row("lucix-route-policy", "lucix-policy", "cache_routing_policy_reference", "LU-CIX",
                dict(aec_program_identity_explicit=True, peer_as_value=31128, route_server_asn=49624,
                     identifier_scope="special_peer_as_value_in_route_server_policy",
                     mapping_disposition="held_routing_policy_not_cache_placement"))]


def registry_review():
    data = read(REPO_ROOT / source("ripe-as31128-rdap")["path"])
    assert data["handle"] == "AS31128" and data["startAutnum"] == data["endAutnum"] == 31128
    orgs = []
    for entity in data["entities"]:
        card = {field[0]: field[3] for field in entity.get("vcardArray", [None, []])[1]}
        if card.get("kind") == "org" and "registrant" in entity.get("roles", []):
            orgs.append(dict(handle=entity["handle"], name=card["fn"]))
    assert orgs == [dict(handle="ORG-ADIL1-RIPE", name="Apple Distribution International Ltd.")]
    return dict(asn=31128, registry_name=data["name"], registrant_organizations=orgs,
                registry_status=data["status"], source_events=data["events"], evidence=evidence("ripe-as31128-rdap"),
                cache_service_or_location_not_established=True,
                note="The registry name SHAZAM-AS and operator AEC labels are different identifiers. The earlier PeeringDB miss did not establish an unallocated ASN.")


def routing(records, output):
    network, results = [], []
    for candidate in records:
        if candidate["asn"] is None:
            continue
        address = candidate["sample_ip"]
        key = "routing-" + address.replace(".", "-")
        payload = read(REPO_ROOT / source(key)["path"])
        data = payload["data"]
        prefix, asns = data["prefix"], list(map(int, data["asns"]))
        assert ipaddress.ip_address(address) in ipaddress.ip_network(prefix)
        matched = candidate["asn"] in asns
        result = dict(candidate_id=candidate["candidate_id"], address=address, prefix=prefix,
                      reported_asn=candidate["asn"], observed_origin_asns=asns,
                      reported_asn_is_observed_origin=matched, evidence=evidence(key))
        results.append(result)
        for asn in asns:
            e = evidence(key)
            e.pop("source_updated_at")
            network.append(canonical_network_record(record_id=f"network:apple-aec-candidates:route-{address}-{asn}",
                evidence_type="routing_origin", subject_type="prefix", subject_id=prefix,
                provider=candidate["network_label"] if matched else "Apple" if asn == 31128 else None,
                service="apple_cdn_candidate", prefix=prefix, ip_family=ipaddress.ip_address(address).version,
                asn=asn, relationship_type="originates_prefix", object_type="asn", object_id=f"AS{asn}",
                status="announced", source_scope="observed", **e, observed_at=utc_datetime(payload["time"]),
                valid_from=None, valid_to=None, confidence="high", properties=dict(
                    candidate_id=candidate["candidate_id"], sample_address=address,
                    address_basis="third_party_classification_not_http_peer", classification_evidence=candidate["evidence"],
                    reported_network=candidate["network_label"], reported_asn=candidate["asn"],
                    reported_asn_is_observed_origin=matched, aec_deployment_not_established=True,
                    physical_location_not_asserted=True, service_health_not_asserted=True,
                    registry_identity_evidence=evidence("ripe-as31128-rdap") if asn == 31128 else None)))
    write_network_layer(records=network, layer_name="apple-aec-candidate-routing", retrieved_at=DATE,
                        parser_name="scripts/update_apple_aec_followup.py", output_root=output)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    records = candidates()
    rows = hosts()
    collection = dict(type="InfrastructureEvidenceCollection", schema_version="1.0.0", retrieved_at=DATE,
        scope_note="Follow-up cache-host and routing-policy declarations; no new cache locality is established.",
        categories=dict(cache_host_declaration="Operator-declared Apple caching with unresolved placement and program identity.",
                        cache_routing_policy_reference="AEC routing-policy identifier, not an installed site."), records=rows)
    validate_collection(collection)
    write_json(args.output_root / INFRA, collection)
    write_json((args.output_root / INFRA).with_suffix(".report.json"), dict(built_at=DATE, record_count=len(rows),
        physical_site_total=None, parser="scripts/update_apple_aec_followup.py", derived_files=csv_target(INFRA)))
    origins = routing(records, args.output_root)
    overview = soup("netify-apple")
    metrics = {r[0]: int(r[1].replace(",", "")) for table in overview.find_all("table")[1:] for r in table_rows(table)[1:]}
    listed = {a["href"].rsplit("/", 1)[-1] for a in overview.find_all("a", href=True) if "/cdn/apple-cdn/country/" in a["href"]}
    geo = soup("netify-geolocation").get_text(" ", strip=True)
    assert "Netify's data collectors" in geo and "IPinfo" in geo
    previous = read(REPO_ROOT / f"data/apple/aec-review.{TAG}.json")
    previous_held = [r for r in previous["locality_dispositions"] if r["disposition"].startswith("held_")]
    write_json(args.output_root / REVIEW, dict(built_at=DATE, canonical_records_added=0, cache_map_points_added=0,
        baseline_manifest=dict(path=repo_ref(BASELINE), sha256=sha256(BASELINE)),
        source_catalog=dict(path=repo_ref(CATALOG), sha256=sha256(CATALOG)),
        candidates=records, candidate_count=len(records), candidate_kind_counts=dict(sorted(Counter(r["candidate_kind"] for r in records).items())),
        country_candidate_counts=dict(sorted(Counter(r["country_code"] for r in records).items())),
        publisher_metrics=dict(values=metrics, evidence=evidence("netify-apple"),
            observed_at=None, cache_inventory_interpretation=False, ip_counts_are_not_server_counts=True),
        geographic_method=dict(evidence=evidence("netify-geolocation"),
            city="Publisher's collectors and analysis", country_fallback="IPinfo", physical_facility_confirmation=False),
        priority_country_coverage={cc.upper(): "country_page_retained" if cc in COUNTRIES else
            "not_listed_in_captured_directory_not_absence" for cc in ["in", "ru", "ae", "sa", "cn"]},
        unlisted_priority_country_codes=[cc.upper() for cc in ["cn", "sa"] if cc not in listed],
        routing_checks=origins, registry_identity=registry_review(), prior_unlocated_hosts=previous_held,
        prior_host_followup={"BIX / Giganet": "Hungarian host reports a 2024 Apple-cache installation; cache city and pilot-to-site identity remain unresolved.",
            "IX Australia": "Explicit Apple cache-hosting statement plus an independent Brisbane classification; no primary cache-to-city assignment.",
            "CEnet": "Independent ASN candidate supports further sampling. General service directory names Apple peering and Google/Akamai caches; omission does not establish AEC retirement.",
            "LU-CIX": "31128 documented as a special route-server peer-as value; no cache placement.",
            "1-IX": "Direct looking-glass capture is a JavaScript shell; indexed session snippets are not admitted as current observations.",
            "PIT-IX": "No additional location source established in this pass; prior membership evidence remains held.",
            "TENET": "No additional location source established in this pass; prior installation declaration remains held."},
        retained_source_limits={s["source_id"]: dict(result=s["result"], http_status=s.get("http_status"), error=s.get("error"))
            for s in sources().values() if s["result"] != "retrieved"},
        admission_limits=["Netify combines Apple-owned CDN, embedded ISP and hosting-network classifications; inclusion is not per-row AEC proof.",
            f"All {len(records)} candidate rows have null geometry; named cities remain publisher labels until a cache-specific host join is established.",
            "Hosting-network entries are retained as excluded leads, not cache deployments. Country-page absence is not infrastructure absence.",
            "A current routing origin validates routing only. It does not establish Apple service responses, physical placement, or that every address in the prefix is a cache.",
            "The Hungarian and Ukrainian Giganet names are not merged. Earlier Apple ASN observations establish neither AEC nor TV identity.",
            "No new target-host probes, subscriber sessions or distributed measurements were launched."],
        next_steps=["Collect public-preview response headers from a known observer on each candidate access network, retaining actual peer address, observer ASN and time.",
            "Join an Apple cache hostname or peer to an explicit host/site declaration before adding an AEC map point.",
            "Resolve Hungarian Giganet's installed cache city and the separate AS42864/AS31128 host-versus-routing labels without choosing Budapest or Nyiregyhaza from office or backbone presence."]))
    print(f"Apple cache follow-up: {len(rows)} host/policy assertions, {len(records)} held CDN classifications, {len(origins)} routing checks; no new cache map points")


if __name__ == "__main__":
    main()
