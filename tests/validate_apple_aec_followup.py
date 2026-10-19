#!/usr/bin/env python3
"""Guard the boundary between Apple CDN classifications, routing and cache sites."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from location_common import sha256
from network_common import validate_network_collection
from update_apple_aec_followup import BASELINE, CATALOG, INFRA, RAW, REVIEW, TAG, read, sources
from update_infrastructure import validate_collection
from validate_apple_tv import hashes, projection


def main():
    assert sha256(BASELINE) == "ae9cd07ed8944182ab180d2efb8773fee7643632c78b5c40d9f21c02f40e27ca"
    old, current = read(BASELINE), read(ROOT / f"data/manifest.{TAG}.json")
    changed = {"network_evidence_layer_count", "network_evidence_record_count", "network_evidence_layers",
               "infrastructure_evidence_layer_count", "infrastructure_evidence_record_count", "infrastructure_evidence_layers",
               "assessments", "bibliography"}
    assert current.keys() == old.keys()
    for key in current.keys() - changed:
        assert current[key] == old[key], key
    for key in ["network_evidence_layers", "infrastructure_evidence_layers", "assessments"]:
        assert current[key][:-1] == old[key]
    assert current["network_evidence_record_count"] == old["network_evidence_record_count"] + 10 == 3989
    assert current["infrastructure_evidence_record_count"] == old["infrastructure_evidence_record_count"] + 3 == 429
    for key in ["layers", "views", "network_evidence_layers", "infrastructure_evidence_layers", "geographic_footprint_views"]:
        for layer in current[key]:
            for item in layer["files"].values():
                assert sha256(ROOT / item["path"]) == item["sha256"]

    catalog = sources()  # Every body and its metadata must match the captured catalog.
    assert len(catalog) == 27
    assert Counter(s["result"] for s in catalog.values()) == {"retrieved": 26, "http_error": 1}
    assert catalog["sfmix-2025-topology"]["http_status"] == 404
    review = read(ROOT / REVIEW)
    assert review["source_catalog"]["sha256"] == sha256(CATALOG)
    candidates = review["candidates"]
    assert review["candidate_count"] == len(candidates) == len({r["candidate_id"] for r in candidates}) == 40
    assert review["candidate_kind_counts"] == {
        "apple_network_scope_only": 7, "hosting_classification_not_aec_evidence": 12,
        "isp_partner_candidate": 11, "other_asn_candidate": 10}
    assert review["country_candidate_counts"] == {"AE": 2, "AU": 21, "HU": 3, "IN": 8, "RU": 3, "UA": 3}
    assert all(r["geometry"] is None and r["location_admission"] == "held" for r in candidates)
    assert all(not r["aec_deployment_verified"] and not r["apple_tv_delivery_verified"] for r in candidates)
    assert all(r["publisher_observed_at"] is None for r in candidates)
    assert all(r["ip_count_is_not_appliance_count"] for r in candidates)
    assert all(r["city_label"] is None for r in candidates if r["asn"] is not None)
    assert len([r for r in candidates if r["sample_ip"] is None and r["sample_prefix"] is None]) == 8
    assert all(r["candidate_kind"] == "hosting_classification_not_aec_evidence" for r in candidates if r["country_code"] == "AE")
    assert review["unlisted_priority_country_codes"] == ["CN", "SA"]
    assert review["cache_map_points_added"] == review["canonical_records_added"] == 0
    assert len(review["prior_unlocated_hosts"]) == 7
    historical = [r["earlier_apple_asn_observation"] for r in candidates if r["asn"]]
    assert sum(r["record_id"] is not None for r in historical) == 1
    assert all(sha256(ROOT / r["path"]) == r["sha256"] for r in historical)

    infra = read(ROOT / INFRA)
    validate_collection(infra)
    assert len(infra["records"]) == 3
    assert all(r["geometry"] is None and r["lifecycle_status"] == "unknown" for r in infra["records"])
    giganet = next(r for r in infra["records"] if r["record_id"].endswith(":giganet-hu"))
    assert giganet["properties"]["claim_year"] == 2024
    assert giganet["properties"]["locality"] is None
    assert giganet["properties"]["same_name_ukrainian_operator_not_joined"]
    exported = projection(INFRA, "infrastructure-json-to-csv.jq", "infrastructure-evidence.schema.json")
    assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in infra["records"]]

    net_path = f"data/network/apple-aec-candidate-routing.{TAG}.json"
    network = read(ROOT / net_path)
    validate_network_collection(network)
    assert len(network["records"]) == 10
    assert {r["properties"]["candidate_id"] for r in network["records"]} == {r["candidate_id"] for r in candidates if r["asn"]}
    assert all(r["properties"]["address_basis"] == "third_party_classification_not_http_peer" for r in network["records"])
    assert all(r["properties"]["physical_location_not_asserted"] and r["properties"]["aec_deployment_not_established"] for r in network["records"])
    mismatches = [r for r in network["records"] if not r["properties"]["reported_asn_is_observed_origin"]]
    assert len(mismatches) == 1
    r = mismatches[0]
    assert (r["properties"]["sample_address"], r["properties"]["reported_asn"], r["asn"], r["prefix"]) == (
        "88.209.219.16", 42864, 31128, "88.209.219.0/27")
    registry = review["registry_identity"]
    assert registry["registry_name"] == "SHAZAM-AS"
    assert registry["registrant_organizations"] == [{"handle": "ORG-ADIL1-RIPE", "name": "Apple Distribution International Ltd."}]
    assert registry["cache_service_or_location_not_established"]
    exported = projection(net_path, "network-json-to-csv.jq", "network-evidence.schema.json")
    assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in network["records"]]
    for value in [review, infra, network]:
        hashes(value)

    frozen_bib = ROOT / f"data/raw/repository/bibliography-before-apple-aec-followup.{TAG}.json"
    assert sha256(frozen_bib) == old["bibliography"]["files"]["json"]["sha256"]
    before, after = read(frozen_bib), read(ROOT / "data/references/bibliography.20261019.json")
    original = {r["reference_id"]: r for r in before["references"]}
    refs = {r["reference_id"]: r for r in after["references"]}
    assert len(original) == 268 and len(refs) == after["reference_count"] == 295
    assert all(refs.get(key) == value for key, value in original.items())
    assert {r["source_id"] for key, r in refs.items() if key not in original} == set(catalog)
    assert next(r for r in refs.values() if r["source_id"] == "sfmix-2025-topology")["usage"] == "failed_retrieval_receipt_no_evidence_admitted"

    retained = {p: sha256(p) for directory in [RAW, ROOT / "data/raw/apple-tv"] for p in directory.iterdir() if p.is_file()}
    with tempfile.TemporaryDirectory(prefix="apple-aec-followup-") as temp:
        subprocess.run([sys.executable, "-B", "scripts/update_apple_aec_followup.py", "--output-root", temp], cwd=ROOT, check=True)
        for p in Path(temp).rglob("*"):
            if p.is_file():
                assert p.read_bytes() == (ROOT / p.relative_to(temp)).read_bytes(), p
    assert all(sha256(p) == digest for p, digest in retained.items())
    print("Apple cache follow-up checks passed: 40 unlocated classifications, 10 routing samples, host/origin distinction, 3 scoped assertions, 27 references and unchanged cache maps.")


if __name__ == "__main__":
    main()
