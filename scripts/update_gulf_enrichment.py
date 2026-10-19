#!/usr/bin/env python3
"""Rebuild scoped Gulf locations, locality views and non-spatial evidence offline."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
import ipaddress
from pathlib import Path
import re
import zipfile

from assess_gulf_coverage import assess
from geography_enrichment_common import record_evidence
from gulf_enrichment_common import (
    AWS_REGIONS, BASELINE, DATE, GULF, LAYERS, OCI_REGIONS, TAG, baseline,
    evidence, read, source, soup,
)
from location_common import REPO_ROOT, load_validator, repo_ref, sha256, slug, write_json, write_layer
from network_common import write_network_layer
from update_infrastructure import validate_collection
from update_network import prefix_record

CITY_IDS = {("AE", "Dubai"): "292223", ("AE", "Abu Dhabi"): "292968",
            ("SA", "Riyadh"): "108410", ("SA", "Jeddah"): "105343",
            ("OM", "Muscat"): "287286", ("QA", "Doha"): "290030"}


def derived(path):
    csv_path = str(Path(path).with_suffix(".csv"))
    return {"csv": {"path": csv_path, "source": path, "generator": "make " + csv_path}}


def cloudfront_labels():
    countries = {"Bahrain": "BH", "Kingdom of Saudi Arabia": "SA", "United Arab Emirates": "AE",
                 "Oman": "OM", "Qatar": "QA", "Kuwait": "KW"}
    labels = {}
    for paragraph in soup("aws-cloudfront").find_all("p"):
        text = " ".join(paragraph.get_text(" ", strip=True).split())
        country, separator, places = text.partition(":")
        if separator and country in countries:
            for city in places.split(","):
                match = re.fullmatch(r"(.+?)(?:\s+\((\d+)\))?", city.strip())
                if not match:
                    raise ValueError(f"Unrecognized CloudFront locality: {city}")
                key = countries[country], match[1]
                if key in labels:
                    raise ValueError(f"Duplicate CloudFront locality: {key}")
                labels[key] = int(match[2]) if match[2] else None
    if len(labels) != 6:
        raise ValueError("CloudFront Gulf list changed; reconcile additions/removals")
    return labels


def refresh_locations(output_root, review):
    previous = {l["layer"]: l for l in baseline()["layers"]}
    regions = {r["region_id"]: r for r in review["aws_current_regions"]}
    zones = {r["zone_id"]: r for r in review["aws_current_zone_ids"]}
    oracle = {r["region_id"]: r for r in review["oracle_public_regions"]}
    cf = cloudfront_labels()
    all_rows, audit = [], []
    for layer in LAYERS:
        rows, changed, sources = [], [], set()
        for feature in read(REPO_ROOT / previous[layer]["files"]["geojson"]["path"])["features"]:
            row = deepcopy(feature["properties"])
            coordinates = (feature["geometry"] or {}).get("coordinates", [None, None])
            row.update(latitude=coordinates[1], longitude=coordinates[0])
            if row["country_code"] in GULF:
                old_evidence = record_evidence(row)
                props = row["properties"]
                if layer == "aws/local-zones":
                    if row["record_id"] != "aws:local_zone:mes1-mct1-az1" or review["aws_local_zones_reconciliation"]["current_gulf_rows"]:
                        raise ValueError("Local Zone listing changed; explicit reconciliation required")
                    row["lifecycle_status"] = "unknown"
                    props.update(listing_review={"reviewed_at": DATE, "status": "absent_from_current_directory",
                        "evidence": evidence("aws-local-zones-guide"), "absence_does_not_establish_retirement": True},
                        legacy_geometry_not_current_confirmation=True)
                    sources.add("aws-local-zones-guide")
                    # The historical assertion was not observed again: retain its retrieval and last_seen dates.
                else:
                    if layer == "aws/regions-and-zones":
                        if row["entity_type"] == "cloud_region":
                            current = regions[row["site_code"]]
                            row["name"] = current["region_name"]
                            props["declared_zone_count"] = current["declared_zone_count"]
                            key = "aws-regions"
                        else:
                            current = zones[row["site_code"]]
                            if row["parent_record_id"] != "aws:cloud_region:" + current["region_id"]:
                                raise ValueError("AWS parent region changed")
                            key = "aws-availability-zones"
                        props["geography_scope"] = "country_only"
                        row.update(city=None, metro=None, latitude=None, longitude=None)
                    elif layer == "oracle/cloud-regions":
                        current = oracle[row["site_code"]]
                        row["name"] = current["region_name"]
                        props.update(realm_key=current["realm_key"], region_key=current["region_key"],
                                     availability_domain_count=current["availability_domain_count"],
                                     region_location=current["source_location_label"])
                        key = "oracle-regions"
                    else:
                        label = row["city"]
                        count = cf[(row["country_code"], label)]
                        old_count = props.pop("asset_count", None)
                        props.update(source_location_label=label, asset_count=count,
                                     asset_count_disclosed=count is not None,
                                     historical_asset_count={"value": old_count, "evidence": old_evidence})
                        if row["country_code"] == "BH":
                            row.update(city=None, metro=None, location_precision="region")
                            props["geography_scope"] = "country_only"
                        key = "aws-cloudfront"
                    row.update({k: v for k, v in evidence(key).items() if k not in {"source_id", "source_updated_at"}})
                    row["last_seen"] = DATE
                    props["previous_evidence"] = old_evidence
                    props["directory_reconfirmed_at"] = DATE
                    sources.add(key)
                changed.append(row["record_id"])
            rows.append(row)
        primary = sorted(sources)[0]
        directory, name = layer.split("/", 1)
        path = f"data/{layer}.{TAG}.geojson"
        write_layer(records=rows, output_dir=output_root / "data" / directory, layer_name=name,
            retrieved_at=DATE, source_url=source(primary)["source_url"], raw_path=REPO_ROOT / source(primary)["path"],
            parser_name="update_gulf_enrichment.py:refresh_locations", extra_report={
                "scope_note": "Only GCC rows reviewed; all other rows retain their original evidence and dates.",
                "previous_snapshot": previous[layer]["files"]["geojson"], "reviewed_record_ids": sorted(changed),
                "enrichment_sources": [{**evidence(k), "source_scope": "provider_declared"} for k in sorted(sources)],
                "generated_files": [path], "derived_files": derived(path),
            })
        audit.append({"layer": layer, "reviewed_record_ids": sorted(changed), "record_count": len(rows)})
        all_rows.extend(r for r in rows if r["country_code"] in GULF)
    return all_rows, audit


def localities(output_root, rows):
    with zipfile.ZipFile(REPO_ROOT / source("geonames-cities15000")["path"]) as archive:
        places = {r[0]: r for line in archive.read("cities15000.txt").decode().splitlines() if (r := line.split("\t"))[0] in CITY_IDS.values()}
    features, held = [], []
    for row in rows:
        if row["entity_type"] == "local_zone":
            reason = "historical_listing_not_reconfirmed"
        elif row["service"] == "aws_cloud":
            reason = "country_only_region_or_zone"
        elif not row["city"]:
            reason = "country_only_edge_label"
        else:
            reason = None
        if reason:
            held.append({"record_id": row["record_id"], "reason": reason})
            continue
        identifier = CITY_IDS[(row["country_code"], row["city"])]
        place = places[identifier]
        if place[8] != row["country_code"] or place[2] != row["city"] or place[6] != "P":
            raise ValueError("Reviewed GeoNames locality identity changed")
        vendor = row["record_id"].split(":")[0]
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(place[5]), float(place[4])]},
            "properties": {"footprint_id": f"{vendor}:locality:{row['service']}:{identifier}",
                "vendor_id": vendor, "provider": row["provider"], "service": row["service"], "locality": row["city"],
                "country_code": row["country_code"], "location_precision": "city",
                "coordinate_method": "gazetteer_reference_point", "coordinate_crs": "EPSG:4326",
                "record_unit": "provider_service_locality", "physical_site_confirmed": False,
                "lifecycle_status": "not_assessed", "excluded_from_canonical_totals": True,
                "source_record_ids": [row["record_id"]], "source_claim_ids": [], "source_locality_labels": [row["city"]],
                "evidence": [record_evidence(row)], "gazetteer": {"geonames_id": identifier, "name": place[1],
                    "feature_code": place[7], "admin1": place[10], "evidence": evidence("geonames-cities15000"),
                    "license_url": "https://creativecommons.org/licenses/by/4.0/"}}})
    collection = {"type": "FeatureCollection", "schema_version": "1.0.0", "built_at": DATE,
                  "excluded_from_canonical_totals": True, "features": sorted(features, key=lambda f: f["properties"]["footprint_id"])}
    load_validator(REPO_ROOT / "schema/geographic-footprint.schema.json").validate(collection)
    path = f"data/gulf/provider-localities.{TAG}.geojson"
    write_json(output_root / path, collection)
    report = {"built_at": DATE, "input_layers": list(LAYERS), "canonical_input_count": len(rows),
              "record_count": len(features), "mapped_record_count": len(features), "held_records": sorted(held, key=lambda r: r["record_id"]),
              "held_record_count": len(held), "physical_site_count": None, "derived_files": derived(path),
              "scope_note": "City reference points only; held country labels and historical Local Zone are not geocoded."}
    write_json(output_root / path.replace(".geojson", ".report.json"), report)
    return report


def infrastructure(output_root, review, canonical_ids):
    records, endpoints = [], {}

    def record(rid, category, unit, name, provider, country, key, properties, relationships=None):
        src = evidence(key)
        src.pop("source_id")
        row = {"record_id": rid, "category": category, "unit": unit, "name": name, "provider": provider,
            "parties": [{"name": provider, "role": "listing_provider"}], "country_codes": [country],
            "country_scope": "single_country", "lifecycle_status": "unknown", "source_scope": "provider_declared",
            **src, "confidence": "high", "geometry": None, "spatial_representation": "none",
            "relationships": relationships or [], "properties": properties}
        records.append(row)
        return row

    aws_map = {
        "AWS Bahrain DC52, Manama, Bahrain": ("aws-dc52-manama", "Amazon Web Services", "BH", "Manama", "DC52"),
        "AWS Bahrain DC53, Manama, Bahrain": ("aws-dc53-manama", "Amazon Web Services", "BH", "Manama", "DC53"),
        "Equinix MC1 Barka, Muscat": ("equinix-mc1", "Equinix", "OM", "Barka", "MC1"),
        "Equinix DX1, Dubai, UAE": ("equinix-dx1", "Equinix", "AE", "Dubai", "DX1"),
        "Etisalat Smart Hub Data Center, Fujairah, UAE": ("etisalat-smarthub-fujairah", "Etisalat", "AE", "Fujairah", None),
    }

    def endpoint(identity, operator, country, locality, site_code, key, label):
        rid = "gulf:interconnect_endpoint:" + identity
        if rid in endpoints:
            endpoints[rid]["properties"]["directory_labels"].append({"label": label, "evidence": evidence(key)})
            return rid
        props = {"operator_label": operator, "locality": locality, "site_code": site_code,
            "identity_status": "explicit_site_code" if site_code else "source_label_only",
            "directory_labels": [{"label": label, "evidence": evidence(key)}],
            "facility_address": None, "unique_physical_facility_asserted": False,
            "region_building_identity_asserted": False, "ownership_not_inferred": True}
        if identity in {"equinix-dx1", "equinix-mc1"}:
            text = " ".join(soup(identity).get_text(" ", strip=True).split())
            address = "Barka, Al Batinah Postal Code 789 Oman" if identity.endswith("mc1") else "Dubai, 500389 United Arab Emirates"
            if address not in text or site_code not in text:
                raise ValueError(f"Equinix address/code changed: {identity}")
            props.update(operator_evidence=evidence(identity), operator_address_label=address,
                         address_precision="locality_postal_label", operator_code_corroborated=True)
            if site_code == "MC1":
                props["metro"] = "Muscat"
        row = record(rid, "interconnect_endpoint_reference", "source_labeled_endpoint", label, operator, country, key, props)
        endpoints[rid] = row
        return rid

    if {r["location_label"] for r in review["aws_interconnect_candidates"]} != set(aws_map):
        raise ValueError("AWS interconnect directory changed; reconcile endpoints")
    for item in review["aws_interconnect_candidates"]:
        identity, operator, cc, city, code = aws_map[item["location_label"]]
        endpoint_id = endpoint(identity, operator, cc, city, code, "aws-direct-connect", item["location_label"])
        record("aws:interconnect_membership:" + identity, "cloud_interconnect_membership", "service_endpoint_membership",
            "AWS Direct Connect / " + item["location_label"], "Amazon Web Services", cc, "aws-direct-connect",
            {"service": "aws_direct_connect", "region_record_id": None, "region_association_not_asserted": True,
             "endpoint_identity_basis": "directory label; explicit site code when present"},
            [{"relationship_type": "uses_interconnect_endpoint", "target_record_id": endpoint_id}])
    oci_by_name = {r["region_name"]: r for r in review["oracle_public_regions"]}
    for item in review["oracle_fastconnect_candidates"]:
        region = oci_by_name[item["region_label"]]
        cc = OCI_REGIONS[region["region_id"]]
        city = region["source_location_label"].split(",")[0]
        code = "DX1" if item["operator"] == "Equinix" and item["location_label"] == "DX1, Dubai, UAE" else None
        identity = "equinix-dx1" if code else slug(item["operator"] + "-" + item["location_label"])
        endpoint_id = endpoint(identity, item["operator"], cc, city, code, "oracle-fastconnect-partners", item["location_label"])
        record("oracle:interconnect_membership:oc1:" + region["region_id"] + ":" + identity,
            "cloud_interconnect_membership", "service_endpoint_membership", "OCI FastConnect / " + item["location_label"],
            "Oracle Cloud Infrastructure", cc, "oracle-fastconnect-partners",
            {"service": "oracle_fastconnect", "realm_key": "OC1", "region_label": item["region_label"],
             "region_building_identity_asserted": False},
            [{"relationship_type": "uses_interconnect_endpoint", "target_record_id": endpoint_id},
             {"relationship_type": "serves_cloud_region", "target_record_id": region["canonical_record_id"]}])
    for item in review["oracle_dedicated_product_references"]:
        realm = re.search(r"\((OC\d+)\)", item["realm_label"])[1]
        country = {"OC9": "OM", "OC21": "QA", "OC29": "AE", "OC36": "SA"}[realm]
        record(f"oracle:dedicated_product_region:{realm.lower()}:{item['region_id']}",
            "dedicated_product_region_reference", "product_region_reference", item["region_name"],
            "Oracle", country, "oracle-epm-realms",
            {"realm_key": realm, "region_id": item["region_id"], "region_key": item["region_key"],
             "realm_label": item["realm_label"], "product_scope": "Oracle EPM Cloud", "access_scope": "dedicated",
             "public_availability_asserted": False, "region_building_identity_asserted": False,
             "sdk_registration_is_not_launch_evidence": True})
    collection = {"type": "InfrastructureEvidenceCollection", "schema_version": "1.0.0", "retrieved_at": DATE,
        "scope_note": "Source-labeled endpoints, service memberships and dedicated product references are different units; no physical-site total or current health assertion.",
        "categories": {"interconnect_endpoint_reference": "Deduplicated source label or explicit operator/site code; not a unique physical facility count.",
            "cloud_interconnect_membership": "Cloud service membership at a referenced endpoint; OCI includes its published region association.",
            "dedicated_product_region_reference": "Oracle EPM directory reference in a dedicated realm, separate from public OCI regions."},
        "records": sorted(records, key=lambda r: r["record_id"])}
    validate_collection(collection, external_record_ids=canonical_ids)
    path = f"data/infrastructure/gulf-cloud-connectivity.{TAG}.json"
    write_json(output_root / path, collection)
    report = {"built_at": DATE, "record_count": len(records), "category_counts": dict(sorted(Counter(r["category"] for r in records).items())),
        "physical_site_count": None, "endpoint_reference_count": len(endpoints),
        "operator_code_corroborated_count": sum(bool(r["properties"].get("operator_code_corroborated")) for r in endpoints.values()),
        "unresolved_address_count": len(endpoints), "derived_files": derived(path)}
    write_json(output_root / path.replace(".json", ".report.json"), report)
    return report


def geofeed_rows():
    result = []
    with (REPO_ROOT / source("aws-geofeed")["path"]).open(newline="", encoding="utf-8") as stream:
        for number, row in enumerate(csv.reader(stream), 1):
            if not row or row[0].startswith("#"):
                continue
            if len(row) != 5:
                raise ValueError(f"AWS geofeed schema changed at line {number}")
            network = ipaddress.ip_network(row[0], strict=True)
            result.append((network, {"prefix": str(network), "country_code": row[1], "subdivision": row[2],
                                     "city_label": row[3], "postal_code": row[4], "source_line": number}))
    if not result:
        raise ValueError("Empty AWS geofeed")
    return result


def join_geofeed(prefix, feeds):
    network = ipaddress.ip_network(prefix, strict=True)
    matches, covered = [], []
    for other, row in feeds:
        if network.version != other.version or not network.overlaps(other):
            continue
        relationship = "exact" if network == other else "covering" if network.subnet_of(other) else "subnet"
        matches.append({**row, "overlap_relation": relationship})
        covered.append(network if network.subnet_of(other) else other)
    coverage = sum(p.num_addresses for p in ipaddress.collapse_addresses(covered))
    return {"matches": matches, "matched_address_count": str(coverage), "prefix_address_count": str(network.num_addresses),
        "coverage": "full" if coverage == network.num_addresses else "partial" if coverage else "none",
        "distinct_label_count": len({(r["country_code"], r["subdivision"], r["city_label"]) for r in matches}),
        "scope": "IP geolocation declarations only; subnet labels do not locate the whole prefix or a facility"}


def prefixes(output_root):
    records, feeds, matched_feed_lines, cache = [], geofeed_rows(), set(), {}
    aws = read(REPO_ROOT / source("aws-ip-ranges")["path"])
    for field, prefix_field in [("prefixes", "ip_prefix"), ("ipv6_prefixes", "ipv6_prefix")]:
        for row in aws[field]:
            if row["region"] not in AWS_REGIONS:
                continue
            prefix = row[prefix_field]
            if prefix not in cache:
                cache[prefix] = join_geofeed(prefix, feeds)
            geo = cache[prefix]
            matched_feed_lines.update(r["source_line"] for r in geo["matches"])
            records.append(prefix_record(provider="Amazon Web Services", service="aws_" + slug(row["service"]).replace("-", "_"),
                prefix=prefix, feed_scope="aws:" + row["region"] + ":" + row["service"] + ":" + row["network_border_group"],
                source_url=source("aws-ip-ranges")["source_url"], raw_path=REPO_ROOT / source("aws-ip-ranges")["path"],
                source_published_at=aws["createDate"][:10], retrieved_at=DATE, observed_at=source("aws-ip-ranges")["captured_at"],
                properties={"region_id": row["region"], "region_record_id": "aws:cloud_region:" + row["region"],
                    "region_country_code": AWS_REGIONS[row["region"]], "network_border_group": row["network_border_group"],
                    "provider_service_label": row["service"], "partition": "aws", "feed_create_date": aws["createDate"],
                    "feed_sync_token": aws["syncToken"], "geofeed": geo, "geofeed_evidence": evidence("aws-geofeed"),
                    "documentation": evidence("aws-ip-documentation"), "physical_location_not_asserted": True}))
    oracle = read(REPO_ROOT / source("oracle-ip-ranges")["path"])
    for region in oracle["regions"]:
        if region["region"] not in OCI_REGIONS:
            continue
        for row in region["cidrs"] + region.get("ipv6_cidrs", []):
            records.append(prefix_record(provider="Oracle Cloud Infrastructure", service="oracle_cloud",
                prefix=row["cidr"], feed_scope="oracle:oc1:" + region["region"],
                source_url=source("oracle-ip-ranges")["source_url"], raw_path=REPO_ROOT / source("oracle-ip-ranges")["path"],
                source_published_at=source("oracle-ip-ranges")["source_published_at"], retrieved_at=DATE,
                observed_at=source("oracle-ip-ranges")["captured_at"],
                properties={"region_id": region["region"], "region_record_id": "oracle:cloud_region:" + region["region"],
                    "realm_key": "OC1", "region_country_code": OCI_REGIONS[region["region"]], "service_tags": sorted(row["tags"]),
                    "feed_last_updated_timestamp": oracle["last_updated_timestamp"], "feed_timestamp_timezone": "not_declared",
                    "source_updated_at": oracle["last_updated_timestamp"][:10],
                    "documentation": evidence("oracle-ip-documentation"), "physical_location_not_asserted": True}))
    unmatched = [row for _, row in feeds if row["country_code"] in GULF and row["source_line"] not in matched_feed_lines]
    report = write_network_layer(records=records, layer_name="gulf-provider-prefixes", retrieved_at=DATE,
        parser_name="update_gulf_enrichment.py:prefixes", output_root=output_root, extra_report={
            "scope_note": "AWS region/service/border-group/prefix and OCI OC1 region/prefix declarations, including IPv6; unlike service rows can repeat a prefix. No routing measurements or facility locations inferred.",
            "record_unit": "provider_region_service_scope_prefix", "distinct_provider_prefix_count": len({(r["provider"], r["prefix"]) for r in records}),
            "region_counts": dict(sorted(Counter(r["properties"]["region_id"] for r in records).items())),
            "aws_distinct_prefix_geofeed_coverage": dict(sorted(Counter(g["coverage"] for g in cache.values()).items())),
            "gulf_geofeed_rows_without_overlap_in_selected_aws_regions": unmatched,
            "unmatched_geofeed_count": len(unmatched), "unmatched_geofeed_is_not_region_launch_evidence": True,
            "geofeed_source": evidence("aws-geofeed"),
            "muscat_border_group_evidence": {
                "network_border_group": "me-south-1-mct-1", "evidence": evidence("aws-ip-ranges"),
                "record_ids": sorted(r["record_id"] for r in records if r["properties"].get("network_border_group") == "me-south-1-mct-1"),
                "operational_local_zone_status_established": False},
            "source_timestamp_policy": "observed_at is HTTP capture time; published dates come from feed metadata. OCI's timezone-less timestamp is preserved verbatim.",
        })
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    review = assess()
    rows, refresh = refresh_locations(args.output_root, review)
    locality = localities(args.output_root, rows)
    infra = infrastructure(args.output_root, review, {r["record_id"] for r in rows})
    network = prefixes(args.output_root)
    result = {"built_at": DATE, "baseline_manifest": {"path": repo_ref(BASELINE), "sha256": sha256(BASELINE)},
        "scope": "AWS and Oracle GCC enrichment; canonical IDs and previous snapshots preserved",
        "canonical_location_additions": 0, "canonical_location_removals": 0,
        "reviewed_canonical_count": len(rows), "current_directory_reconfirmed_count": sum(r["last_seen"] == DATE for r in rows),
        "historical_unconfirmed_count": sum(r["last_seen"] != DATE for r in rows),
        "geometry_null_count": sum(r["latitude"] is None for r in rows), "refreshed_layers": refresh,
        "locality_count": locality["record_count"], "locality_held_count": locality["held_record_count"],
        "infrastructure_counts": infra["category_counts"], "network_record_count": network["record_count"],
        "saudi_launch_watch": {**review["aws_saudi_plan"], "review_due": "2026-10-26",
            "admission_rule": "Require explicit launch evidence and official region/AZ identifiers; geofeed or SDK registration alone is insufficient."},
        "listing_discrepancies": [review["aws_local_zones_reconciliation"], review["aws_cloudfront_reconciliation"]],
        "muscat_network_corroboration": network["muscat_border_group_evidence"],
        "remaining_gaps": ["Ten endpoint references lack verified street addresses; no physical-site count or geometry admitted.",
            "Only DX1 and MC1 have independent operator-code corroboration; other names remain source labels.",
            "Country-only AWS core regions and Bahrain edge label remain unlocated at city precision.",
            "Muscat Local Zone needs explicit status evidence; Fujairah CloudFront needs a current listing.",
            "No new routing, latency, DNS or application-origin observations were made.",
            "Public prefix feeds omit some services and are not complete infrastructure inventories."],
        "reproduce": "python3 -B scripts/update_gulf_enrichment.py"}
    write_json(args.output_root / f"data/gulf/enrichment-implementation.{TAG}.json", result)
    print(f"Gulf: {len(rows)} canonical rows reviewed; {locality['record_count']} locality points; {infra['record_count']} infrastructure assertions; {network['record_count']} prefix declarations")


if __name__ == "__main__":
    main()
