#!/usr/bin/env python3
"""Fetch and normalize provider prefix feeds plus a sampled RIPEstat validation layer."""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, repo_ref, retrieval_tag, sha256, write_json, write_provenance
from network_common import (
    NETWORK_SCHEMA_PATH,
    canonical_network_record,
    write_network_layer,
)


AWS_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
GOOGLE_OWNED_URL = "https://www.gstatic.com/ipranges/goog.json"
GOOGLE_CLOUD_URL = "https://www.gstatic.com/ipranges/cloud.json"
AZURE_LANDING_URL = "https://www.microsoft.com/en-us/download/details.aspx?id=56519"
RIPESTAT_BASE = "https://stat.ripe.net/data"
SOURCEAPP = "cloud-cdn-cache"

USER_AGENT = "cloud-cdn-cache-data-refresh/1.0 (+https://github.com/stevesong/cloud_cdn_cache)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("all", "prefixes", "ripestat"), default="all")
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--sample-per-family", type=int, default=1)
    parser.add_argument("--schema", type=Path, default=NETWORK_SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def raw_paths(retrieved_at: str) -> dict[str, Path]:
    tag = retrieval_tag(retrieved_at)
    root = REPO_ROOT / "data/raw/network"
    return {
        "aws": root / "aws" / f"ip-ranges.{tag}.json",
        "google-owned": root / "google" / f"goog.{tag}.json",
        "google-cloud": root / "google" / f"cloud.{tag}.json",
        "azure-landing": root / "microsoft" / f"service-tags-download.{tag}.html",
        "azure": root / "microsoft" / f"service-tags-public.{tag}.json",
        "ripestat": root / "ripestat" / f"prefix-pilot.{tag}.json",
    }


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_to(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(fetch_bytes(url))


def azure_download_url(landing_path: Path) -> str:
    page = html.unescape(landing_path.read_text(encoding="utf-8"))
    match = re.search(
        r'https://download\.microsoft\.com/[^"<> ]+/ServiceTags_Public_[0-9]{8}\.json',
        page,
    )
    if not match:
        raise ValueError(f"Azure service-tag download URL not found in {landing_path}")
    return match.group(0)


def azure_published_date(landing_path: Path, download_url: str) -> str:
    page = landing_path.read_text(encoding="utf-8")
    match = re.search(r'"datePublished":"([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})', page)
    if match:
        return datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    version = re.search(r"ServiceTags_Public_([0-9]{8})\.json", download_url)
    if not version:
        raise ValueError("Azure service-tag date is unavailable")
    return datetime.strptime(version.group(1), "%Y%m%d").date().isoformat()


def utc_datetime(value: str) -> str:
    cleaned = value.strip()
    if cleaned.endswith("Z") or re.search(r"[+-][0-9]{2}:[0-9]{2}$", cleaned):
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    else:
        parsed = datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def aws_observed_at(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d-%H-%M-%S").replace(tzinfo=timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def record_key(*values: str) -> str:
    digest = hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()[:20]
    return digest


def normalized_prefix(value: str) -> tuple[str, int]:
    network = ipaddress.ip_network(value, strict=True)
    return str(network), network.version


def fetch_prefix_sources(paths: dict[str, Path]) -> None:
    fetch_to(AWS_URL, paths["aws"])
    fetch_to(GOOGLE_OWNED_URL, paths["google-owned"])
    fetch_to(GOOGLE_CLOUD_URL, paths["google-cloud"])
    fetch_to(AZURE_LANDING_URL, paths["azure-landing"])
    fetch_to(azure_download_url(paths["azure-landing"]), paths["azure"])


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prefix_record(
    *,
    provider: str,
    service: str,
    prefix: str,
    feed_scope: str,
    source_url: str,
    raw_path: Path,
    source_published_at: str,
    retrieved_at: str,
    observed_at: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    canonical_prefix, family = normalized_prefix(prefix)
    return canonical_network_record(
        record_id=f"network:provider_prefix:{record_key(feed_scope, canonical_prefix)}",
        evidence_type="provider_prefix",
        subject_type="prefix",
        subject_id=canonical_prefix,
        provider=provider,
        service=service,
        prefix=canonical_prefix,
        ip_family=family,
        asn=None,
        relationship_type="declares_prefix",
        object_type="provider_service",
        object_id=f"{service}:{feed_scope}",
        status="published",
        source_scope="provider_declared",
        source_url=source_url,
        raw_source_ref=repo_ref(raw_path),
        source_sha256=sha256(raw_path),
        source_published_at=source_published_at,
        retrieved_at=retrieved_at,
        observed_at=observed_at,
        valid_from=None,
        valid_to=None,
        confidence="high",
        properties={
            "feed_scope": feed_scope,
            "network_location_not_asserted": True,
            **properties,
        },
    )


def build_prefix_records(
    paths: dict[str, Path], retrieved_at: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    missing = [str(path) for key, path in paths.items() if key != "ripestat" and not path.exists()]
    if missing:
        raise FileNotFoundError("missing prefix source(s): " + ", ".join(missing))

    aws = load_json(paths["aws"])
    aws_published = datetime.strptime(aws["createDate"], "%Y-%m-%d-%H-%M-%S").date().isoformat()
    aws_seen = aws_observed_at(aws["createDate"])
    records: list[dict[str, Any]] = []
    for collection_name, field in (("ipv4", "prefixes"), ("ipv6", "ipv6_prefixes")):
        prefix_field = "ip_prefix" if collection_name == "ipv4" else "ipv6_prefix"
        for item in aws[field]:
            if item["service"] != "CLOUDFRONT" or item["region"] != "GLOBAL":
                continue
            records.append(prefix_record(
                provider="Amazon Web Services",
                service="aws_cloudfront",
                prefix=item[prefix_field],
                feed_scope="aws_cloudfront_global",
                source_url=AWS_URL,
                raw_path=paths["aws"],
                source_published_at=aws_published,
                retrieved_at=retrieved_at,
                observed_at=aws_seen,
                properties={
                    "feed_create_date": aws["createDate"],
                    "feed_sync_token": aws["syncToken"],
                    "network_border_group": item["network_border_group"],
                    "provider_region": item["region"],
                    "provider_service_code": item["service"],
                    "scope_limit": "CLOUDFRONT records whose provider region is GLOBAL; origin-facing and regional records are excluded.",
                },
            ))

    for key, provider, service, scope, url in (
        ("google-owned", "Google", "google_owned_network", "google_owned", GOOGLE_OWNED_URL),
        ("google-cloud", "Google Cloud", "google_cloud_customer_ranges", "google_cloud_customer", GOOGLE_CLOUD_URL),
    ):
        payload = load_json(paths[key])
        seen = utc_datetime(payload["creationTime"])
        published = seen[:10]
        for item in payload["prefixes"]:
            prefix = item.get("ipv4Prefix") or item.get("ipv6Prefix")
            if not prefix:
                raise ValueError(f"Google prefix record has no CIDR: {item}")
            records.append(prefix_record(
                provider=provider,
                service=service,
                prefix=prefix,
                feed_scope=scope,
                source_url=url,
                raw_path=paths[key],
                source_published_at=published,
                retrieved_at=retrieved_at,
                observed_at=seen,
                properties={
                    "feed_creation_time": payload["creationTime"],
                    "feed_sync_token": payload["syncToken"],
                    "provider_scope": item.get("scope"),
                    "provider_service_code": item.get("service"),
                    "scope_limit": (
                        "Broad Google-owned ranges; the feed does not identify Google Global Cache."
                        if key == "google-owned"
                        else "External ranges available to Google Cloud customer resources; not a Google edge or facility inventory."
                    ),
                },
            ))

    azure_url = azure_download_url(paths["azure-landing"])
    azure_published = azure_published_date(paths["azure-landing"], azure_url)
    azure_seen = f"{azure_published}T00:00:00Z"
    azure = load_json(paths["azure"])
    selected = [item for item in azure["values"] if item["name"] == "AzureFrontDoor.Frontend"]
    if len(selected) != 1:
        raise ValueError(f"expected one AzureFrontDoor.Frontend service tag, found {len(selected)}")
    frontdoor = selected[0]
    for prefix in frontdoor["properties"]["addressPrefixes"]:
        records.append(prefix_record(
            provider="Microsoft Azure",
            service="azure_front_door",
            prefix=prefix,
            feed_scope="azure_front_door_frontend",
            source_url=azure_url,
            raw_path=paths["azure"],
            source_published_at=azure_published,
            retrieved_at=retrieved_at,
            observed_at=azure_seen,
            properties={
                "feed_change_number": azure["changeNumber"],
                "feed_cloud": azure["cloud"],
                "provider_platform": frontdoor["properties"]["platform"],
                "provider_region": frontdoor["properties"]["region"] or None,
                "provider_service_tag": frontdoor["name"],
                "service_tag_change_number": frontdoor["properties"]["changeNumber"],
                "source_time_precision": "date",
                "scope_limit": "AzureFrontDoor.Frontend service tag only; backend and first-party/security tags are excluded.",
            },
        ))

    source_definitions = [
        (paths["aws"], AWS_URL, "application/json", aws_published, "AWS public IP-range feed; normalized scope is GLOBAL CLOUDFRONT only."),
        (paths["google-owned"], GOOGLE_OWNED_URL, "application/json", load_json(paths["google-owned"])["creationTime"][:10], "Broad Google-owned IP ranges; not GGC-specific."),
        (paths["google-cloud"], GOOGLE_CLOUD_URL, "application/json", load_json(paths["google-cloud"])["creationTime"][:10], "Google Cloud customer-resource external IP ranges; not a site inventory."),
        (paths["azure-landing"], AZURE_LANDING_URL, "text/html", azure_published, "Official download landing page used to resolve the versioned Azure Service Tags file."),
        (paths["azure"], azure_url, "application/json", azure_published, "Full Azure Public Service Tags snapshot; normalized scope is AzureFrontDoor.Frontend only."),
    ]
    sources = []
    for path, url, media_type, published, notes in source_definitions:
        write_provenance(
            path,
            source_url=url,
            retrieved_at=retrieved_at,
            media_type=media_type,
            source_published_at=published,
            notes=notes + " Source-specific terms apply; no blanket relicensing is asserted.",
        )
        sources.append({
            "raw_source_ref": repo_ref(path),
            "sha256": sha256(path),
            "source_published_at": published,
            "source_url": url,
        })

    scope_counts = Counter(record["properties"]["feed_scope"] for record in records)
    family_counts = Counter(f"ipv{record['ip_family']}" for record in records)
    return records, {
        "family_counts": dict(sorted(family_counts.items())),
        "scope_counts": dict(sorted(scope_counts.items())),
        "sources": sources,
        "source_terms_status": "Official public operational feeds retained with source-specific terms; repository licensing does not automatically relicense them.",
    }


def sample_address(prefix: str) -> str:
    network = ipaddress.ip_network(prefix, strict=True)
    if network.num_addresses > 2:
        return str(network.network_address + 1)
    return str(network.network_address)


def api_url(endpoint: str, **parameters: str) -> str:
    query = urllib.parse.urlencode({**parameters, "sourceapp": SOURCEAPP})
    return f"{RIPESTAT_BASE}/{endpoint}/data.json?{query}"


def fetch_json_url(url: str) -> dict[str, Any]:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def select_prefix_sample(
    prefix_records: list[dict[str, Any]], sample_per_family: int
) -> list[dict[str, Any]]:
    if sample_per_family < 1:
        raise ValueError("--sample-per-family must be positive")
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in prefix_records:
        grouped[(record["properties"]["feed_scope"], record["ip_family"])].append(record)
    selected: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda record: (
                int(ipaddress.ip_network(record["prefix"]).network_address),
                ipaddress.ip_network(record["prefix"]).prefixlen,
                record["prefix"],
            ),
        )
        selected.extend(ordered[:sample_per_family])
    return selected


def fetch_ripestat_bundle(
    *,
    prefix_records: list[dict[str, Any]],
    output: Path,
    retrieved_at: str,
    sample_per_family: int,
) -> None:
    queries = []
    for record in select_prefix_sample(prefix_records, sample_per_family):
        address = sample_address(record["prefix"])
        network_url = api_url("network-info", resource=address)
        network_response = fetch_json_url(network_url)
        data = network_response.get("data") or {}
        rpki_queries = []
        returned_prefix = data.get("prefix")
        for asn in sorted({int(value) for value in data.get("asns") or [] if int(value) > 0}):
            if not returned_prefix:
                continue
            validation_url = api_url("rpki-validation", resource=str(asn), prefix=returned_prefix)
            rpki_queries.append({
                "asn": asn,
                "request_url": validation_url,
                "response": fetch_json_url(validation_url),
            })
        queries.append({
            "declared_prefix": record["prefix"],
            "feed_scope": record["properties"]["feed_scope"],
            "network_info": {"request_url": network_url, "response": network_response},
            "prefix_record_id": record["record_id"],
            "provider": record["provider"],
            "sampled_address": address,
            "service": record["service"],
            "rpki_validation": rpki_queries,
        })
    write_json(output, {
        "queries": queries,
        "retrieved_at": retrieved_at,
        "sample_per_family": sample_per_family,
        "sample_policy": "For each retained feed scope and IP family, sort canonical prefixes by network address/prefix length and query the first N. Query one address inside each selected prefix.",
        "sourceapp": SOURCEAPP,
    })


def response_time(payload: dict[str, Any], retrieved_at: str) -> str:
    value = payload.get("time")
    return utc_datetime(value) if value else f"{retrieved_at}T00:00:00Z"


def build_ripestat_records(
    *, paths: dict[str, Path], retrieved_at: str, prefix_records: list[dict[str, Any]],
    write_source_provenance: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_path = paths["ripestat"]
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    bundle = load_json(raw_path)
    prefix_by_id = {record["record_id"]: record for record in prefix_records}
    raw_digest = sha256(raw_path)
    records: list[dict[str, Any]] = []
    queried_prefixes: set[str] = set()

    for query in bundle["queries"]:
        prefix_record = prefix_by_id.get(query["prefix_record_id"])
        if not prefix_record:
            raise ValueError(f"RIPEstat bundle references unknown prefix record: {query['prefix_record_id']}")
        queried_prefixes.add(prefix_record["record_id"])
        network_payload = query["network_info"]["response"]
        network_data = network_payload.get("data") or {}
        returned_prefix = network_data.get("prefix")
        origins = sorted({int(asn) for asn in network_data.get("asns") or [] if int(asn) > 0})
        network_status = network_payload.get("status")
        if network_status != "ok":
            origins = []
            returned_prefix = None

        if origins and returned_prefix:
            routed_prefix, family = normalized_prefix(returned_prefix)
            for asn in origins:
                routing_id = f"network:routing_origin:{record_key(prefix_record['record_id'], routed_prefix, str(asn))}"
                records.append(canonical_network_record(
                    record_id=routing_id,
                    evidence_type="routing_origin",
                    subject_type="prefix",
                    subject_id=routed_prefix,
                    provider=prefix_record["provider"],
                    service=prefix_record["service"],
                    prefix=routed_prefix,
                    ip_family=family,
                    asn=asn,
                    relationship_type="originates_prefix",
                    object_type="asn",
                    object_id=f"AS{asn}",
                    status="announced",
                    source_scope="observed",
                    source_url=query["network_info"]["request_url"],
                    raw_source_ref=repo_ref(raw_path),
                    source_sha256=raw_digest,
                    source_published_at=None,
                    retrieved_at=retrieved_at,
                    observed_at=response_time(network_payload, retrieved_at),
                    valid_from=None,
                    valid_to=None,
                    confidence="medium",
                    properties={
                        "api_data_call_status": network_payload.get("data_call_status"),
                        "api_version": network_payload.get("version"),
                        "declared_prefix": query["declared_prefix"],
                        "provider_prefix_record_id": prefix_record["record_id"],
                        "returned_prefix_may_cover_only_sampled_address": True,
                        "sampled_address": query["sampled_address"],
                        "scope_limit": "One address was sampled; the returned route does not prove that every address in the provider-declared prefix is routed identically.",
                    },
                ))
        else:
            declared_prefix, family = normalized_prefix(query["declared_prefix"])
            records.append(canonical_network_record(
                record_id=f"network:routing_origin:{record_key(prefix_record['record_id'], 'not-announced')}",
                evidence_type="routing_origin",
                subject_type="prefix",
                subject_id=declared_prefix,
                provider=prefix_record["provider"],
                service=prefix_record["service"],
                prefix=declared_prefix,
                ip_family=family,
                asn=None,
                relationship_type="originates_prefix",
                object_type="asn",
                object_id=None,
                status="not_announced" if network_status == "ok" else "unknown",
                source_scope="observed",
                source_url=query["network_info"]["request_url"],
                raw_source_ref=repo_ref(raw_path),
                source_sha256=raw_digest,
                source_published_at=None,
                retrieved_at=retrieved_at,
                observed_at=response_time(network_payload, retrieved_at),
                valid_from=None,
                valid_to=None,
                confidence="medium" if network_status == "ok" else "low",
                properties={
                    "api_data_call_status": network_payload.get("data_call_status"),
                    "api_version": network_payload.get("version"),
                    "declared_prefix": query["declared_prefix"],
                    "provider_prefix_record_id": prefix_record["record_id"],
                    "sampled_address": query["sampled_address"],
                    "scope_limit": "A negative sampled lookup is not evidence that the whole provider prefix is unused.",
                },
            ))

        for validation in query["rpki_validation"]:
            payload = validation["response"]
            data = payload.get("data") or {}
            status = data.get("status")
            if status not in {"valid", "invalid_asn", "invalid_length", "unknown"}:
                status = "unknown"
            rpki_prefix, family = normalized_prefix(data.get("prefix") or returned_prefix or query["declared_prefix"])
            asn = int(validation["asn"])
            records.append(canonical_network_record(
                record_id=f"network:rpki_validation:{record_key(prefix_record['record_id'], rpki_prefix, str(asn))}",
                evidence_type="rpki_validation",
                subject_type="asn",
                subject_id=f"AS{asn}",
                provider=prefix_record["provider"],
                service=prefix_record["service"],
                prefix=rpki_prefix,
                ip_family=family,
                asn=asn,
                relationship_type="validated_by_rpki",
                object_type="prefix",
                object_id=rpki_prefix,
                status=status,
                source_scope="observed",
                source_url=validation["request_url"],
                raw_source_ref=repo_ref(raw_path),
                source_sha256=raw_digest,
                source_published_at=None,
                retrieved_at=retrieved_at,
                observed_at=response_time(payload, retrieved_at),
                valid_from=None,
                valid_to=None,
                confidence="high" if payload.get("status") == "ok" else "low",
                properties={
                    "api_data_call_status": payload.get("data_call_status"),
                    "api_version": payload.get("version"),
                    "description": data.get("description"),
                    "provider_prefix_record_id": prefix_record["record_id"],
                    "scope_limit": "RPKI validity applies to an origin/prefix pair and is not ownership or location evidence.",
                },
            ))

    if write_source_provenance:
        write_provenance(
            raw_path,
            source_url=f"{RIPESTAT_BASE}/",
            retrieved_at=retrieved_at,
            media_type="application/json",
            source_published_at=None,
            notes="Bundled network-info and RPKI-validation API responses for a deterministic provider-prefix sample; no geolocation endpoint is used.",
        )
    return records, {
        "provider_prefix_record_count": len(prefix_records),
        "queried_prefix_count": len(queried_prefixes),
        "raw_source_ref": repo_ref(raw_path),
        "sample_per_family": bundle["sample_per_family"],
        "sample_policy": bundle["sample_policy"],
        "source_url": f"{RIPESTAT_BASE}/",
        "sourceapp": bundle["sourceapp"],
    }


def main() -> None:
    args = parse_args()
    paths = raw_paths(args.retrieved_at)
    if args.fetch and args.dataset in {"all", "prefixes"}:
        fetch_prefix_sources(paths)

    prefix_records, prefix_report = build_prefix_records(paths, args.retrieved_at)
    reports: dict[str, Any] = {}
    if args.dataset in {"all", "prefixes"}:
        reports["provider-prefixes"] = write_network_layer(
            records=prefix_records,
            layer_name="provider-prefixes",
            retrieved_at=args.retrieved_at,
            parser_name="update_network.py:prefixes",
            output_root=args.output_root,
            schema_path=args.schema,
            extra_report=prefix_report,
        )

    if args.fetch and args.dataset in {"all", "ripestat"}:
        fetch_ripestat_bundle(
            prefix_records=prefix_records,
            output=paths["ripestat"],
            retrieved_at=args.retrieved_at,
            sample_per_family=args.sample_per_family,
        )
    if args.dataset in {"all", "ripestat"}:
        routing_records, routing_report = build_ripestat_records(
            paths=paths,
            retrieved_at=args.retrieved_at,
            prefix_records=prefix_records,
        )
        reports["ripestat-routing"] = write_network_layer(
            records=routing_records,
            layer_name="ripestat-routing",
            retrieved_at=args.retrieved_at,
            parser_name="update_network.py:ripestat",
            output_root=args.output_root,
            schema_path=args.schema,
            extra_report=routing_report,
        )

    print(json.dumps({
        layer: {"record_count": report["record_count"], "statuses": report["statuses"]}
        for layer, report in reports.items()
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
