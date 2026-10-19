#!/usr/bin/env python3
"""Check source fidelity, conservative joins, complete gap accounting and offline replay."""
from __future__ import annotations

from collections import Counter
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from location_common import load_validator, sha256
from network_common import validate_network_collection
from update_completion_enrichment import BASELINE, CATALOG, DATE, INFRA, TAG, VIEW, external_ids, read
from update_infrastructure import validate_collection


def hashes(value):
    if isinstance(value, dict):
        if value.get("source_sha256") and value.get("raw_source_ref"):
            assert sha256(ROOT / value["raw_source_ref"]) == value["source_sha256"]
        for v in value.values():
            hashes(v)
    elif isinstance(value, list):
        for v in value:
            hashes(v)


def projection(path, script, schema=None):
    cmd = ["jq", "-r"]
    if schema:
        cmd += ["--slurpfile", "schema", str(ROOT / "schema" / schema)]
    cmd += ["-f", str(ROOT / "scripts" / script), str(path)]
    return list(csv.DictReader(io.StringIO(subprocess.check_output(cmd, text=True))))


def main():
    assert sha256(BASELINE) == "041bc3b47fe004256c8c7066472d5da31b81cd7872a0b8d81366c3ba1008c127"
    before, current = read(BASELINE), read(ROOT / f"data/manifest.{TAG}.json")
    for key in ["layers", "views", "vendor_registry", "application_endpoint_layers", "observation_comparison_views"]:
        assert current[key] == before[key], key
    assert (current["record_count"], current["layer_count"]) == (28024, 39)
    for key in ["infrastructure_evidence_layers", "network_evidence_layers", "geographic_footprint_views"]:
        assert current[key][:-1] == before[key]
    assert current["infrastructure_evidence_record_count"] == 400
    assert current["network_evidence_record_count"] == 3975
    assert current["geographic_footprint_view_count"] == 3
    for key in ["layers", "views", "infrastructure_evidence_layers", "network_evidence_layers", "geographic_footprint_views"]:
        for layer in current[key]:
            for item in layer["files"].values():
                assert sha256(ROOT / item["path"]) == item["sha256"]

    catalog = read(CATALOG)
    for s in catalog["sources"]:
        if s["result"] == "retrieved":
            assert sha256(ROOT / s["path"]) == s["sha256"]
            assert read(ROOT / (s["path"] + ".provenance.json")) == s
        else:
            assert s["error"] and not s.get("path")
    infra = read(ROOT / INFRA)
    validate_collection(infra, external_record_ids=external_ids())
    rows = infra["records"]
    assert len(rows) == 76
    assert Counter(r["category"] for r in rows) == {
        "project_approval_reference": 21, "property_title_reference": 4,
        "phase_status_disclosure": 3, "historical_cdn_city_declaration": 10,
        "facility_address_registration": 5, "campus_activity_disclosure": 2,
        "cloud_access_latency_measurement": 31}
    assert all(r["geometry"] is None and r["lifecycle_status"] == "unknown" for r in rows)
    assert all(r["properties"]["physical_site_count_not_asserted"] for r in rows)
    for r in rows:
        p = r["properties"]
        if r["category"] == "project_approval_reference":
            assert p["public_site_code"] is None and p["operation_not_inferred_from_approval"]
            assert r["parties"][0]["name"] == p["legal_entity"]
        if r["category"] == "historical_cdn_city_declaration":
            assert p["current_deployment_not_established"] and p["claim_as_of"] is None
            assert p["map_copyright_year"] == 2024 and p["marker_status_as_depicted"] == "active"
    cst = [r for r in rows if r["category"] == "cloud_access_latency_measurement"]
    assert len({r["provider"] for r in cst}) == 19
    assert {r["properties"]["locality"]: r["properties"]["country_weighted_average_ms"]
            for r in cst if r["provider"] == "Oracle"} == {"Riyadh": 19, "Jeddah": 20}
    assert all(r["properties"]["report_period"] == "2026-H1" and r["properties"]["october_health_not_asserted"] for r in cst)
    registry = [r for r in rows if r["category"] == "facility_address_registration"]
    assert len({rel["target_record_id"] for r in registry for rel in r["relationships"]}) == 5
    assert all("center3" not in rel["target_record_id"] for r in registry for rel in r["relationships"])
    exported = projection(ROOT / INFRA, "infrastructure-json-to-csv.jq", "infrastructure-evidence.schema.json")
    assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in rows]

    view = read(ROOT / VIEW)
    load_validator(ROOT / "schema/geographic-footprint.schema.json").validate(view)
    assert len(view["features"]) == 13
    assert Counter(f["properties"]["vendor_id"] for f in view["features"]) == {"tata": 10, "huawei": 1, "tencent": 1, "chindata": 1}
    ids = {r["record_id"] for r in rows}
    for f in view["features"]:
        p = f["properties"]
        assert not p["physical_site_confirmed"] and p["excluded_from_canonical_totals"]
        assert set(p["source_claim_ids"]) <= ids
        assert set(p["source_record_ids"]) <= external_ids()
        if p["locality"] == "Nantong":
            assert p["gazetteer"]["geonames_id"] == "1799722" and p["gazetteer"]["admin1"] == "04"
    assert len(projection(ROOT / VIEW, "geographic-footprint-to-csv.jq")) == 13
    all_footprints = [f["properties"]["footprint_id"] for layer in current["geographic_footprint_views"]
                      for f in read(ROOT / layer["files"]["geojson"]["path"])["features"]]
    assert len(all_footprints) == len(set(all_footprints)) == 169

    network_path = ROOT / f"data/network/gulf-routing-review.{TAG}.json"
    net = read(network_path)
    validate_network_collection(net)
    assert Counter(r["status"] for r in net["records"]) == {"announced": 12, "not_announced": 1, "valid": 12}
    assert all(r["properties"]["service_health_not_asserted"] and r["properties"]["physical_location_not_asserted"] for r in net["records"])
    assert all(r["observed_at"] for r in net["records"])
    prefix_ids = {r["record_id"] for r in read(ROOT / f"data/network/gulf-provider-prefixes.{TAG}.json")["records"]}
    assert {r["properties"]["provider_prefix_record_id"] for r in net["records"]} <= prefix_ids
    assert len(projection(network_path, "network-json-to-csv.jq", "network-evidence.schema.json")) == 25

    review = read(ROOT / f"data/enrichment/completion-review.{TAG}.json")
    assert len(review["china_held_record_dispositions"]) == 24
    assert Counter(r["disposition"] for r in review["china_held_record_dispositions"])["resolved_in_supplement"] == 2
    assert Counter(r["disposition"] for r in review["china_held_record_dispositions"])["excluded_multi_region_container"] == 2
    assert len(review["china_vendor_cohort"]) == 31
    assert len(review["gulf_endpoint_dispositions"]) == 10
    assert sum(r["address_disposition"] == "no_verified_address" for r in review["gulf_endpoint_dispositions"]) == 8
    assert review["workflow_receipt"]["conclusion"] == "success"
    assert review["yandex_status_source_updated_at"] == "2026-10-11"
    assert all(t["additional_evidence_required"] for t in review["tasks"] if t["disposition"] != "implemented")
    assert sha256(CATALOG) == review["source_catalog"]["sha256"]
    for value in [infra, view, net, review]:
        hashes(value)
    bibliography = read(ROOT / f"data/references/bibliography.{TAG}.json")
    assert bibliography["reference_count"] == len(bibliography["references"]) == 209
    assert len({r["reference_id"] for r in bibliography["references"]}) == 209
    assert {s["source_id"] for s in catalog["sources"]} <= {r["source_id"] for r in bibliography["references"]}

    # Reproduction must neither change captured inputs/metadata nor depend on network access.
    retained = {p: sha256(p) for p in (ROOT / "data/raw/completion-review").glob("*") if p.is_file()}
    with tempfile.TemporaryDirectory(prefix="completion-reproduction-") as temp:
        subprocess.run([sys.executable, "-B", "scripts/update_completion_enrichment.py", "--output-root", temp], cwd=ROOT, check=True)
        for p in Path(temp).rglob("*"):
            if p.is_file():
                assert p.read_bytes() == (ROOT / p.relative_to(temp)).read_bytes(), p
    assert all(sha256(p) == digest for p, digest in retained.items())
    print("Completion checks passed: 76 scoped assertions, 13 locality points, 25 routing/RPKI records, all gap dispositions, hosted success and unchanged historical inputs.")


if __name__ == "__main__":
    main()
