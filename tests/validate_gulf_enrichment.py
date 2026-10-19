#!/usr/bin/env python3
"""Guard Gulf identity, geography, historical scope, prefix joins and review behavior."""
from __future__ import annotations

from collections import Counter
from datetime import date
import csv
import io
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_gulf_sources import KEYS, check_one, compare_rows, semantic_rows
from gulf_enrichment_common import BASELINE, CATALOG, DATE, GULF, LAYERS, TAG, baseline, read, source
from location_common import load_validator, sha256, validate_records
from network_common import validate_network_collection
from update_gulf_enrichment import geofeed_rows, join_geofeed
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


def project(path, script, schema=None):
    args = ["jq", "-r"]
    if schema:
        args += ["--slurpfile", "schema", str(ROOT / "schema" / schema)]
    args += ["-f", str(ROOT / "scripts" / script), str(path)]
    return list(csv.DictReader(io.StringIO(subprocess.check_output(args, text=True))))


def main():
    old, manifest = baseline(), read(ROOT / f"data/manifest.{TAG}.json")
    previous = {l["layer"]: l for l in old["layers"]}
    current = {l["layer"]: l for l in manifest["layers"]}
    assert set(current) == set(previous)
    assert {k for k in previous if previous[k] != current[k]} == set(LAYERS)
    assert manifest["record_count"] == old["record_count"] == 28024
    assert manifest["layer_count"] == 39
    for key in ["views", "vendor_registry", "application_endpoint_layers", "observation_comparison_views"]:
        assert manifest[key] == old[key]
    assert manifest["network_evidence_layers"][:-1] == old["network_evidence_layers"]
    assert manifest["infrastructure_evidence_layers"][:-1] == old["infrastructure_evidence_layers"]
    assert (manifest["network_evidence_record_count"], manifest["infrastructure_evidence_record_count"]) == (3950, 324)
    assert manifest["geographic_footprint_views"][:1] == old["geographic_footprint_views"]
    assert manifest["geographic_footprint_view_count"] == 2

    gulf, all_ids = {}, set()
    for name in LAYERS:
        before = {f["properties"]["record_id"]: f for f in read(ROOT / previous[name]["files"]["geojson"]["path"])["features"]}
        after = {f["properties"]["record_id"]: f for f in read(ROOT / current[name]["files"]["geojson"]["path"])["features"]}
        assert set(before) == set(after)
        all_ids.update(after)
        rows = []
        for rid, feature in after.items():
            p = feature["properties"]
            coords = (feature["geometry"] or {}).get("coordinates", [None, None])
            rows.append({**p, "latitude": coords[1], "longitude": coords[0]})
            assert p["first_seen"] == before[rid]["properties"]["first_seen"]
            if p["country_code"] not in GULF:
                assert feature == before[rid], rid
                continue
            gulf[rid] = feature
            if name == "aws/local-zones":
                assert p["lifecycle_status"] == "unknown"
                for key in ["raw_source_ref", "source_sha256", "retrieved_at", "last_seen"]:
                    assert p[key] == before[rid]["properties"][key]
                assert feature["geometry"] == before[rid]["geometry"]
            else:
                assert p["last_seen"] == p["retrieved_at"] == DATE
                assert feature["geometry"] is None
            if name == "aws/regions-and-zones":
                assert p["city"] is None and p["properties"]["geography_scope"] == "country_only"
            if name == "aws/cloudfront":
                assert p["properties"]["asset_count"] is None
                assert p["properties"]["historical_asset_count"]["value"] == before[rid]["properties"]["properties"]["asset_count"]
        validate_records(rows)
        projected = project(ROOT / current[name]["files"]["geojson"]["path"], "geojson-to-csv.jq", "location.schema.json")
        assert [r["record_id"] for r in projected] == [r["record_id"] for r in rows]
        assert [json.loads(r["properties"]) for r in projected] == [r["properties"] for r in rows]
    assert len(gulf) == 19
    assert gulf["aws:edge_pop:cloudfront-bh-bahrain"]["properties"]["city"] is None

    view_path = ROOT / f"data/gulf/provider-localities.{TAG}.geojson"
    view = read(view_path)
    load_validator(ROOT / "schema/geographic-footprint.schema.json").validate(view)
    assert len(view["features"]) == 9
    assert Counter(f["properties"]["vendor_id"] for f in view["features"]) == {"aws": 5, "oracle": 4}
    mapped = [rid for f in view["features"] for rid in f["properties"]["source_record_ids"]]
    report = read(view_path.with_suffix(".report.json"))
    held = [r["record_id"] for r in report["held_records"]]
    assert len(mapped) == len(set(mapped)) == 9 and len(held) == 10
    assert set(mapped).isdisjoint(held) and set(mapped) | set(held) == set(gulf)
    for f in view["features"]:
        p = f["properties"]
        original = gulf[p["source_record_ids"][0]]["properties"]
        assert p["locality"] == original["city"] and p["country_code"] == original["country_code"]
        assert not p["physical_site_confirmed"] and p["excluded_from_canonical_totals"]
    exported = project(view_path, "geographic-footprint-to-csv.jq")
    assert len(exported) == 9
    for f, row in zip(view["features"], exported, strict=True):
        assert f["geometry"]["coordinates"] == [float(row["longitude"]), float(row["latitude"])]
        assert f["properties"]["source_record_ids"] == json.loads(row["source_record_ids"])

    infra_path = ROOT / f"data/infrastructure/gulf-cloud-connectivity.{TAG}.json"
    infra = read(infra_path)
    validate_collection(infra, external_record_ids=all_ids)
    assert Counter(r["category"] for r in infra["records"]) == {
        "interconnect_endpoint_reference": 10, "cloud_interconnect_membership": 11, "dedicated_product_region_reference": 6}
    assert all(r["geometry"] is None and r["lifecycle_status"] == "unknown" for r in infra["records"])
    endpoints = {r["record_id"]: r for r in infra["records"] if r["category"] == "interconnect_endpoint_reference"}
    assert len(endpoints["gulf:interconnect_endpoint:equinix-dx1"]["properties"]["directory_labels"]) == 2
    assert endpoints["gulf:interconnect_endpoint:equinix-mc1"]["properties"]["locality"] == "Barka"
    assert endpoints["gulf:interconnect_endpoint:equinix-mc1"]["properties"]["metro"] == "Muscat"
    assert all(r["properties"]["facility_address"] is None for r in endpoints.values())
    dedicated = [r for r in infra["records"] if r["category"] == "dedicated_product_region_reference"]
    assert {r["properties"]["realm_key"] for r in dedicated} == {"OC9", "OC21", "OC29", "OC36"}
    assert all(not r["properties"]["public_availability_asserted"] and r["properties"]["product_scope"] == "Oracle EPM Cloud" for r in dedicated)
    exported = project(infra_path, "infrastructure-json-to-csv.jq", "infrastructure-evidence.schema.json")
    assert [json.loads(r["relationships"]) for r in exported] == [r["relationships"] for r in infra["records"]]

    net_path = ROOT / f"data/network/gulf-provider-prefixes.{TAG}.json"
    net = read(net_path)
    validate_network_collection(net)
    assert len(net["records"]) == 563
    assert Counter((r["provider"], r["ip_family"]) for r in net["records"]) == {
        ("Amazon Web Services", 4): 259, ("Amazon Web Services", 6): 229,
        ("Oracle Cloud Infrastructure", 4): 59, ("Oracle Cloud Infrastructure", 6): 16}
    for row in net["records"]:
        assert row["properties"]["region_record_id"] in gulf
        assert row["properties"]["physical_location_not_asserted"]
        assert row["asn"] is None and row["valid_from"] is None and row["valid_to"] is None
        assert row["observed_at"].endswith("+00:00")
        if row["provider"] == "Oracle Cloud Infrastructure":
            assert row["source_published_at"] is None and row["properties"]["source_updated_at"] == "2026-08-25"
    net_report = read(net_path.with_suffix(".report.json"))
    assert net_report["aws_distinct_prefix_geofeed_coverage"] == {"full": 282, "none": 11}
    assert len(net_report["muscat_border_group_evidence"]["record_ids"]) == 4
    held_feed = net_report["gulf_geofeed_rows_without_overlap_in_selected_aws_regions"]
    assert Counter(r["country_code"] for r in held_feed) == {"SA": 60, "AE": 16, "BH": 14, "OM": 3}
    feed_lines = {r["source_line"] for _, r in geofeed_rows() if r["country_code"] in GULF}
    joined_lines = {r["source_line"] for n in net["records"] for r in n["properties"].get("geofeed", {}).get("matches", []) if r["country_code"] in GULF}
    assert joined_lines.isdisjoint(r["source_line"] for r in held_feed)
    assert joined_lines | {r["source_line"] for r in held_feed} == feed_lines
    exported = project(net_path, "network-json-to-csv.jq", "network-evidence.schema.json")
    assert [json.loads(r["properties"]) for r in exported] == [r["properties"] for r in net["records"]]

    # A subnet cannot locate the whole prefix; duplicate overlaps cannot inflate coverage.
    def feed(prefix, city="Dubai"):
        return ipaddress.ip_network(prefix), {"prefix": prefix, "country_code": "AE", "subdivision": "AE-DU", "city_label": city}
    partial = join_geofeed("192.0.2.0/24", [feed("192.0.2.0/25"), feed("192.0.2.0/26")])
    assert partial["coverage"] == "partial" and partial["matched_address_count"] == "128"
    covering = join_geofeed("192.0.2.0/25", [feed("192.0.2.0/24"), feed("2001:db8::/32")])
    assert covering["coverage"] == "full" and covering["matches"][0]["overlap_relation"] == "covering"
    assert join_geofeed("2001:db8::/48", [feed("2001:db8::/48")])["matches"][0]["overlap_relation"] == "exact"

    review = read(ROOT / f"data/gulf/enrichment-implementation.{TAG}.json")
    assert review["saudi_launch_watch"]["lifecycle_status"] == "planned"
    assert review["saudi_launch_watch"]["region_id"] is None
    assert (review["current_directory_reconfirmed_count"], review["historical_unconfirmed_count"]) == (18, 1)
    for payload in [list(gulf.values()), view, infra, net, net_report, review]:
        hashes(payload)
    bibliography = read(ROOT / f"data/references/bibliography.{TAG}.json")
    indexed = {r["raw_source_ref"] for r in bibliography["references"]}
    for item in read(CATALOG)["sources"]:
        assert item["path"] in indexed
        source(item["source_id"])
    for key in ["layers", "geographic_footprint_views", "network_evidence_layers", "infrastructure_evidence_layers"]:
        for entry in manifest[key]:
            for item in entry["files"].values():
                assert sha256(ROOT / item["path"]) == item["sha256"]

    # Detect missing/new region IDs and fail on parser breakage, not page tracking changes.
    body = (ROOT / source("aws-regions")["path"]).read_bytes()
    before = semantic_rows("aws-regions", body)
    changed = body.replace(b"me-central-1", b"me-central-9")
    diff = compare_rows(before, semantic_rows("aws-regions", changed))
    assert diff["semantic_changed"] and len(diff["removed_rows"]) == len(diff["added_rows"]) == 1
    cf_body = (ROOT / source("aws-cloudfront")["path"]).read_bytes()
    assert semantic_rows("aws-cloudfront", cf_body) == semantic_rows("aws-cloudfront", cf_body + b'<script>tracking="different"</script>')
    try:
        semantic_rows("oracle-regions", b"<html>Unexpected service response</html>")
    except ValueError:
        pass
    else:
        raise AssertionError("Parser drift silently accepted")

    with tempfile.TemporaryDirectory(prefix="gulf-reproduction-") as temp:
        output = Path(temp)
        subprocess.run([sys.executable, "-B", "scripts/update_gulf_enrichment.py", "--output-root", temp], cwd=ROOT, check=True)
        for generated in output.rglob("*"):
            if generated.is_file():
                assert generated.read_bytes() == (ROOT / generated.relative_to(output)).read_bytes(), generated
        subprocess.run([sys.executable, "-B", "scripts/build_manifest.py", "--retrieved-at", DATE, "--output", str(output / "manifest.json")], cwd=ROOT, check=True)
        assert (output / "manifest.json").read_bytes() == (ROOT / f"data/manifest.{TAG}.json").read_bytes()
        subprocess.run([sys.executable, "-B", "scripts/check_gulf_sources.py", "--offline", "--as-of", DATE,
                        "--output-dir", str(output / "monitor")], cwd=ROOT, check=True)
        monitor = read(output / "monitor/report.json")
        assert len(monitor["sources"]) == len(KEYS) == 12 and not monitor["error_count"]
        with patch("check_gulf_sources.urlopen", side_effect=OSError("test network unavailable")):
            failed = check_one("oracle-regions", output / "failure", False, date.fromisoformat(DATE))
            assert failed["status"] == "capture_or_parser_error"
    print("Gulf checks passed: 19 preserved IDs, 9 locality points, 27 scoped infrastructure assertions, 563 prefix declarations, guarded monitoring and offline reproduction.")


if __name__ == "__main__":
    main()
