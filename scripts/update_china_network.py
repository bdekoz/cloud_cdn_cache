#!/usr/bin/env python3
"""Normalize retained public endpoint observations and bounded registry joins."""

from __future__ import annotations

import argparse
import ipaddress
import json
from collections import Counter
from pathlib import Path

from china_enrichment_common import DATE, TAG, source
from location_common import REPO_ROOT, slug
from network_common import canonical_network_record, write_network_layer


def raw(key):
    return json.loads((REPO_ROOT / source(key)["path"]).read_text())["records"]


def record(key, identifier, kind, subject_type, subject_id, provider, observed_at, *,
           source_url=None, prefix=None, asn=None, relationship=None, object_type=None, object_id=None,
           status="observed", scope="observed", properties=None):
    info = source(key)
    return canonical_network_record(
        record_id=f"network:china-vendor-evidence:{identifier}", evidence_type=kind,
        subject_type=subject_type, subject_id=subject_id, provider=provider,
        service="china_vendor_network_evidence", prefix=prefix,
        ip_family=ipaddress.ip_network(prefix).version if prefix else None, asn=asn,
        relationship_type=relationship, object_type=object_type, object_id=object_id,
        status=status, source_scope=scope, source_url=source_url or info["source_url"],
        raw_source_ref=info["path"], source_sha256=info["sha256"], source_published_at=None,
        retrieved_at=DATE, observed_at=observed_at, valid_from=None, valid_to=None,
        confidence="high", properties=properties or {},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    checks, routes, registry = raw("endpoint-observations"), raw("endpoint-routing"), raw("endpoint-peeringdb")
    registrations = {row["asn"]: row for row in raw("endpoint-rdap") if row["result"] == "retrieved"}
    rows = [record("endpoint-observations", "run", "measurement_run", "measurement", "china-public-endpoints-" + TAG,
        None, min(c["observed_at"] for c in checks), properties={
            "target_count": len(checks), "maximum_target_count": 24,
            "methods": ["system_dns", "verified_tls", "http_head_root"], "port": 443,
            "credentials_or_generation_requests_used": False, "private_addresses_contacted": False,
            "vantage_geography": "not_established", "single_vantage_not_global_availability": True,
            "retrieval_date_timezone": "America/Los_Angeles", "observed_at_timezone": "UTC"})]
    ip_context = {}
    for check in checks:
        if "connected_ip" in check:
            ip_context.setdefault(check["connected_ip"], []).append(check["provider"])
        rows.append(record("endpoint-observations", "endpoint-" + slug(check["hostname"]), "reachability_observation",
            "measurement", check["hostname"], check["provider"], check["observed_at"],
            source_url="https://" + check["hostname"] + "/", status=check["status"],
            object_type="provider_service", object_id=check["endpoint_record_ids"][0],
            properties={**check, "dns_ip_tls_and_http_status_are_not_compute_geography": True,
                        "timing_scope": "Combined DNS/TCP/TLS/context setup elapsed time; not network RTT or inference latency",
                        "authentication_error_or_head_rejection_is_not_service_closure": True}))
    net_map = {}
    for item in registry:
        if item.get("asn") and item["result"] == "retrieved":
            for net in item["response"].get("data", []):
                net_map[net["id"]] = net
    asn_map = {obj["asn"]: obj for obj in net_map.values()}
    for route in routes:
        if route["result"] != "retrieved":
            continue
        data = route["response"].get("data", {})
        prefix = data.get("prefix")
        for asn in data.get("asns", []):
            asn = int(asn)
            if asn <= 0 or not prefix:
                continue
            props = {"sampled_endpoint_ip": route["ip_address"],
                     "endpoint_provider_context": sorted(set(ip_context.get(route["ip_address"], []))),
                     "endpoint_context_does_not_establish_asn_ownership": True,
                     "api_frontend_origin_does_not_establish_training_or_inference_host": True}
            if asn in registrations:
                info = source("endpoint-rdap")
                props["asn_registration"] = {"facts": registrations[asn]["facts"],
                    "source_url": registrations[asn]["source_url"], "raw_source_ref": info["path"],
                    "source_sha256": info["sha256"], "observed_at": registrations[asn]["observed_at"],
                    "registered_country_is_not_hosting_country": True}
            if asn in asn_map:
                info = source("endpoint-peeringdb")
                props["provider_name_source"] = {"source_url": f"https://www.peeringdb.com/api/net?asn={asn}",
                    "raw_source_ref": info["path"], "source_sha256": info["sha256"],
                    "role": "registry_network_display_name_not_model_provider_or_compute_owner"}
            rows.append(record("endpoint-routing", f"routing-{slug(route['ip_address'])}-as{asn}", "routing_origin",
                "prefix", prefix, asn_map.get(asn, {}).get("name"), route["observed_at"],
                source_url=route["source_url"], prefix=prefix, asn=asn, relationship="originates_prefix",
                object_type="asn", object_id=f"AS{asn}", status="announced",
                properties=props))
    for item in registry:
        if item.get("relationship_endpoint") not in {"netfac", "netixlan"} or item["result"] != "retrieved":
            continue
        net = net_map[item["network_id"]]
        facility = item["relationship_endpoint"] == "netfac"
        for obj in item["response"].get("data", []):
            target = str(obj["fac_id"] if facility else obj["ix_id"])
            rows.append(record("endpoint-peeringdb", f"{item['relationship_endpoint']}-{obj['id']}",
                "facility_registration" if facility else "ix_membership", "asn", f"AS{net['asn']}", net["name"], item["observed_at"],
                source_url=item["source_url"], asn=net["asn"], relationship="registered_at_facility" if facility else "present_at_ix",
                object_type="facility" if facility else "internet_exchange", object_id=target,
                status=obj.get("status", "registry_listed"), scope="registry", properties={
                    "network_id": item["network_id"], "network_name": net["name"],
                    "registry_relationship_id": obj["id"], "sample_limit_per_network_and_type": 2,
                    "facility_ownership_and_operational_presence_not_established": True,
                    "not_complete_network_inventory": True}))
    write_network_layer(records=rows, layer_name="china-vendor-evidence", retrieved_at=DATE,
        parser_name="update_china_network.py", output_root=args.output_root,
        extra_report={"target_count": len(checks), "target_bound": 24,
                      "tls_verified_count": sum(c["status"].startswith("tls_verified") for c in checks),
                      "routing_ip_sample_bound": 12, "asn_query_sample_bound": 10,
                      "reachability_status_counts": dict(Counter(c["status"] for c in checks)),
                      "failed_registry_queries": [{k: v for k, v in row.items() if k != "response"} for row in routes + registry if row["result"] != "retrieved"]})
    print(json.dumps({"record_count": len(rows), "evidence_types": dict(Counter(r["evidence_type"] for r in rows)), "tls_verified": len(checks)}))


if __name__ == "__main__":
    main()
