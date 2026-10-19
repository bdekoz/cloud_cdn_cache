#!/usr/bin/env python3
"""Reconcile AWS/Oracle Gulf references without changing their canonical layers."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re

from geography_enrichment_common import BASELINE, DATE, TAG, baseline_layers, evidence, read, source, soup
from location_common import REPO_ROOT, repo_ref, sha256, write_json

GULF = {"AE", "SA", "BH", "OM", "QA", "KW"}


def cells(row):
    return [" ".join(c.get_text(" ", strip=True).split()) for c in row.find_all(["td", "th"], recursive=False)]


def assess():
    layers = baseline_layers()
    baseline = []
    for name, layer in layers.items():
        if not name.startswith(("aws/", "oracle/")):
            continue
        for feature in read(REPO_ROOT / layer["files"]["geojson"]["path"])["features"]:
            row = feature["properties"]
            if row["country_code"] in GULF:
                baseline.append({"layer": name, "record_id": row["record_id"], "provider": row["provider"],
                    "entity_type": row["entity_type"], "country_code": row["country_code"], "city": row["city"],
                    "geometry_null": feature["geometry"] is None, "retrieved_at": row["retrieved_at"],
                    "lifecycle_status": row["lifecycle_status"], "raw_source_ref": row["raw_source_ref"],
                    "source_sha256": row["source_sha256"], "source_url": row["source_url"]})

    oracle_public = []
    for table in soup("oracle-regions").find_all("table"):
        for tr in table.find_all("tr"):
            row = cells(tr)
            if len(row) == 6 and row[1] in {"me-abudhabi-1", "me-dubai-1", "me-jeddah-1", "me-riyadh-1"}:
                oracle_public.append({"region_name": row[0], "region_id": row[1], "source_location_label": row[2],
                    "region_key": row[3], "realm_key": row[4], "availability_domain_count": int(row[5]),
                    "canonical_record_id": "oracle:cloud_region:" + row[1], "evidence": evidence("oracle-regions")})
    if len(oracle_public) != 4:
        raise ValueError("Oracle Gulf public directory changed; review required")

    dedicated, realm = [], None
    for table in soup("oracle-epm-realms").find_all("table"):
        if "Geographical Region (Realm)" not in table.get_text(" ", strip=True):
            continue
        for tr in table.find_all("tr")[1:]:
            row = cells(tr)
            if len(row) != 4:
                continue
            if row[0]:
                realm = row[0]
            if realm and realm.startswith("DRCC ") and row[2].startswith("me-"):
                dedicated.append({"region_id": row[2], "region_name": row[1], "realm_label": realm,
                    "region_key": row[3], "scope": "Oracle EPM product directory / dedicated realm",
                    "public_availability_asserted": False, "current_lifecycle_status": "unknown",
                    "evidence": evidence("oracle-epm-realms")})

    oracle_interconnect = []
    for table in soup("oracle-fastconnect-partners").find_all("table"):
        if "Data Center Provider" not in table.get_text(" ", strip=True):
            continue
        for tr in table.find_all("tr")[1:]:
            row = cells(tr)
            if len(row) == 4 and row[0].startswith(("UAE ", "Saudi Arabia ")):
                oracle_interconnect.append({"region_label": row[0], "operator": row[2], "location_label": row[3],
                    "record_unit": "region_interconnect_location_relationship", "region_building_identity_asserted": False,
                    "evidence": evidence("oracle-fastconnect-partners")})
    aws_interconnect = []
    for table in soup("aws-direct-connect").find_all("table"):
        for tr in table.find_all("tr")[1:]:
            row = cells(tr)
            if row and any(label in row[0] for label in ("Manama", "Muscat", "Dubai", "Fujairah")):
                aws_interconnect.append({"location_label": row[0], "record_unit": "interconnect_location",
                    "region_building_identity_asserted": False, "evidence": evidence("aws-direct-connect")})

    aws_regions = []
    for line in (REPO_ROOT / source("aws-regions")["path"]).read_text().splitlines():
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(row) >= 4 and row[0] in {"me-central-1", "me-south-1"}:
            aws_regions.append({"region_id": row[0], "region_name": row[1], "declared_zone_count": int(row[2]),
                "country_label": row[3], "city": None, "evidence": evidence("aws-regions")})
    aws_azs = []
    for line in (REPO_ROOT / source("aws-availability-zones")["path"]).read_text().splitlines():
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(row) == 3 and re.fullmatch(r"(?:mec1|mes1)-az\d+", row[0]):
            aws_azs.append({"zone_id": row[0], "region_id": row[1], "evidence": evidence("aws-availability-zones")})
    if len(aws_regions) != 2 or len(aws_azs) != 6:
        raise ValueError("AWS Gulf region/AZ directory changed; review required")
    saudi_text = soup("aws-saudi-plan").get_text(" ", strip=True)
    if not re.search(r"December\s+2026", saudi_text):
        raise ValueError("Saudi planned launch date changed; review required")
    cf_text = soup("aws-cloudfront").get_text(" ", strip=True)
    for label in ["Dubai", "Jeddah", "Riyadh", "Muscat", "Doha", "Bahrain"]:
        if label not in cf_text:
            raise ValueError(f"CloudFront locality no longer listed: {label}")
    local_zone_rows = [cells(tr) for table in soup("aws-local-zones-guide").find_all("table")
                       for tr in table.find_all("tr")[1:]]
    current_gulf_zones = [r for r in local_zone_rows if any(re.search(r"\b" + token + r"\b", " ".join(r), re.I)
        for token in ["Oman", "Muscat", "Saudi", "Dubai", "Emirates", "Bahrain", "Doha", "Qatar", "Kuwait"])]

    priorities = [
        {"priority": "P0", "action": "Add separate city-reference views for the four public OCI regions and five explicit Gulf CloudFront cities; keep country-only Bahrain and AWS core-region geography at country precision.",
         "acceptance": "No AWS UAE region/AZ assigned to Dubai; city views excluded from facility totals, with original source dates and a licensed gazetteer crosswalk."},
        {"priority": "P0", "action": "Refresh core directory identities and track AWS Saudi as planned for December 2026; wait for official region/AZ identifiers and launch evidence.",
         "acceptance": "Provider, service and realm namespace every identity. No inferred Saudi code, AZ count or operational lifecycle. Existing IDs persist."},
        {"priority": "P0", "action": "Reconcile the historical Muscat Local Zone against the current guide, where no Gulf Local Zone rows were found.",
         "acceptance": "Retain mes1-mct1-az1 and its original evidence; mark listing discrepancy for review. Absence alone cannot establish retirement."},
        {"priority": "P1", "action": "Add the five AWS Direct Connect entries and six OCI FastConnect region/site relationships to an interconnect evidence layer, after operator/address matching.",
         "acceptance": "Deduplicate physical endpoints separately from region associations; do not identify them as region data-center buildings. Reconcile historical Fujairah CloudFront evidence separately."},
        {"priority": "P1", "action": "Add Oracle EPM's six dedicated Gulf region references in OC9, OC21, OC29 and OC36 as product-scoped evidence; review SDK-only entries separately.",
         "acceptance": "Dedicated realms remain separate from OC1 public regions; no public availability or tenancy-independent AD names inferred from SDK registration."},
        {"priority": "P2", "action": "Join official AWS/OCI prefix feeds and published geofeeds by provider/service/region; use public measurements only as dated corroboration.",
         "acceptance": "Prefix registration, routing, latency, DNS and CDN edge location remain distinct from application origins, owned facilities and service health."},
        {"priority": "P2", "action": "Implement weekly source-change checks and a planned-launch watch, retaining raw bytes, publication date, assertion date and retrieval date.",
         "acceptance": "Alert on missing IDs and schema/realm changes; publish counts of listed, mapped, unlocated, stale and conflicting records separately. No scheduler created by this assessment."},
    ]
    return {"reviewed_at": DATE, "scope": "GCC: UAE, Saudi Arabia, Bahrain, Oman, Qatar, Kuwait; AWS and Oracle",
        "mode": "assessment_and_implementation_plan", "canonical_aws_oracle_layers_changed": False,
        "baseline_manifest": {"path": repo_ref(BASELINE), "sha256": sha256(BASELINE)},
        "baseline_records": baseline, "baseline_record_count": len(baseline),
        "baseline_geometry_null": sum(r["geometry_null"] for r in baseline),
        "baseline_layer_counts": dict(sorted(Counter(r["layer"] for r in baseline).items())),
        "aws_current_regions": aws_regions, "aws_current_zone_ids": aws_azs,
        "aws_saudi_plan": {"expected_launch": "2026-12", "lifecycle_status": "planned", "region_id": None,
            "availability_zone_ids": [], "evidence": evidence("aws-saudi-plan")},
        "aws_cloudfront_reconciliation": {"current_listed_gulf_labels": ["Bahrain", "Doha", "Dubai", "Jeddah", "Muscat", "Riyadh"],
            "current_source": evidence("aws-cloudfront"), "historical_fujairah_source": evidence("aws-uae-launch"),
            "fujairah_assessment": "2022 launch post mentions a CloudFront location, absent from current features city list; do not silently add as currently operational"},
        "aws_local_zones_reconciliation": {"current_gulf_rows": current_gulf_zones,
            "source": evidence("aws-local-zones-guide"), "historical_muscat_record": "aws:local_zone:mes1-mct1-az1",
            "missing_listing_is_not_retirement": True},
        "aws_interconnect_candidates": aws_interconnect,
        "oracle_public_regions": sorted(oracle_public, key=lambda r: r["region_id"]),
        "oracle_dedicated_product_references": dedicated, "oracle_fastconnect_candidates": oracle_interconnect,
        "oracle_sdk_reference": {"evidence": evidence("oracle-sdk-regions"),
            "limitation": "SDK registration establishes a client identifier and realm, not current launch, public access, address or ownership"},
        "accuracy_risks": ["A cloud region is not necessarily its city's data center; AWS UAE is country-scoped.",
            "AWS me-central-1 is UAE; Alibaba me-central-1 is Riyadh. Alibaba me-east-1 is Dubai; Huawei me-east-1 is Riyadh.",
            "OCI AD counts and fault domains are not building counts; AD names have tenancy-specific prefixes.",
            "Directory lifecycle is separate from present service health; this review is not a live health assessment."],
        "plan": priorities}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    result = assess()
    write_json(args.output_root / f"data/gulf/aws-oracle-coverage.{TAG}.json", result)
    print(f"Gulf review: {result['baseline_record_count']} records, {result['baseline_geometry_null']} unlocated; "
          f"{len(result['aws_interconnect_candidates'])} AWS and {len(result['oracle_fastconnect_candidates'])} OCI interconnect candidates; "
          f"{len(result['oracle_dedicated_product_references'])} dedicated Oracle product references")


if __name__ == "__main__":
    main()
