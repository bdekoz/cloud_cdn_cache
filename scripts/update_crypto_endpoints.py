#!/usr/bin/env python3
"""Build separate application evidence from retained public exchange endpoints."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import ipaddress
from pathlib import Path

from location_common import REPO_ROOT, load_validator, repo_ref, slug, write_json
from review_russia_enrichment import crypto_review
from russia_enrichment_common import DATE, TAG, evidence, raw_path, read, source
from update_cdn_comparisons import csv_ref
from update_yandex import network_rows

SCHEMA = REPO_ROOT / "schema/application-endpoint.schema.json"
PATH = f"data/applications/crypto-endpoints.{TAG}.json"
HOST_ENTITY = {"abcex.io": "abcex", "hub.abcex.io": "abcex", "api.bybit.com": "bybit",
               "stream.bybit.com": "bybit", "exmo.me": "exmo-me"}
NETWORK = {"abcex.io": ("abcex_route", "abcex_registry", "servicepipe_asn"),
           "hub.abcex.io": ("abcex_route", "abcex_registry", "servicepipe_asn"),
           "exmo.me": ("exmo_route", "exmo_registry", "ddos_guard_asn")}
RR_TYPES = {"A": 1, "AAAA": 28, "CNAME": 5}


def query_result(query):
    if query.get("error"):
        return "transport_error"
    response = query["response"]
    if response["Status"] == 3:
        return "nxdomain"
    if response["Status"] != 0:
        return "dns_error"
    return ("answered" if any(row["type"] == RR_TYPES[query["rrtype"]]
                              for row in response.get("Answer", [])) else "noerror_no_requested_rr")


def entities():
    result = []
    for review in crypto_review():
        name = review["entity"]
        declared = None
        if "provider_declared_server_country_code" in review:
            declared = {"country_code": review["provider_declared_server_country_code"],
                        "cloud_provider": review["provider_declared_cloud"],
                        "availability_zone_ids": review["provider_declared_az_ids"], "source": evidence("bybit"),
                        "endpoint_to_zone_mapping_asserted": False}
        status, date = {"EXMO.me": ("termination_announced", "2026-07-24"),
                        "Garantex": ("historical_seizure_reported", "2025-03-07")}.get(name, ("unverified", None))
        result.append({"entity_id": f"application:entity:{slug(name)}", "name": name,
                       "assessment": review["finding"], "admission": review["admission"],
                       "sources": [evidence(key) for key in review["source_keys"]],
                       "provider_declared_hosting": declared, "origin_country_code": None,
                       "facility_record_id": None, "service_status": {"status": status,
                           "reported_at": date, "current_operation_verified": False}})
    return sorted(result, key=lambda row: row["entity_id"])


def address_attribution(host, address):
    if host not in NETWORK:
        return None
    route_key, registry_key, asn_key = NETWORK[host]
    for key in NETWORK[host]:
        source(key)
    response, registry, asn = read(raw_path(route_key)), read(raw_path(registry_key)), read(raw_path(asn_key))["data"]
    route, ip = response["data"], ipaddress.ip_address(address)
    net = ipaddress.ip_network(route["prefix"])
    if ip.version != net.version or ip not in net:
        return None
    start, end = ipaddress.ip_address(registry["startAddress"]), ipaddress.ip_address(registry["endAddress"])
    if not start <= ip <= end or asn["resource"] not in route["asns"]:
        raise ValueError("Registry/routing attribution does not contain the observed address")
    return {"routing_prefix": route["prefix"], "origin_asns": [int(a) for a in route["asns"]],
            "asn_holder": asn["holder"], "observed_at": response["time"] + "Z",
            "registry_network_name": registry["name"], "registry_country_code": registry["country"],
            "registry_start_address": str(start), "registry_end_address": str(end),
            "routing_evidence": evidence(route_key), "registry_evidence": evidence(registry_key),
            "asn_identity_evidence": evidence(asn_key), "physical_country_code": None}


def collection():
    source("dns")
    prefixes, _ = network_rows()
    rows = []
    for index, query in enumerate(read(raw_path("dns"))["records"]):
        host, role, observed, rrtype = (query[k] for k in ("hostname", "endpoint_role", "queried_at", "rrtype"))
        entity_id = "application:entity:" + HOST_ENTITY[host]
        identity = "|".join((entity_id, host, role, observed, rrtype))
        response = query.get("response")
        answers = response.get("Answer", []) if response else []
        addresses = []
        for address in sorted({a["data"] for a in answers if a["type"] in (1, 28)}):
            ip = ipaddress.ip_address(address)
            matches = [{"network_record_id": row["record_id"], "service": row["service"], "prefix": row["prefix"],
                        "snapshot_ref": f"data/network/yandex-prefixes.{TAG}.json"}
                       for row in prefixes if row["ip_family"] == ip.version and ip in ipaddress.ip_network(row["prefix"])]
            addresses.append({"address": address, "ip_family": ip.version,
                              "network_attribution": address_attribution(host, address), "published_prefix_matches": matches})
        rows.append({"record_id": "application:dns:" + hashlib.sha256(identity.encode()).hexdigest()[:24],
                     "entity_id": entity_id, "hostname": host, "endpoint_role": role,
                     "observed_at": observed, "resolver_url": query["resolver_url"],
                     "measurement_vantage_country_code": None, "ecs_sent": False, "rrtype": rrtype,
                     "query_result": query_result(query), "dns_response": response,
                     "source_scope": "observed", "confidence": "high",
                     "transport_error": query.get("error"), "address_observations": addresses,
                     "cnames": sorted({a["data"] for a in answers if a["type"] == 5}),
                     "origin_country_code": None, "facility_record_id": None, "origin_evidence": [],
                     "source": evidence("dns"), "source_json_pointer": f"/records/{index}"})
    value = {"type": "ApplicationEndpointCollection", "schema_version": "1.0.0", "built_at": DATE,
             "excluded_from_location_and_network_totals": True, "endpoint_is_not_origin": True,
             "entities": entities(), "records": sorted(rows, key=lambda row: row["record_id"])}
    validate(value)
    return value


def validate(value):
    load_validator(SCHEMA).validate(value)
    entity_ids = [entity["entity_id"] for entity in value["entities"]]
    ids, keys = set(), set()
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("Duplicate application entity IDs")
    for row in value["records"]:
        key = tuple(row[k] for k in ("entity_id", "hostname", "endpoint_role", "observed_at", "rrtype"))
        if row["record_id"] in ids or key in keys or row["entity_id"] not in entity_ids:
            raise ValueError("Duplicate query identity or unresolved entity")
        ids.add(row["record_id"])
        keys.add(key)
        response = row["dns_response"]
        if response and response["Question"] != [{"name": row["hostname"] + ".", "type": RR_TYPES[row["rrtype"]]}]:
            raise ValueError("DNS question does not match endpoint query")
        expected = query_result({"rrtype": row["rrtype"], "response": response, "error": row["transport_error"]})
        if row["query_result"] != expected:
            raise ValueError("DNS status classification disagrees with response")


def run(root: Path):
    value = collection()
    write_json(root / PATH, value)
    write_json((root / PATH).with_suffix(".report.json"), {
        "layer": "applications/crypto-endpoints", "built_at": DATE, "parser": "update_crypto_endpoints.py",
        "schema": repo_ref(SCHEMA), "schema_version": "1.0.0", "record_count": len(value["records"]),
        "record_unit": "entity_hostname_role_timestamp_rrtype", "entity_count": len(value["entities"]),
        "hostname_count": len({row["hostname"] for row in value["records"]}),
        "query_results": dict(sorted(Counter(row["query_result"] for row in value["records"]).items())),
        "excluded_from_location_and_network_totals": True,
        "origin_attributed_record_count": sum(row["origin_country_code"] is not None for row in value["records"]),
        "source_method": read(raw_path("dns"))["method"], "prefix_match_scope": "retained Yandex published service feeds only",
        "limitations": ["Single public resolver without a located probe or explicit ECS.",
                        "Registry country, CDN/protection endpoints and business offices do not locate physical origins.",
                        "Reachable DNS does not establish active trading. Grinex has no verified current endpoint in this cohort.",
                        "No Yandex feed match does not exclude other Yandex dependencies."],
        "generated_files": [PATH], "derived_files": csv_ref(PATH)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    run(parser.parse_args().output_root)
