#!/usr/bin/env python3
"""Retain a bounded public RIPEstat sample for each Gulf region and Muscat border group."""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json

from capture_completion_review import ROOT, DATE, TAG
from location_common import REPO_ROOT, repo_ref, sha256, write_json
from update_network import fetch_ripestat_bundle


def selection():
    rows = json.loads((REPO_ROOT / f"data/network/gulf-provider-prefixes.{TAG}.json").read_text())["records"]
    groups = {}
    for row in rows:
        p = row["properties"]
        if row["provider"] == "Amazon Web Services" and p["provider_service_label"] != "AMAZON":
            continue
        key = (p["region_id"], p.get("network_border_group", p["region_id"]), row["ip_family"])
        groups.setdefault(key, []).append(row)
    return [min(groups[k], key=lambda r: (int(ipaddress.ip_network(r["prefix"]).network_address),
                                          ipaddress.ip_network(r["prefix"]).prefixlen, r["record_id"]))
            for k in sorted(groups)]


def main():
    path = ROOT / f"gulf-routing-sample.{TAG}.json"
    sidecar = path.with_suffix(".json.provenance.json")
    if path.exists():
        item = json.loads(sidecar.read_text())
        if sha256(path) != item["sha256"]:
            raise ValueError("Retained routing sample changed")
    else:
        rows = selection()
        print(f"Querying {len(rows)} declared-prefix samples; no active probes", flush=True)
        fetch_ripestat_bundle(prefix_records=rows, output=path, retrieved_at=DATE, sample_per_family=1)
        item = dict(source_id="gulf-routing-sample", source_url="https://stat.ripe.net/docs/data-api/api-endpoints/network-info",
                    title="Gulf prefix sample: RIPEstat routing origins and RPKI responses", publisher="RIPE NCC",
                    role="One IPv4 and IPv6 prefix per AWS/OCI Gulf region and available Muscat border-group family; one address per prefix. Routing evidence does not establish geography, latency or service health.",
                    source_published_at=None, source_updated_at=None, result="retrieved", path=repo_ref(path),
                    raw_source_ref=repo_ref(path), sha256=sha256(path), bytes=path.stat().st_size,
                    retrieved_at=DATE, captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    capture_method="api_response_bundle", query_count=len(rows))
        write_json(sidecar, item)
    catalog = ROOT / f"catalog.{TAG}.json"
    data = json.loads(catalog.read_text())
    sources = {r["source_id"]: r for r in data["sources"]}
    sources[item["source_id"]] = item
    data["sources"] = [sources[k] for k in sorted(sources)]
    write_json(catalog, data)
    print(f"Retained {item['query_count']} routing samples")


if __name__ == "__main__":
    main()
