#!/usr/bin/env python3
"""Reproduce the bounded Yandex/crypto enrichment assessment from retained evidence.

This writes an assessment, not canonical location or network inventory. It makes
no network requests and preserves unknown origin locations.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from location_common import REPO_ROOT, sha256, write_json

TAG = "20261019"
DATE = "2026-10-19"
SOURCES = {
    "zones": "yandex/cloud-zones",
    "regions": "yandex/cloud-regions",
    "public_ips": "yandex/cloud-public-ips",
    "cdn_cities": "yandex/cdn-pops",
    "cdn_prefixes": "yandex/cdn-prefixes",
    "yandex_status": "yandex/provider-status",
    "interconnect": "yandex/cloud-interconnect",
    "yandex_asn": "yandex/as200350-overview",
    "bybit": "crypto/bybit-api-faq",
    "garantex": "crypto/garantex-doj",
    "grinex": "crypto/grinex-treasury",
    "exmo_closure": "crypto/exmo-me-closure",
    "exmo_split_fetch": "crypto/exmo-com-split",
    "abcex_docs": "crypto/abcex-api",
    "abcex_api": "crypto/abcex-api-intro",
    "abcex_offices": "crypto/abcex-offices",
    "dns": "crypto/endpoint-dns",
    "abcex_route": "crypto/abcex-network-info",
    "exmo_route": "crypto/exmo-me-network-info",
    "abcex_registry": "crypto/abcex-rdap",
    "exmo_registry": "crypto/exmo-me-rdap",
    "servicepipe_asn": "crypto/as201706-overview",
    "ddos_guard_asn": "crypto/as57724-overview",
}
JSON_SOURCES = {
    "cdn_prefixes", "yandex_asn", "dns", "abcex_route", "exmo_route",
    "abcex_registry", "exmo_registry", "servicepipe_asn", "ddos_guard_asn",
}


def raw_path(key: str) -> Path:
    extension = "json" if key in JSON_SOURCES else "html"
    return REPO_ROOT / f"data/raw/{SOURCES[key]}.{TAG}.{extension}"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def document(key: str) -> BeautifulSoup:
    return BeautifulSoup(raw_path(key).read_text(encoding="utf-8"), "html.parser")


def yandex_body(key: str):
    return max(document(key).select(".yfm"), key=lambda element: len(element.get_text()))


def source_receipts() -> dict:
    receipts = {}
    for key in SOURCES:
        path = raw_path(key)
        metadata = read_json(path.with_name(path.name + ".provenance.json"))
        assert metadata["sha256"] == sha256(path), key
        assert metadata["raw_source_ref"] == str(path.relative_to(REPO_ROOT)), key
        receipts[key] = metadata
    return receipts


def baseline_profile() -> dict:
    manifest = read_json(REPO_ROOT / f"data/manifest.{TAG}.json")
    layers, all_rows = [], []
    for layer in manifest["layers"]:
        path = REPO_ROOT / layer["files"]["geojson"]["path"]
        assert layer["files"]["geojson"]["sha256"] == sha256(path)
        rows = [feature for feature in read_json(path)["features"]
                if feature["properties"]["country_code"] == "RU"]
        if not rows:
            continue
        all_rows.extend(rows)
        layers.append({
            "layer": layer["layer"], "source": layer["files"]["geojson"],
            "record_count": len(rows), "snapshot_tag": layer["snapshot_tag"],
            "entity_types": dict(Counter(row["properties"]["entity_type"] for row in rows)),
            "geometry_null": sum(row["geometry"] is None for row in rows),
        })
    identifiers = [row["properties"]["record_id"] for row in all_rows]
    assert len(identifiers) == len(set(identifiers)), "RU record IDs must be unique across canonical layers"
    old_view = next(view for view in manifest["views"] if view["layer"] == "russia/locations-and-observations")
    return {
        "manifest_ref": f"data/manifest.{TAG}.json", "filter": {"country_code": "RU"},
        "canonical_location_record_count": manifest["record_count"],
        "ru_record_count": len(all_rows), "layers": layers,
        "duplicate_record_ids": len(identifiers) - len(set(identifiers)),
        "geometry_null": sum(row["geometry"] is None for row in all_rows),
        "retained_country_view": {"source": old_view["files"]["geojson"],
                                  "record_count": old_view["record_count"],
                                  "snapshot_tag": old_view["snapshot_tag"]},
        "limit": "Mixed units and source ages; neither a current operational inventory nor a facility count. The older RU view omits the newly restored 2023 Akamai city records.",
    }


def yandex_review() -> dict:
    zones = sorted(set(re.findall(r"ru-central1-[a-z]", yandex_body("zones").get_text())))
    region_codes = set(re.findall(r"(?:ru-central1-[a-z]|kz1-[a-z])", yandex_body("regions").get_text()))
    assert set(zones) <= region_codes and "kz1-a" in region_codes
    prefixes = {}
    for table in yandex_body("public_ips").select("table"):
        heading = table.find_previous(["h2", "h3", "h4"])["id"]
        # Single addresses are represented as /32 or /128 only in this candidate
        # assessment; their service roles remain distinct from customer pools.
        prefixes[heading] = [str(ipaddress.ip_network(code.get_text(strip=True), strict=True))
                             for code in table.select("code")]
    cdn_prefixes = read_json(raw_path("cdn_prefixes"))["prefixes"]
    nets = [ipaddress.ip_network(prefix, strict=True) for prefix in cdn_prefixes]
    assert len(nets) == len(set(nets)), "Duplicate CDN prefixes"
    tables = yandex_body("cdn_cities").select("table")
    cities = {}
    city_rows = tables[1].select("tr")
    assert [cell.get_text(strip=True) for cell in city_rows[0].select("td")] == ["Country", "Cities"]
    for row in city_rows[1:]:
        country, cell = row.select("td")
        cities[country.get_text(strip=True)] = [city.strip() for city in cell.get_text().split("•") if city.strip()]
    assert all(len(names) == len(set(names)) for names in cities.values())
    status = document("yandex_status").get_text(" ", strip=True)
    assert "11.10.2026" in status and "Сасово" in status and "Владимире" in status
    asn = read_json(raw_path("yandex_asn"))["data"]
    assert "200350" in yandex_body("interconnect").get_text() and asn["resource"] == "200350"
    comparison_path = REPO_ROOT / f"data/observations/cdn-asn-comparison.{TAG}.json"
    comparison = read_json(comparison_path)
    matching = [row for row in comparison["records"] if row["asn"] == 200350]
    assert len(matching) == 1
    return {
        "certified_localities_ref": "data/yandex/data-centers.20261011.geojson",
        "cloud_zone_candidates": [
            {"zone_id": zone, "source_country_code": "RU", "facility_record_id": None,
             "service_scope": "baremetal" if zone.endswith("-m") else "public_cloud",
             "current_health_verified": False} for zone in zones
        ],
        "separate_kazakhstan_zones": sorted(region_codes - set(zones)),
        "cloud_zone_source_keys": ["zones", "regions"],
        "status_review": {
            "source_key": "yandex_status", "report_updated_at": "2026-10-11",
            "reported_statuses": {"Sasovo": "stopped", "Vladimir": "stopped", "Kaluga": "partially_disrupted"},
            "current_recovery_verified": False,
            "limit": "The retrieved statement is still dated October 11; absence of a later update establishes neither continued outage nor recovery. Do not infer permanent retirement or zone-to-building mappings.",
        },
        "cdn": {
            "source_keys": ["cdn_cities", "cdn_prefixes"],
            "provider_global_pop_claim": int(tables[0].select("tr")[-1].select("td")[0].get_text(strip=True)),
            "city_count": sum(map(len, cities.values())),
            "source_country_labels": cities,
            "source_russia_label_city_count": len(cities["Russia"]),
            "country_review_required": [{"city": "Simferopol", "source_country_label": "Russia",
                                          "normalized_country_code": None,
                                          "reason": "Disputed territorial attribution; preserve the source label and review country normalization before any RU view inclusion."}],
            "prefix_count": len(nets), "ip_families": dict(Counter(str(net.version) for net in nets)),
            "duplicate_prefixes": 0,
            "overlapping_prefix_pairs": [[str(a), str(b)] for i, a in enumerate(nets) for b in nets[i + 1:]
                                         if a.version == b.version and a.overlaps(b)],
            "prefix_geography_provided": False,
            "prefix_to_city_mapping_provided": False,
            "limit": "City declarations, global PoP totals and service prefixes cannot be added or joined one-to-one; overlapping prefixes are valid declarations, not extra capacity.",
        },
        "public_ip_candidates": {"source_key": "public_ips", "prefixes_by_service": prefixes,
                                 "counts_by_service": {key: len(value) for key, value in prefixes.items()},
                                 "physical_country_code": None},
        "asn": {"number": 200350, "holder": asn["holder"], "source_keys": ["interconnect", "yandex_asn"]},
        "existing_cdn_observations": {
            "comparison_source": {"path": str(comparison_path.relative_to(REPO_ROOT)), "sha256": sha256(comparison_path)},
            "asn": 200350, "source_study_month": "2026-06",
            "provider_record_ids": {key: value for key, value in matching[0]["provider_record_ids"].items() if value},
            "physical_country_code": None,
            "limit": "ASN-level TLS associations do not identify a city, cache count, Apple-owned infrastructure, current operation, or a crypto-exchange customer.",
        },
    }


def dns_review(yandex: dict) -> dict:
    queries = read_json(raw_path("dns"))["records"]
    query_keys = [(query["hostname"], query["rrtype"]) for query in queries]
    assert len(query_keys) == len(set(query_keys)), "Duplicate hostname/type queries"
    pools = dict(yandex["public_ip_candidates"]["prefixes_by_service"])
    pools["cloud_cdn"] = read_json(raw_path("cdn_prefixes"))["prefixes"]
    networks = [(service, ipaddress.ip_network(prefix)) for service, prefixes in pools.items() for prefix in prefixes]
    endpoints = []
    routes = {"abcex.io": ("abcex_route", "abcex_registry", "servicepipe_asn"),
              "hub.abcex.io": ("abcex_route", "abcex_registry", "servicepipe_asn"),
              "exmo.me": ("exmo_route", "exmo_registry", "ddos_guard_asn")}
    for host in sorted({query["hostname"] for query in queries}):
        rows = [query for query in queries if query["hostname"] == host]
        addresses = sorted({answer["data"] for query in rows for answer in query.get("response", {}).get("Answer", [])
                            if answer["type"] in (1, 28)})
        aliases = sorted({answer["data"] for query in rows for answer in query.get("response", {}).get("Answer", [])
                          if answer["type"] == 5})
        matches = [{"address": address, "service": service, "prefix": str(network)}
                   for address in addresses for service, network in networks
                   if ipaddress.ip_address(address).version == network.version and ipaddress.ip_address(address) in network]
        attribution = None
        if host in routes:
            route_key, registry_key, asn_key = routes[host]
            route = read_json(raw_path(route_key))["data"]
            registry = read_json(raw_path(registry_key))
            overview = read_json(raw_path(asn_key))["data"]
            assert overview["resource"] in route["asns"]
            assert any(ipaddress.ip_address(address) in ipaddress.ip_network(route["prefix"])
                       for address in addresses if ipaddress.ip_address(address).version == 4)
            attribution = {"source_keys": list(routes[host]), "routing_prefix": route["prefix"],
                           "origin_asns": [int(asn) for asn in route["asns"]], "asn_holder": overview["holder"],
                           "registry_network_name": registry["name"], "registry_country_code": registry["country"],
                           "physical_country_code": None}
        endpoints.append({"hostname": host, "endpoint_role": rows[0]["endpoint_role"],
                          "addresses": addresses, "cnames": aliases,
                          "query_times": [query["queried_at"] for query in rows],
                          "query_statuses": {query["rrtype"]: query.get("response", {}).get("Status") for query in rows},
                          "yandex_published_prefix_matches": matches, "network_attribution": attribution,
                          "origin_country_code": None, "facility_record_id": None})
    return {
        "source_key": "dns", "query_count": len(queries), "hostname_count": len(endpoints),
        "query_errors": sum("error" in query for query in queries),
        "nonzero_dns_status_count": sum(query.get("response", {}).get("Status") not in (0, None) for query in queries),
        "endpoints": endpoints,
        "yandex_matched_endpoint_count": sum(bool(endpoint["yandex_published_prefix_matches"]) for endpoint in endpoints),
        "limit": "One resolver, A/AAAA/CNAME only, no explicit ECS or located probe. Empty NOERROR answers are not NXDOMAIN. Network registration is not physical hosting; a CDN or protection endpoint can hide origins. No match against these Yandex feeds does not exclude other Yandex dependencies.",
    }


def crypto_review() -> list[dict]:
    bybit = document("bybit").get_text(" ", strip=True)
    assert "AWS Singapore" in bybit and "apse1-az2" in bybit and "az3" in bybit
    assert "hub.abcex.io" in document("abcex_api").get_text()
    assert "ликвидации" in document("exmo_closure").get_text()
    reviews = [
        {"entity": "ABCEX", "source_keys": ["abcex_docs", "abcex_api", "abcex_offices"],
         "finding": "Provider documents Russian cash offices and a public WebSocket endpoint; these identify business presence and an endpoint, not compute facilities.",
         "admission": "DNS/routing candidate only; origin and site identity remain unknown."},
        {"entity": "Bybit", "source_keys": ["bybit"],
         "provider_declared_server_country_code": "SG", "provider_declared_cloud": "AWS",
         "provider_declared_az_ids": ["apse1-az2", "apse1-az3"],
         "finding": "The operator API FAQ declares Singapore hosting; observed production API CNAMEs point to CloudFront names.",
         "admission": "Use as a non-RU comparison and customer/cloud relationship, not as a new owned facility."},
        {"entity": "EXMO.me", "source_keys": ["exmo_closure"], "status_report_date": "2026-07-24",
         "finding": "Operator announced termination and liquidation. Continued website DNS answers do not establish active trading or recovered service.",
         "admission": "Dated service-status and endpoint evidence; apply only to EXMO.me, not similarly named entities."},
        {"entity": "Garantex", "source_keys": ["garantex", "grinex"],
         "finding": "DOJ reports March 2025 domain seizures and server seizures by German and Finnish authorities; Treasury describes Russian operations. Neither establishes current Russian physical hosting.",
         "admission": "Historical event and attributed entity evidence only. Keep law-enforcement jurisdiction separate from server geography."},
        {"entity": "Grinex", "source_keys": ["grinex"],
         "finding": "Treasury's August 2025 release describes a successor relationship to Garantex. Current domain-to-operator identity and hosting were not established in this review.",
         "admission": "Re-verify operator/domain identity before collecting endpoints; do not inherit Garantex locations."},
    ]
    for review in reviews:
        review["confirmed_current_ru_hosting"] = None
        review["facility_record_id"] = None
    return reviews


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    yandex = yandex_review()
    assessment = {
        "assessment_type": "russia_yandex_crypto_enrichment", "assessed_at": DATE,
        "scope": "RU infrastructure coverage with Yandex and a bounded five-exchange cohort; not a market census.",
        "excluded_from_canonical_totals": True, "new_canonical_records": 0,
        "sources": source_receipts(), "baseline": baseline_profile(), "yandex": yandex,
        "crypto_exchanges": crypto_review(), "dns_pilot": dns_review(yandex),
        "source_access_gaps": [
            {"source_url": "https://grinex.io/", "status": "HTTP 403 in raw fetch; web reader returned a journal title",
             "impact": "No reliable current exchange-domain identity or operating-status inference."},
            {"source_key": "exmo_split_fetch", "status": "HTTP 200 soft 404 in raw fetch; web reader returned an older article",
             "impact": "Excluded from structured identity/hosting assertions."},
        ],
        "enrichment_options": [
            {"priority": 1, "candidate": "Yandex cloud region/zone hierarchy",
             "target": "location layer with region and availability_zone units",
             "gate": "Separate four public-cloud zones from BareMetal and Kazakhstan; keep facility joins null; document age and current-health limits."},
            {"priority": 1, "candidate": "Yandex CDN city declarations",
             "target": "city-level edge declarations",
             "gate": "Resolve Simferopol country normalization; retain global PoP claim separately; no city-to-prefix join or exact site inference."},
            {"priority": 1, "candidate": "Yandex service-prefix feeds and ASN routing",
             "target": "existing network-evidence provider_prefix/routing_origin types",
             "gate": "Keep VPC, BareMetal, CDN and supporting services distinct; preserve overlaps; country null without geographic evidence."},
            {"priority": 1, "candidate": "Exchange identities, service status and DNS endpoints",
             "target": "separate application-endpoint evidence contract",
             "gate": "Store entity ID, endpoint role, exact DNS response/time/resolver, routing and registry evidence; CDN/protection and origin attribution must be separate. Do not place exchanges in the facility inventory."},
            {"priority": 2, "candidate": "RIPE June 2026 ASN registration join for CDN observations",
             "target": "separate registration-filtered comparison view",
             "gate": "Match source-study date and allocated/assigned ASN intervals, as for APNIC; registration country must not populate physical country."},
            {"priority": 2, "candidate": "Other domestic providers",
             "target": "Selectel hierarchy, Cloud.ru product hierarchies, IXcellerate lifecycle directory",
             "gate": "Use the October 11 assessment as a lead; re-fetch before normalization. Not revalidated in this focused review."},
        ],
    }
    output = args.output_root / f"data/russia/enrichment-assessment.{TAG}.json"
    write_json(output, assessment)
    print(json.dumps({"ru_records": assessment["baseline"]["ru_record_count"],
                      "yandex_zones": len(yandex["cloud_zone_candidates"]),
                      "yandex_cdn_cities": yandex["cdn"]["city_count"],
                      "yandex_cdn_prefixes": yandex["cdn"]["prefix_count"],
                      "exchange_count": len(assessment["crypto_exchanges"]),
                      "dns_queries": assessment["dns_pilot"]["query_count"],
                      "new_canonical_records": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
