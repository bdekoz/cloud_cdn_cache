#!/usr/bin/env python3
"""Fetch a bounded PeeringDB facility/IX relationship pilot for routed provider ASNs."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, repo_ref, retrieval_tag, sha256, slug, write_json, write_provenance
from network_common import NETWORK_SCHEMA_PATH, canonical_network_record, write_network_layer


API_BASE = "https://www.peeringdb.com/api"
USER_AGENT = "cloud-cdn-cache-data-refresh/1.0 (+https://github.com/stevesong/cloud_cdn_cache)"
PAGE_SIZE = 250

TARGETS = {
    8075: {"provider": "Microsoft", "service": "microsoft_network"},
    15169: {"provider": "Google", "service": "google_network"},
    16509: {"provider": "Amazon Web Services", "service": "aws_network"},
    396982: {"provider": "Google Cloud", "service": "google_cloud_network"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=NETWORK_SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def raw_path(retrieved_at: str) -> Path:
    return REPO_ROOT / "data/raw/network/peeringdb" / f"provider-relationships-pilot.{retrieval_tag(retrieved_at)}.json"


def api_url(resource: str, **parameters: str | int) -> str:
    return f"{API_BASE}/{resource}?{urllib.parse.urlencode(parameters)}"


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_pages(resource: str, **parameters: str | int) -> list[dict[str, Any]]:
    pages = []
    skip = 0
    for _ in range(20):
        url = api_url(resource, **parameters, limit=PAGE_SIZE, skip=skip, depth=0)
        response = fetch_json(url)
        data = response.get("data") or []
        pages.append({"request_url": url, "response": response})
        if len(data) < PAGE_SIZE:
            return pages
        skip += PAGE_SIZE
    raise ValueError(f"PeeringDB pagination exceeded safety bound for {resource}")


def fetch_bundle(output: Path, retrieved_at: str) -> None:
    asn_list = ",".join(str(asn) for asn in sorted(TARGETS))
    net_url = api_url("net", asn__in=asn_list, depth=0)
    net_response = fetch_json(net_url)
    networks = net_response.get("data") or []
    returned_asns = {int(network["asn"]) for network in networks}
    if returned_asns != set(TARGETS):
        raise ValueError(f"PeeringDB target mismatch: expected {sorted(TARGETS)}, got {sorted(returned_asns)}")
    net_ids = ",".join(str(network["id"]) for network in sorted(networks, key=lambda item: item["id"]))
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    write_json(output, {
        "aup_url": "https://www.peeringdb.com/aup",
        "net": {"request_url": net_url, "response": net_response},
        "netfac_pages": fetch_pages("netfac", net_id__in=net_ids),
        "netixlan_pages": fetch_pages("netixlan", net_id__in=net_ids),
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "scope": "Bounded research pilot for origin ASNs found in the 2026-08-05 RIPEstat prefix sample.",
        "target_asns": sorted(TARGETS),
    })


def page_records(bundle: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [record for page in bundle[key] for record in page["response"].get("data") or []]


def build_records(path: Path, retrieved_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    networks = bundle["net"]["response"].get("data") or []
    networks_by_id = {int(network["id"]): network for network in networks}
    raw_digest = sha256(path)
    observed_at = bundle["observed_at"]
    records: list[dict[str, Any]] = []

    for relation in page_records(bundle, "netfac_pages"):
        network = networks_by_id.get(int(relation["net_id"]))
        if not network:
            raise ValueError(f"netfac {relation['id']} references an unrequested network")
        asn = int(network["asn"])
        target = TARGETS.get(asn)
        if not target:
            raise ValueError(f"unexpected ASN in netfac: {asn}")
        records.append(canonical_network_record(
            record_id=f"network:facility_registration:peeringdb-{int(relation['id'])}",
            evidence_type="facility_registration",
            subject_type="asn",
            subject_id=f"AS{asn}",
            provider=target["provider"],
            service=target["service"],
            prefix=None,
            ip_family=None,
            asn=asn,
            relationship_type="registered_at_facility",
            object_type="facility",
            object_id=f"peeringdb:facility:{int(relation['fac_id'])}",
            status="registered" if relation.get("status") == "ok" else "inactive",
            source_scope="registry",
            source_url=f"{API_BASE}/netfac",
            raw_source_ref=repo_ref(path),
            source_sha256=raw_digest,
            source_published_at=None,
            retrieved_at=retrieved_at,
            observed_at=observed_at,
            valid_from=relation.get("created"),
            valid_to=None,
            confidence="medium",
            properties={
                "city": relation.get("city"),
                "country_code": relation.get("country"),
                "facility_name": relation.get("name"),
                "local_asn": relation.get("local_asn"),
                "network_name": network.get("name"),
                "peeringdb_facility_id": int(relation["fac_id"]),
                "peeringdb_net_id": int(relation["net_id"]),
                "peeringdb_relationship_id": int(relation["id"]),
                "registration_not_cdn_presence": True,
                "registration_not_provider_ownership": True,
                "source_record_url": f"{API_BASE}/netfac/{int(relation['id'])}",
                "relationship_updated_at": relation.get("updated"),
            },
        ))

    for relation in page_records(bundle, "netixlan_pages"):
        network = networks_by_id.get(int(relation["net_id"]))
        if not network:
            raise ValueError(f"netixlan {relation['id']} references an unrequested network")
        asn = int(network["asn"])
        target = TARGETS.get(asn)
        if not target:
            raise ValueError(f"unexpected ASN in netixlan: {asn}")
        records.append(canonical_network_record(
            record_id=f"network:ix_membership:peeringdb-{int(relation['id'])}",
            evidence_type="ix_membership",
            subject_type="asn",
            subject_id=f"AS{asn}",
            provider=target["provider"],
            service=target["service"],
            prefix=None,
            ip_family=None,
            asn=asn,
            relationship_type="present_at_ix",
            object_type="internet_exchange",
            object_id=f"peeringdb:ix:{int(relation['ix_id'])}",
            status="operational" if relation.get("status") == "ok" and relation.get("operational") else "not_operational",
            source_scope="registry",
            source_url=f"{API_BASE}/netixlan",
            raw_source_ref=repo_ref(path),
            source_sha256=raw_digest,
            source_published_at=None,
            retrieved_at=retrieved_at,
            observed_at=observed_at,
            valid_from=relation.get("created"),
            valid_to=None,
            confidence="medium",
            properties={
                "bfd_support": relation.get("bfd_support"),
                "ipaddr4": relation.get("ipaddr4"),
                "ipaddr6": relation.get("ipaddr6"),
                "is_rs_peer": relation.get("is_rs_peer"),
                "ix_name": relation.get("name"),
                "ixlan_id": relation.get("ixlan_id"),
                "network_name": network.get("name"),
                "operational": relation.get("operational"),
                "peeringdb_ix_id": int(relation["ix_id"]),
                "peeringdb_net_id": int(relation["net_id"]),
                "peeringdb_relationship_id": int(relation["id"]),
                "registration_not_cdn_presence": True,
                "registration_not_provider_ownership": True,
                "source_record_url": f"{API_BASE}/netixlan/{int(relation['id'])}",
                "relationship_updated_at": relation.get("updated"),
                "speed_mbps": relation.get("speed"),
            },
        ))

    relationship_counts = Counter(record["evidence_type"] for record in records)
    asn_counts = Counter(f"AS{record['asn']}" for record in records)
    return records, {
        "aup_status": "PeeringDB AUP applies. This is a bounded operational-research pilot; review permission before bulk reuse or redistribution.",
        "aup_url": bundle["aup_url"],
        "network_count": len(networks),
        "relationship_counts": dict(sorted(relationship_counts.items())),
        "relationship_counts_by_asn": dict(sorted(asn_counts.items())),
        "scope": bundle["scope"],
        "target_asns": bundle["target_asns"],
    }


def main() -> None:
    args = parse_args()
    path = raw_path(args.retrieved_at)
    if args.fetch:
        path.parent.mkdir(parents=True, exist_ok=True)
        fetch_bundle(path, args.retrieved_at)
    if not path.exists():
        raise FileNotFoundError(path)
    write_provenance(
        path,
        source_url=f"{API_BASE}/",
        retrieved_at=args.retrieved_at,
        media_type="application/json",
        source_published_at=None,
        notes="Bounded PeeringDB research snapshot for four sampled provider origin ASNs. PeeringDB AUP applies; registered facility/IX relationships do not prove CDN presence or ownership.",
    )
    records, audit = build_records(path, args.retrieved_at)
    report = write_network_layer(
        records=records,
        layer_name="peeringdb-relationships",
        retrieved_at=args.retrieved_at,
        parser_name="update_peeringdb.py",
        output_root=args.output_root,
        schema_path=args.schema,
        extra_report=audit,
    )
    print(json.dumps({
        "record_count": report["record_count"],
        "relationship_counts": report["relationship_counts"],
        "relationship_counts_by_asn": report["relationship_counts_by_asn"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
