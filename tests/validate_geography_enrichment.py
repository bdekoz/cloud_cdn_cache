#!/usr/bin/env python3
"""Check lineage, locality precision, held evidence, Gulf distinctions and rebuilding."""
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from geography_enrichment_common import BASELINE, CATALOG, CLOUD_LAYERS, RAW, TAG, baseline_layers, read, source
from location_common import load_validator, sha256, validate_records
from update_geography_enrichment import gazetteer, REGIONAL_KEYS, SCHEMA


def evidence_hashes(value):
    if isinstance(value, dict):
        if value.get("raw_source_ref") and value.get("source_sha256"):
            assert sha256(ROOT / value["raw_source_ref"]) == value["source_sha256"]
        for child in value.values():
            evidence_hashes(child)
    elif isinstance(value, list):
        for child in value:
            evidence_hashes(child)


def main():
    previous = baseline_layers()
    manifest = read(ROOT / f"data/manifest.{TAG}.json")
    frozen = read(ROOT / f"data/raw/repository/manifest-before-gulf.{TAG}.json")
    current = {l["layer"]: l for l in frozen["layers"]}
    assert set(current) == set(previous)
    assert {name for name in current if current[name] != previous[name]} == {"chindata/data-centers"}
    assert manifest["record_count"] == read(BASELINE)["record_count"] + 5 == 28024
    assert manifest["layer_count"] == 39
    for key in ["views", "network_evidence_layers", "infrastructure_evidence_layers", "vendor_registry",
                "observation_comparison_views", "application_endpoint_layers"]:
        assert frozen[key] == read(BASELINE)[key], key
    # The subsequent Gulf refresh must leave the China inputs and locality view intact.
    assert [l for l in manifest["layers"] if l["layer"].startswith("chindata/")] == [l for l in frozen["layers"] if l["layer"].startswith("chindata/")]
    assert manifest["geographic_footprint_views"][0] == frozen["geographic_footprint_views"][0]
    assert sha256(ROOT / "data/manifest.20261011.json") == "f408815674b2e195bc98a9b911b70154ec1b33847b3501147da102fcae964730"

    codes = read(ROOT / f"data/chindata/data-centers.{TAG}.geojson")["features"]
    old = {f["properties"]["record_id"]: f["properties"] for f in read(ROOT / previous["chindata/data-centers"]["files"]["geojson"]["path"])["features"]}
    assert len(codes) == 9 and all(f["geometry"] is None for f in codes)
    rows = [{**f["properties"], "latitude": None, "longitude": None} for f in codes]
    validate_records(rows)
    assert {r["name"] for r in rows} == {f"ChinaNorth H0{i}" for i in range(1, 7)} | {"ChinaNorth W01", "ChinaEast H01", "ChinaSouth W01"}
    for row in rows:
        assert row["city"] is None and row["lifecycle_status"] == "unknown"
        assert row["properties"]["code_to_campus_alias_not_established"]
        assert row["record_id"] not in old or row["first_seen"] == old[row["record_id"]]["first_seen"]
    report = read(ROOT / f"data/chindata/data-centers.{TAG}.report.json")
    assert {r["source_id"] for r in report["traversed_regional_pages"]} == {"chindata-" + k for k in REGIONAL_KEYS}
    assert sum(r["code_count"] for r in report["traversed_regional_pages"]) == 9
    assert len(report["named_bases_separate_from_code_inventory"]) == 2
    claims = read(ROOT / f"data/chindata/campus-alias-review.{TAG}.json")
    assert len(claims["claims"]) == 8
    assert all(r["match_status"] == "unresolved" and r["campus_claim_id"] is None for r in claims["code_matches"])
    assert claims["alias_relationships"][0]["match_status"] == "candidate"
    phases = [r for r in claims["claims"] if r["phase"]]
    assert {r["phase"] for r in phases} == {"9", "10"}
    assert all(r["claim_as_of"] == "2025-12-28" and r["evidence"][0]["source_published_at"] == "2026-04-01" for r in phases)

    path = ROOT / f"data/china/provider-localities.{TAG}.geojson"
    view = read(path)
    validator = load_validator(SCHEMA)
    validator.validate(view)
    invalid = copy.deepcopy(view)
    invalid["features"][0]["properties"]["physical_site_confirmed"] = True
    assert not validator.is_valid(invalid), "Facility assertion must not pass the locality-view schema"
    mapping = gazetteer()
    mapped, mapped_claims, unique = set(), set(), set()
    all_source_records = {f["properties"]["record_id"]: f["properties"]
        for name in CLOUD_LAYERS for f in read(ROOT / previous[name]["files"]["geojson"]["path"])["features"]}
    for feature in view["features"]:
        p = feature["properties"]
        key = (p["vendor_id"], p["service"], p["gazetteer"]["geonames_id"])
        assert key not in unique
        unique.add(key)
        selected, raw, source_id = mapping[(p["country_code"], p["locality"])]
        assert p["gazetteer"]["geonames_id"] == raw[0]
        assert p["location_precision"] == selected["location_precision"]
        assert feature["geometry"]["coordinates"] == [float(raw[5]), float(raw[4])]
        assert feature["geometry"]["coordinates"] != [0, 0]
        for rid in p["source_record_ids"]:
            assert rid not in mapped
            row = all_source_records[rid]
            assert row["entity_type"] != "availability_zone" and row["city"] in p["source_locality_labels"]
            assert row["country_code"] == p["country_code"]
            assert row["retrieved_at"] in {s["retrieved_at"] for s in p["evidence"]}
            mapped.add(rid)
        for cid in p["source_claim_ids"]:
            assert cid not in mapped_claims
            mapped_claims.add(cid)
    audit = read(ROOT / f"data/china/provider-localities.{TAG}.report.json")
    held = {r["record_id"] for r in audit["held_records"] if r["record_id"]}
    zones = set(audit["excluded_availability_zone_ids"])
    assert not (mapped & held or mapped & zones or held & zones)
    assert mapped | held | zones == set(all_source_records)
    assert (len(view["features"]), len(mapped), len(held), len(zones)) == (147, 183, 24, 265)
    assert mapped_claims == {r["claim_id"] for r in claims["claims"]}
    assert audit["vendor_counts"]["alibaba"] == 29 and audit["vendor_counts"]["chindata"] == 4
    assert {f["properties"]["locality"] for f in view["features"] if f["properties"]["vendor_id"] == "chindata"} == {"Huailai", "Lingqiu", "Qingyang", "Zhongwei"}
    assert {"Johor", "Saudi Arabia", "Virginia", "Silicon Valley", "Haidong"} <= {r["source_locality"] for r in audit["held_records"]}
    exported = list(csv.DictReader(io.StringIO(subprocess.check_output(["jq", "-r", "-f", "scripts/geographic-footprint-to-csv.jq", str(path)], cwd=ROOT, text=True))))
    assert len(exported) == len(view["features"])
    for row, feature in zip(exported, view["features"], strict=True):
        p = feature["properties"]
        assert row["footprint_id"] == p["footprint_id"]
        assert [float(row["longitude"]), float(row["latitude"])] == feature["geometry"]["coordinates"]
        for field in ["source_record_ids", "source_claim_ids", "source_locality_labels", "evidence", "gazetteer"]:
            assert json.loads(row[field]) == p[field]
    review = read(ROOT / f"data/china/geography-enrichment.{TAG}.json")
    assert len(review["vendors"]) == len({r["vendor_id"] for r in review["vendors"]}) == 31
    assert review["alibaba_reconciliation"]["directory_tables_equal_to_20261011"]
    assert review["alibaba_reconciliation"]["region_count"] == 38
    assert review["alibaba_reconciliation"]["availability_zone_count"] == 133

    gulf = read(ROOT / f"data/gulf/aws-oracle-coverage.{TAG}.json")
    assert (gulf["baseline_record_count"], gulf["baseline_geometry_null"]) == (19, 18)
    assert len(gulf["aws_current_regions"]) == 2 and len(gulf["aws_current_zone_ids"]) == 6
    assert all(r["city"] is None for r in gulf["aws_current_regions"])
    assert gulf["aws_saudi_plan"]["region_id"] is None and gulf["aws_saudi_plan"]["expected_launch"] == "2026-12"
    assert gulf["aws_saudi_plan"]["lifecycle_status"] == "planned"
    assert len(gulf["oracle_public_regions"]) == 4
    assert all(r["realm_key"] == "OC1" and r["availability_domain_count"] == 1 for r in gulf["oracle_public_regions"])
    assert len(gulf["oracle_dedicated_product_references"]) == 6
    assert all(not r["public_availability_asserted"] for r in gulf["oracle_dedicated_product_references"])
    assert (len(gulf["aws_interconnect_candidates"]), len(gulf["oracle_fastconnect_candidates"])) == (5, 6)
    assert gulf["aws_local_zones_reconciliation"]["current_gulf_rows"] == []
    assert gulf["aws_local_zones_reconciliation"]["missing_listing_is_not_retirement"]

    bibliography = read(ROOT / f"data/references/bibliography.{TAG}.json")
    references = bibliography["references"]
    assert bibliography["reference_count"] == len(references) == len({r["reference_id"] for r in references})
    indexed = {r["raw_source_ref"] for r in references if r["availability"] == "retained"}
    for r in references:
        if r["availability"] == "retained":
            assert sha256(ROOT / r["raw_source_ref"]) == r["sha256"]
    for item in read(CATALOG)["sources"]:
        if item["result"] == "retrieved":
            source(item["source_id"])
            assert item["path"] in indexed
    assert any("cdn-mapping-across-the-globe" in r["source_url"] for r in references)
    for value in [rows, claims, audit, view, review, gulf]:
        evidence_hashes(value)
    for entry in manifest["geographic_footprint_views"]:
        assert entry["excluded_from_canonical_totals"]
        if entry["layer"] == "china/provider-localities":
            assert entry["record_count"] == 147
        for file in entry["files"].values():
            assert sha256(ROOT / file["path"]) == file["sha256"]
    for item in manifest["assessments"]:
        assert sha256(ROOT / item["path"]) == item["sha256"]
    for file in manifest["bibliography"]["files"].values():
        assert sha256(ROOT / file["path"]) == file["sha256"]

    generated = [f"data/{name}.{TAG}.{suffix}" for name, suffix in (
        ("chindata/data-centers", "geojson"), ("chindata/data-centers", "report.json"),
        ("chindata/campus-alias-review", "json"), ("china/provider-localities", "geojson"),
        ("china/provider-localities", "report.json"), ("china/geography-enrichment", "json"),
        ("gulf/aws-oracle-coverage", "json"), ("references/bibliography", "json"))]
    generated.append(f"docs/bibliography.{TAG}.md")
    with tempfile.TemporaryDirectory(prefix="geography-enrichment-") as temp:
        for script in ["update_geography_enrichment.py", "assess_gulf_coverage.py", "build_bibliography.py"]:
            subprocess.run([sys.executable, "-B", "scripts/" + script, "--output-root", temp], cwd=ROOT, check=True)
        for name in generated:
            assert (ROOT / name).read_bytes() == (Path(temp) / name).read_bytes(), name
    print("Geography checks passed: 9 Chindata codes; 147 locality points; 24 held records; 31-vendor review; Gulf distinctions; bibliography; offline reproduction.")


if __name__ == "__main__":
    main()
