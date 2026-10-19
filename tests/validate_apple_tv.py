#!/usr/bin/env python3
"""Validate Apple delivery evidence, conservative cache mapping and offline replay."""
from __future__ import annotations

from collections import Counter
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from location_common import load_validator, sha256
from network_common import validate_network_collection
from update_apple_tv import ASSESSMENT, BASELINE, CATALOG, CDNS, INFRA, TAG, VIEW, read, sources
from update_apple_aec import INFRA as AEC_INFRA, REVIEW as AEC_REVIEW, VIEW as AEC_VIEW
from update_infrastructure import validate_collection


def hashes(value):
    if isinstance(value, dict):
        if value.get("source_sha256") and value.get("raw_source_ref"):
            assert sha256(ROOT / value["raw_source_ref"]) == value["source_sha256"]
        for child in value.values():
            hashes(child)
    elif isinstance(value, list):
        for child in value:
            hashes(child)


def projection(path, script, schema=None):
    args = ["jq", "-r"]
    if schema:
        args += ["--slurpfile", "schema", str(ROOT / "schema" / schema)]
    args += ["-f", str(ROOT / "scripts" / script), str(ROOT / path)]
    return list(csv.DictReader(io.StringIO(subprocess.check_output(args, text=True))))


def check_boundaries():
    assert sha256(BASELINE) == "c06527415def65023f40211790d322efa23a3f776630f9688684d078a21caf35"
    old, current = read(BASELINE), read(ROOT / f"data/manifest.{TAG}.json")
    changed = {"network_evidence_layer_count", "network_evidence_record_count", "network_evidence_layers",
               "infrastructure_evidence_layer_count", "infrastructure_evidence_record_count", "infrastructure_evidence_layers",
               "geographic_footprint_view_count", "geographic_footprint_views", "assessments", "bibliography"}
    assert current.keys() == old.keys()
    for key in current.keys() - changed:
        assert current[key] == old[key], key
    for key, added in [("network_evidence_layers", 1), ("infrastructure_evidence_layers", 2),
                       ("geographic_footprint_views", 2), ("assessments", 2)]:
        assert current[key][:-added] == old[key], key
    assert (current["record_count"], current["layer_count"]) == (28024, 39)
    assert current["network_evidence_record_count"] - old["network_evidence_record_count"] == 4
    assert current["infrastructure_evidence_record_count"] - old["infrastructure_evidence_record_count"] == 26
    assert current["geographic_footprint_view_count"] == 5
    for key in ["layers", "views", "network_evidence_layers", "infrastructure_evidence_layers", "geographic_footprint_views"]:
        for layer in current[key]:
            for item in layer["files"].values():
                assert sha256(ROOT / item["path"]) == item["sha256"]

    frozen_bib = ROOT / f"data/raw/repository/bibliography-before-apple-tv.{TAG}.json"
    assert sha256(frozen_bib) == old["bibliography"]["files"]["json"]["sha256"]
    before, after = read(frozen_bib), read(ROOT / current["bibliography"]["files"]["json"]["path"])
    originals = {r["reference_id"]: r for r in before["references"]}
    refs = {r["reference_id"]: r for r in after["references"]}
    assert len(refs) == len(after["references"]) == after["reference_count"] == 268
    assert len(originals) == 209
    assert all(refs.get(key) == value for key, value in originals.items())
    additions = [r for key, r in refs.items() if key not in originals]
    assert {r["source_id"] for r in additions} == set(sources())
    failed = next(r for r in additions if r["source_id"] == "aec-peeringdb-network")
    assert failed["usage"] == "failed_retrieval_receipt_no_evidence_admitted"
    assert next(r for r in additions if r["source_id"] == "aec-peeringdb-fac")["availability"] == "unavailable"


