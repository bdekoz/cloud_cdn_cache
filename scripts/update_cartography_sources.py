#!/usr/bin/env python3
"""Rebuild the 2026-10-19 Akamai restoration and Apple DNS city observations.

Offline: every input is retained in the canonical infrastructure repository.
The Akamai date is the normalization date, not a new deployment survey.
Apple records have city-presence grain; endpoint counts are evidence metadata.
"""
from __future__ import annotations

import csv
import ipaddress
import json
from collections import defaultdict
from pathlib import Path

from location_common import (
    REPO_ROOT, SCHEMA_VERSION, canonical_record, country_identity, repo_ref,
    sha256, slug, write_json, write_layer,
)

DATE = "2026-10-19"
TAG = "20261019"
RAW = REPO_ROOT / "data/raw/cartography-restoration"
AKAMAI = RAW / "akamai-legacy.20230713.geojson"
APPLE = RAW / "apple-geofeed.20261019.csv"
OBSERVATIONS = [RAW / f"doh-ipv{version}.20261019.txt" for version in (4, 6)]
DNS = RAW / "apple-doh-dns.20261019.json"
SELECTION = RAW / "apple-dns-city-selection.20261019.json"
GEONAMES = RAW / "apple-dns-geonames.20261019.tsv"
HOSTS = {"doh.dns.apple.com", "doh.dns.apple.com.v.aaplimg.com", "doh-dns-apple-com.v.aaplimg.com"}


def source(path):
    p = json.loads(path.with_suffix(path.suffix + ".provenance.json").read_text())
    assert p["sha256"] == sha256(path), path
    return {"raw_source_ref": repo_ref(path), "source_sha256": sha256(path),
            "source_url": p["source_url"], "source_published_at": p["source_published_at"],
            "source_scope": "observed"}


def base(raw, **kwargs):
    s = source(raw)
    s.pop("source_scope")
    return canonical_record(
        schema_version=SCHEMA_VERSION, aliases=[], site_code=None,
        source_scope="observed", retrieved_at=DATE, first_seen=DATE, last_seen=DATE,
        confidence="medium", metro=None, **s, **kwargs)


def akamai_records():
    records = []
    aliases = {"Saint Lucia": ("Saint Lucia", "LC"), "Myanmar": ("Myanmar", "MM"),
               "Trinidad and Tobago": ("Trinidad and Tobago", "TT")}
    for index, feature in enumerate(json.loads(AKAMAI.read_text())["features"], 1):
        p = feature["properties"]
        assert p["Provider"] == "Akamai"
        assert feature["geometry"]["type"] == "Point"
        lon, lat = feature["geometry"]["coordinates"]
        country, code = aliases.get(p["Country"], country_identity(p["Country"]))
        assert code, p["Country"]
        records.append(base(AKAMAI,
            record_id=f"akamai:legacy-20230713:{index:04d}", provider="Akamai",
            service=f"akamai_{p['Service Name']}", entity_type="edge_pop",
            service_scope=["cdn"], source_collection="akamai_legacy_20230713",
            source_record_id=str(index), name=f"{p['City']} — {p['Service Name']}",
            lifecycle_status={"existing": "operational", "planned": "planned"}[p["Status"]],
            city=p["City"], subdivision=None, country=country, country_code=code,
            latitude=lat, longitude=lon, location_precision="city", coordinate_method="legacy",
            properties={"legacy_properties": p, "legacy_feature_index": index,
                "legacy_path": "data/akamai_13-07-2023.geojson",
                "evidence_vintage": "2023-07-13", "revalidated_current_deployment": False,
                "scope_note": "Historical city coordinates and lifecycle retained; normalization is not a 2026 deployment confirmation."}))
    return records


def endpoint_evidence():
    endpoints = defaultdict(list)
    for path in OBSERVATIONS:
        source(path)
        for number, line in enumerate(path.read_text().splitlines(), 1):
            address, sep, comment = line.partition("#")
            if not sep or not HOSTS.intersection(x.strip() for x in comment.split(",")):
                continue
            ip = str(ipaddress.ip_address(address.strip()))
            endpoints[ip].append({"raw_source_ref": repo_ref(path), "line": number})
    source(DNS)
    for answer in json.loads(DNS.read_text())["Answer"]:
        if answer["type"] in (1, 28):
            ip = str(ipaddress.ip_address(answer["data"]))
            endpoints[ip].append({"raw_source_ref": repo_ref(DNS), "dns_type": answer["type"]})
    return endpoints


