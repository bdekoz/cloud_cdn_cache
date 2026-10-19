#!/usr/bin/env python3
"""Normalize provider-declared Yandex zones, CDN cities and network evidence."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
from pathlib import Path

from location_common import REPO_ROOT
from network_common import canonical_network_record, write_network_layer
from review_russia_enrichment import yandex_review
from russia_enrichment_common import (DATE, TAG, evidence, location, publish_locations,
                                      raw_path, read, source)


def cloud_rows():
    review = yandex_review()
    rows = []
    for country, name, zones in (("RU", "Russia", review["cloud_zone_candidates"]),
                                  ("KZ", "Kazakhstan", [{"zone_id": z, "service_scope": "public_cloud"}
                                                          for z in review["separate_kazakhstan_zones"]])):
        region = location("regions", "yandex", "cloud_region", name, name,
                          "Yandex Cloud", "yandex_cloud", country=country, scope=["public_cloud"],
                          properties={"identity_basis": "provider_region_label", "current_health_verified": False})
        rows.append(region)
        for zone in zones:
            code = zone["zone_id"]
            rows.append(location("zones" if country == "RU" else "regions", "yandex", "availability_zone", code,
                code, "Yandex Cloud", "yandex_baremetal" if zone["service_scope"] == "baremetal" else "yandex_cloud",
                country=country, parent=region["record_id"], code=code, scope=[zone["service_scope"]],
                properties={"country_evidence": evidence("regions"), "current_health_verified": False,
                            "provider_status_ref": "data/russia/enrichment-assessment.20261019.json#/yandex/status_review"}))
    return rows


def city_rows():
    review = yandex_review()["cdn"]
    rows = []
    for declared_country, cities in review["source_country_labels"].items():
        for city in cities:
            corrected = city == "Simferopol"
            country = "UA" if corrected else declared_country
            properties = {"record_grain": "city_with_one_or_more_cdn_pops",
                          "source_country_label": declared_country, "current_health_verified": False,
                          "prefix_to_city_mapping_asserted": False}
            if corrected:
                properties.update(country_normalization="internationally_recognized_borders",
                                  country_normalization_evidence=evidence("country_policy"))
            rows.append(location("cdn_cities", "yandex", "edge_pop", f"cdn-{city}", city,
                                 "Yandex Cloud", "yandex_cdn", country=country, city=city,
                                 scope=["cdn"], properties=properties))
    return rows


def network_rows():
    review = yandex_review()
    groups = dict(review["public_ip_candidates"]["prefixes_by_service"])
    groups["cloud-cdn"] = read(raw_path("cdn_prefixes"))["prefixes"]
    rows = []
    for group, prefixes in groups.items():
        key = "cdn_prefixes" if group == "cloud-cdn" else "public_ips"
        item = source(key)
        service = "yandex_" + group.replace("-", "_")
        for prefix in prefixes:
            net = ipaddress.ip_network(prefix)
            identity = hashlib.sha256(f"{service}|{net}".encode()).hexdigest()[:24]
            rows.append(canonical_network_record(
                record_id=f"network:provider_prefix:yandex-{identity}", evidence_type="provider_prefix",
                subject_type="prefix", subject_id=str(net), provider="Yandex Cloud", service=service,
                prefix=str(net), ip_family=net.version, asn=None, relationship_type="declares_prefix",
                object_type="provider_service", object_id=service, status="published", source_scope="provider_declared",
                source_url=item["source_url"], raw_source_ref=item["raw_source_ref"], source_sha256=item["sha256"],
                source_published_at=item.get("source_published_at"), retrieved_at=DATE,
                observed_at=item["retrieved_at_utc"], valid_from=None, valid_to=None, confidence="high",
                properties={"service_role": group, "source_updated_at": item.get("source_updated_at"),
                            "physical_country_code": None, "network_location_not_asserted": True,
                            "customer_assignable": group in {"virtual-private-cloud", "baremetal"},
                            "customer_relationship_not_asserted": True}))
    item = source("yandex_routes")
    routing = read(raw_path("yandex_routes"))["data"]
    if routing["resource"] not in ("AS200350", "200350"):
        raise ValueError("Unexpected routing ASN")
    routes = []
    for entry in routing["prefixes"]:
        net = ipaddress.ip_network(entry["prefix"], strict=True)
        identity = hashlib.sha256(f"200350|{net}".encode()).hexdigest()[:24]
        routes.append(canonical_network_record(
            record_id=f"network:routing_origin:yandex-{identity}", evidence_type="routing_origin",
            subject_type="prefix", subject_id=str(net), provider="Yandex Cloud", service="yandex_cloud_network",
            prefix=str(net), ip_family=net.version, asn=200350, relationship_type="originates_prefix",
            object_type="asn", object_id="AS200350", status="announced", source_scope="observed",
            source_url=item["source_url"], raw_source_ref=item["raw_source_ref"], source_sha256=item["sha256"],
            source_published_at=None, retrieved_at=DATE, observed_at=routing["query_endtime"] + "Z",
            valid_from=None, valid_to=None, confidence="high", properties={
                "query_starttime": routing["query_starttime"], "query_endtime": routing["query_endtime"],
                "timelines": entry["timelines"], "physical_country_code": None,
                "service_membership_not_inferred": True, "asn_identity_evidence": evidence("yandex_asn")}))
    return rows, routes


def run(root: Path):
    publish_locations(root, "yandex/regions-and-zones", cloud_rows(), "regions",
        enrichment_sources=[evidence("zones") | {"source_scope": "provider_declared"}],
        current_health_not_asserted=True)
    publish_locations(root, "yandex/cdn-cities", city_rows(), "cdn_cities",
        source_global_pop_claim=78, record_unit="provider_declared_city", country_normalization_exception_count=1,
        enrichment_sources=[evidence("country_policy") | {"source_scope": "inferred"}])
    for name, rows in zip(("yandex-prefixes", "yandex-routing"), network_rows()):
        write_network_layer(records=rows, layer_name=name, retrieved_at=DATE,
                            parser_name="update_yandex.py", output_root=root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    run(parser.parse_args().output_root)
