#!/usr/bin/env python3
"""Bounded DNS/TLS/HEAD checks and public routing/registration corroboration.

Targets come only from the retained documented AI endpoint layer. No credentials,
generation requests, broad port scans, private addresses or guessed targets.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import ipaddress
import json
import socket
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATE, TAG = "2026-10-11", "20261011"
FOLDER = ROOT / "data/raw/china-enrichment"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def query(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cloud-cdn-cache-source-review/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
        return {"source_url": url, "observed_at": now(), "result": "retrieved",
                "response_sha256": hashlib.sha256(raw).hexdigest(), "response": json.loads(raw)}
    except Exception as error:
        return {"source_url": url, "observed_at": now(), "result": "failed", "error": type(error).__name__ + ": " + str(error)}


def targets():
    path = ROOT / f"data/infrastructure/china-ai-services.{TAG}.json"
    collection = json.loads(path.read_text())
    hosts = {}
    for row in collection["records"]:
        if row["category"] != "ai_api_endpoint":
            continue
        props = row["properties"]
        url = props.get("base_url") or "https://" + (props.get("domain") or "")
        if "{" in url:
            continue
        host = urlparse(url).hostname
        if not host or not all(c.isalnum() or c in ".-" for c in host):
            continue
        hosts.setdefault(host, {"hostname": host, "provider": row["provider"], "endpoint_record_ids": [], "source_urls": []})
        hosts[host]["endpoint_record_ids"].append(row["record_id"])
        hosts[host]["source_urls"].append(row["source_url"])
    # Keep every direct model provider, four carrier pools, both BytePlus regions
    # and three public Model Studio domains; sample two Tencent API gateways.
    wanted_tencent = {"hunyuan.ai.tencentcloudapi.com", "hunyuan.tencentcloudapi.com"}
    selected = [v for h, v in hosts.items() if not h.endswith("tencentcloudapi.com") or h in wanted_tencent]
    if len(selected) > 24:
        raise ValueError(f"Target bound exceeded: {len(selected)}")
    return sorted(selected, key=lambda row: row["hostname"]), path


def observe(target):
    result = {**target, "observed_at": now(), "port": 443, "tls_verification_required": True,
              "http_method": "HEAD", "http_path": "/", "status": "unknown",
              "measurement_vantage_geography": "not_established", "ttl_not_observed": True}
    start = time.perf_counter()
    try:
        addresses = sorted({x[4][0] for x in socket.getaddrinfo(target["hostname"], 443, type=socket.SOCK_STREAM)})
        result["dns_addresses"] = addresses
        public = [a for a in addresses if ipaddress.ip_address(a).is_global]
        result["non_public_addresses_not_contacted"] = [a for a in addresses if a not in public]
        if not public:
            result["status"] = "non_public_resolution_not_contacted"
            return result
        address = next((a for a in public if ipaddress.ip_address(a).version == 4), public[0])
        result["connected_ip"] = address
        context = ssl.create_default_context()
        with socket.create_connection((address, 443), timeout=8) as tcp:
            with context.wrap_socket(tcp, server_hostname=target["hostname"]) as tls:
                result.update(status="tls_verified", tls_version=tls.version(),
                              certificate_sha256=hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest(),
                              certificate_not_after=tls.getpeercert().get("notAfter"),
                              connection_and_tls_ms=round((time.perf_counter() - start) * 1000, 3))
                request = f"HEAD / HTTP/1.1\r\nHost: {target['hostname']}\r\nUser-Agent: cloud-cdn-cache-data-check/1.0\r\nConnection: close\r\n\r\n"
                tls.sendall(request.encode("ascii"))
                response = tls.recv(1024).split(b"\r\n", 1)[0].decode("ascii", errors="replace")
                result["http_status_line"] = response
                result["http_response_does_not_establish_model_availability"] = True
    except Exception as error:
        result["status"] = "connection_check_failed" if result["status"] != "tls_verified" else "tls_verified_head_failed"
        result["error"] = type(error).__name__ + ": " + str(error)
    result["completed_at"] = now()
    return result


def retain(stem, rows, url, method):
    path = FOLDER / f"{stem}.{TAG}.json"
    if path.exists():
        raise ValueError(f"Refusing to overwrite immutable observations: {path}")
    payload = {"retrieved_at": DATE, "capture_method": method, "records": rows}
    dump(path, payload)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = {"source_url": url, "raw_source_ref": str(path.relative_to(ROOT)), "sha256": digest,
                  "retrieved_at": DATE, "source_published_at": None, "capture_method": method,
                  "notes": "Bounded public endpoint/routing/registration evidence. No inference calls, credentials or private-address connections. This does not establish hosting geography or facility ownership."}
    dump(path.with_suffix(".json.provenance.json"), provenance)
    return {"source_id": stem, "source_url": url, "path": provenance["raw_source_ref"], "sha256": digest,
            "retrieved_at": DATE, "source_published_at": None, "source_updated_at": None,
            "capture_method": method, "bytes": path.stat().st_size, "result": "retrieved"}


def main():
    selected, input_path = targets()
    if (FOLDER / f"endpoint-observations.{TAG}.json").exists():
        raise ValueError("Observations already captured; use offline normalization instead of repeating checks")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        observations = list(executor.map(observe, selected))
    public_ips = sorted({row["connected_ip"] for row in observations if "connected_ip" in row})[:12]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        routing = list(executor.map(lambda ip: {"ip_address": ip, **query("https://stat.ripe.net/data/network-info/data.json?" + urlencode({"resource": ip}))}, public_ips))
    asns = sorted({int(a) for row in routing if row["result"] == "retrieved" for a in row["response"].get("data", {}).get("asns", []) if int(a) > 0})[:10]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        registration = list(executor.map(lambda asn: {"asn": asn, **query(f"https://www.peeringdb.com/api/net?asn={asn}")}, asns))
    for row in registration:
        if row["result"] == "retrieved":
            # Retain only network metadata; personal contact fields are irrelevant.
            row["response"] = {"data": [{k: v for k, v in obj.items() if k in {"id", "asn", "name", "name_long", "website", "info_type", "irr_as_set", "updated", "status"}} for obj in row["response"].get("data", [])]}
    net_ids = sorted({obj["id"] for row in registration if row["result"] == "retrieved" for obj in row["response"].get("data", [])
                      if any(token in (obj.get("name", "") + obj.get("name_long", "")).lower() for token in ["alibaba", "tencent", "unicom", "telecom", "china mobile", "bilibili", "bytedance"])})[:5]
    relationships = []
    for net_id in net_ids:
        for endpoint in ["netfac", "netixlan"]:
            result = query(f"https://www.peeringdb.com/api/{endpoint}?net_id={net_id}")
            if result["result"] == "retrieved":
                result["response"] = {"data": result["response"].get("data", [])[:2]}
            relationships.append({"network_id": net_id, "relationship_endpoint": endpoint, "sample_limit": 2, **result})
    captures = [
        retain("endpoint-observations", observations, "urn:cloud-cdn-cache:endpoint-observations:20261011", "bounded_native_dns_tls_head"),
        retain("endpoint-routing", routing, "https://stat.ripe.net/data/network-info/data.json", "public_http_json_responses"),
        retain("endpoint-peeringdb", registration + relationships, "https://www.peeringdb.com/api/", "public_network_metadata_and_bounded_relationship_extracts"),
    ]
    catalog_path = FOLDER / f"catalog.{TAG}.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["sources"] = sorted(catalog["sources"] + captures, key=lambda row: row["source_id"])
    dump(catalog_path, catalog)
    print(json.dumps({"target_count": len(selected), "routing_ip_sample_count": len(public_ips), "asn_sample_count": len(asns),
                      "peeringdb_network_relationship_sample_count": len(relationships),
                      "tls_verified": sum(r["status"].startswith("tls_verified") for r in observations),
                      "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