def apple_records():
    endpoints = endpoint_evidence()
    networks = []
    for number, row in enumerate(csv.reader(APPLE.open()), 1):
        if row and not row[0].startswith("#"):
            networks.append((ipaddress.ip_network(row[0]), row, number))
    rows = {r[0]: r for r in csv.reader(GEONAMES.open(), delimiter="\t")}
    selection = json.loads(SELECTION.read_text())
    places = {(p["country_code"], p["subdivision"], p["geofeed_city"]): p
              for p in selection["places"]}
    grouped = defaultdict(list)
    held = []
    for ip, evidence in sorted(endpoints.items()):
        address = ipaddress.ip_address(ip)
        matches = [(net, row, number) for net, row, number in networks
                   if address.version == net.version and address in net]
        if not matches:
            held.append({"ip": ip, "reason": "no_apple_geofeed_match", "evidence": evidence})
            continue
        specific = max(n.prefixlen for n, _, _ in matches)
        matches = [(n, r, i) for n, r, i in matches if n.prefixlen == specific]
        keys = {tuple(r[1:4]) for _, r, _ in matches}
        if len(keys) != 1:
            held.append({"ip": ip, "reason": "conflicting_most_specific_geofeed_rows", "evidence": evidence})
            continue
        key = next(iter(keys))
        if key not in places:
            held.append({"ip": ip, "reason": "city_identity_not_reviewed", "geofeed_place": key, "evidence": evidence})
            continue
        grouped[key].append({"ip": ip, "evidence": evidence,
            "geofeed_matches": [{"prefix": str(n), "line": i} for n, _, i in matches]})
    records = []
    for (code, subdivision, city), observations in sorted(grouped.items()):
        place = places[(code, subdivision, city)]
        row = rows[place["geonames_id"]]
        assert row[8] == code and (row[10] == subdivision[3:] if code == "US" else row[10] == "08")
        country = {"US": "United States", "CA": "Canada"}[code]
        identifier = f"{code.lower()}-{slug(subdivision)}-{slug(city)}"
        records.append(base(APPLE,
            record_id=f"apple:dns-city:{identifier}", provider="Apple", service="dns_over_https",
            entity_type="observed_presence", service_scope=["dns_over_https"],
            source_collection="apple_doh_city_observations", source_record_id=identifier,
            name=f"{city} — Apple DNS over HTTPS", lifecycle_status="unknown",
            city=city, subdivision=subdivision, country=country, country_code=code,
            latitude=float(row[4]), longitude=float(row[5]), location_precision="city",
            coordinate_method="geocoded", properties={
                "hostname": "doh.dns.apple.com", "grain": "distinct_observed_dns_city",
                "endpoint_count": len(observations), "endpoint_evidence": observations,
                "geonames_id": row[0], "coordinate_source_ref": repo_ref(GEONAMES),
                "coordinate_source_sha256": sha256(GEONAMES), "selection_ref": repo_ref(SELECTION),
                "selection_sha256": sha256(SELECTION), "physical_site_confirmed": False,
                "scope_note": "Partial DNS endpoint geography from observed addresses joined to Apple's most-specific geofeed city. City centroid, not a facility or content cache; endpoint multiplicity is not a site count."}))
    audit = {"retrieved_at": DATE, "observed_endpoint_count": len(endpoints),
        "located_endpoint_count": sum(len(x) for x in grouped.values()),
        "held_endpoint_count": len(held), "held_endpoints": held,
        "city_record_count": len(records), "country_codes": sorted({r["country_code"] for r in records}),
        "grain": "one record per distinct observed DNS city, independent of IP count",
        "method": "Exact hostname tokens; IPv4 and IPv6; longest-prefix Apple geofeed join; explicit GeoNames identity selection.",
        "scope_note": "Resolver vantage bias and incomplete observations. Four shared anycast addresses have no Apple geofeed city. PCH's entire POP list and the unitemized 236-location aggregate are not promoted to Apple sites.",
        "sources": [source(p) for p in [APPLE, *OBSERVATIONS, DNS, GEONAMES, SELECTION,
            RAW / "apple-service-documentation.20261019.json", RAW / "cdn-mapping-study.20261019.json"]]}
    return records, audit


def main():
    akamai = akamai_records()
    apple, audit = apple_records()
    for layer, records, raw, extra in [
        ("akamai/legacy-locations", akamai, AKAMAI, {"evidence_vintage": "2023-07-13",
            "normalization_only": True, "scope_note": "Restores retained 2023 geography, including 61 planned rows. No 2026 deployment verification."}),
        ("apple/dns-cities", apple, APPLE, {"endpoint_audit": "data/apple/dns-endpoint-audit.20261019.json",
            "enrichment_sources": audit["sources"], "scope_note": audit["scope_note"]})]:
        directory, name = layer.split("/")
        write_layer(records=records, output_dir=REPO_ROOT / "data" / directory,
            layer_name=name, retrieved_at=DATE, source_url=source(raw)["source_url"],
            raw_path=raw, parser_name="scripts/update_cartography_sources.py", extra_report=extra)
    write_json(REPO_ROOT / "data/apple/dns-endpoint-audit.20261019.json", audit)
    print(json.dumps({"akamai_records": len(akamai), "apple_city_records": len(apple),
        "apple_located_endpoints": audit["located_endpoint_count"], "apple_held_endpoints": audit["held_endpoint_count"]}))


if __name__ == "__main__":
    main()