def main():
    check_boundaries()
    catalog = sources()  # Checks every retained body digest and exact sidecar/catalog agreement.
    assert len(catalog) == len(read(CATALOG)["sources"]) == 59
    assert Counter(s["result"] for s in catalog.values()) == {"retrieved": 57, "http_error": 1, "unavailable": 1}
    assert all("set-cookie" not in s.get("response_headers", {}) for s in catalog.values())
    assert {urlparse(s["source_url"]).path.rsplit(".", 1)[-1]
            for s in catalog.values() if s["source_id"].startswith(("tv-preview-", "tv-variant-"))} == {"m3u8"}

    infra, aec = read(ROOT / INFRA), read(ROOT / AEC_INFRA)
    all_rows = infra["records"] + aec["records"]
    rows = {r["record_id"]: r for r in all_rows}
    assert len(rows) == len(all_rows) == 26
    admitted_refs = {s["path"] for s in catalog.values() if s["result"] == "retrieved"}
    for collection, path in [(infra, INFRA), (aec, AEC_INFRA)]:
        validate_collection(collection)
        assert all(r["geometry"] is None and r["lifecycle_status"] == "unknown" for r in collection["records"])
        assert all(r["raw_source_ref"].removesuffix(".provenance.json") in admitted_refs for r in collection["records"])
        exported = projection(path, "infrastructure-json-to-csv.jq", "infrastructure-evidence.schema.json")
        assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in collection["records"]]
    assert Counter(r["category"] for r in infra["records"]) == {"media_delivery_path": 6,
        "service_delivery_observation": 6, "service_endpoint_reference": 3, "cdn_pop_observation": 1,
        "cache_host_declaration": 1, "peering_status_reference": 1}
    assert Counter(r["category"] for r in aec["records"]) == {
        "cache_host_declaration": 3, "cache_exchange_reference": 4, "cache_pilot_reference": 1}

    tv_review, aec_review = read(ROOT / ASSESSMENT), read(ROOT / AEC_REVIEW)
    assert len(tv_review["sampled_master_playlists"]) == 2
    for master in tv_review["sampled_master_playlists"]:
        assert (master["content_type"], master["entitlement_reason"]) == ("Preview", "Free")
        assert set(master["advertised_cdn_hosts"]) == set(CDNS)
    assert tv_review["advertised_video_cdns"] == ["Akamai", "Apple", "Fastly"]
    assert tv_review["video_renditions_identical"]
    assert len({catalog["tv-variant-" + host.split(".")[0]]["sha256"] for host in CDNS}) == 1
    for host, (provider, code) in CDNS.items():
        record = rows["apple:tv:tv-variant-" + host.split(".")[0]]
        assert record["provider"] == provider and record["raw_source_ref"].endswith(".provenance.json")
        assert record["properties"]["response_headers"]["cdn-server"] == code
        assert record["properties"]["http_status"] == 200
        assert record["properties"]["observed_at"] == catalog["tv-variant-" + host.split(".")[0]]["captured_at"]
    assert tv_review["apple_http_peer_geofeed_match"] is None
    dns = tv_review["delivery_resolution_observations"]
    assert len(dns) == 16 and all(r["ecs"] == "0.0.0.0/0" for r in dns)
    apple_a = next(r for r in dns if r["hostname"] == "vod-ap-aoc.tv.apple.com" and r["rrtype"] == "A")
    assert apple_a["addresses"][0]["provider_geofeed_match"]["city"] == "Chicago"

    net_path = f"data/network/apple-tv-routing.{TAG}.json"
    net = read(ROOT / net_path)
    validate_network_collection(net)
    assert {(r["properties"]["sample_address"], r["asn"], r["properties"]["address_basis"]) for r in net["records"]} == {
        ("149.112.115.176", 40271, "http_peer"), ("23.192.228.8", 20940, "http_peer"),
        ("151.101.3.6", 54113, "http_peer"), ("17.253.27.156", 6185, "resolver_answer")}
    assert all(r["properties"]["physical_location_not_asserted"] for r in net["records"])
    exported = projection(net_path, "network-json-to-csv.jq", "network-evidence.schema.json")
    assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in net["records"]]

    sfmix = rows["apple:tv:sfmix-aec-scl02"]["properties"]
    assert sfmix["site_code"] == "SCL02" and sfmix["locality"] == "Santa Clara"
    assert sfmix["participant_status"] == "Inactive" and not sfmix["sampled_peer_to_site_mapping_asserted"]
    lyon = rows["apple:aec:franceix-lyon"]["properties"]
    assert lyon["cache_hardware_count"] == 2 and lyon["cache_site_count"] is None
    assert lyon["claim_period"] == "2025-Q2" and not lyon["aec_program_identity_explicit"]
    assert lyon["presentation_claim_date"] == "2025-06-19" and lyon["locality_corroboration_evidence"]["page"] == 5
    assert not lyon["apple_tv_delivery_established"] and lyon["current_operation_not_verified"]
    assert rows["apple:aec:cenet"]["source_published_at"] == "2023-12-04"
    assert rows["apple:aec:tenet"]["source_published_at"] == "2026-09-16"
    assert len(aec_review["locality_dispositions"]) == 9
    held = {r["record_id"] for r in aec_review["locality_dispositions"] if r["disposition"].startswith("held_")}
    assert len(held) == 7
    assert aec_review["explicitly_named_aec_localities"] == aec_review["apple_cache_localities_program_unconfirmed"] == 1
    views = []
    for path, expected in [(VIEW, {("Apple", "Santa Clara"), ("Fastly", "Palo Alto")}),
                           (AEC_VIEW, {("Apple", "Santa Clara"), ("Apple", "Lyon")})]:
        view = read(ROOT / path)
        views.append(view)
        load_validator(ROOT / "schema/geographic-footprint.schema.json").validate(view)
        assert {(f["properties"]["provider"], f["properties"]["locality"]) for f in view["features"]} == expected
        exported = projection(path, "geographic-footprint-to-csv.jq")
        for feature, projected in zip(view["features"], exported, strict=True):
            p = feature["properties"]
            assert p["coordinate_method"] == "gazetteer_reference_point" and p["excluded_from_canonical_totals"]
            assert p["lifecycle_status"] == "not_assessed" and not p["physical_site_confirmed"]
            assert set(p["source_claim_ids"]) <= rows.keys() and held.isdisjoint(p["source_claim_ids"])
            assert not p["source_record_ids"]
            assert feature["geometry"]["coordinates"] == [float(projected["longitude"]), float(projected["latitude"])]
            for key in ["source_claim_ids", "source_record_ids", "evidence", "gazetteer"]:
                assert json.loads(projected[key]) == p[key]
            assert p["locality"] != "Chicago"
        if path == AEC_VIEW:
            assert "program name unconfirmed" in next(f["properties"]["service"] for f in view["features"] if f["properties"]["locality"] == "Lyon")
    for value in [infra, aec, net, tv_review, aec_review, *views]:
        hashes(value)
    assert tv_review["source_catalog"]["sha256"] == aec_review["source_catalog"]["sha256"] == sha256(CATALOG)

    retained = {p: sha256(p) for p in (ROOT / "data/raw/apple-tv").glob("*") if p.is_file()}
    with tempfile.TemporaryDirectory(prefix="apple-delivery-reproduction-") as temp:
        for script in ["update_apple_tv.py", "update_apple_aec.py"]:
            subprocess.run([sys.executable, "-B", "scripts/" + script, "--output-root", temp], cwd=ROOT, check=True)
        for p in Path(temp).rglob("*"):
            if p.is_file():
                assert p.read_bytes() == (ROOT / p.relative_to(temp)).read_bytes(), p
    assert all(sha256(p) == digest for p, digest in retained.items())
    print("Apple checks passed: 26 scoped assertions, 4 routing samples, two overlapping locality views, 7 held leads, 59 references and deterministic offline reproduction.")


if __name__ == "__main__":
    main()
