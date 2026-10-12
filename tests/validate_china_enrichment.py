#!/usr/bin/env python3
"""Check public-source completeness, scope, provenance, joins and offline reproduction."""

import copy
import csv
import io
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from china_enrichment_common import source_bytes, soup, cells, walk
from location_common import sha256, validate_records
from network_common import validate_network_collection
from update_infrastructure import validate_collection

TAG = "20261011"


def read(path):
    return json.loads((ROOT / path).read_text())


def locations(name):
    return [{**f["properties"], "latitude": None, "longitude": None}
            for f in read(f"data/{name}.{TAG}.geojson")["features"]]


def parity(path, schema, program):
    rows = read(path)["records"]
    document = read(schema)
    contract = document.get("$defs", {}).get("record", document["properties"]["records"]["items"])
    output = subprocess.check_output(["jq", "-r", "--slurpfile", "schema", schema, "-f", program, path], cwd=ROOT, text=True)
    parsed = csv.DictReader(io.StringIO(output))
    assert parsed.fieldnames == contract["required"]
    # Compare every field to the schema projection, including nested values.
    projected = list(parsed)
    assert len(projected) == len(rows)
    for actual, expected in zip(projected, rows, strict=True):
        for field, value in expected.items():
            if isinstance(value, (dict, list)):
                assert json.loads(actual[field]) == value
            else:
                assert actual[field] == ("" if value is None else str(value))


def main():
    manifest = read(f"data/manifest.{TAG}.json")
    assert (manifest["record_count"], manifest["layer_count"], manifest["view_count"]) == (27500, 31, 8)
    assert (manifest["network_evidence_record_count"], manifest["infrastructure_evidence_record_count"], manifest["vendor_registry_record_count"]) == (3167, 297, 47)
    current_ids = set()
    cloud_paths = []
    for layer in manifest["layers"]:
        document = read(layer["files"]["geojson"]["path"])
        ids = {f["properties"]["record_id"] for f in document["features"]}
        assert not ids & current_ids
        current_ids |= ids
        if layer["snapshot_tag"] == TAG and layer["layer"].split("/")[0] in {
            "alibaba", "tencent", "huawei", "volcano", "microsoft", "qiniu", "aws", "baidu", "jd", "kingsoft", "tianyi", "chindata"}:
            assert all(f["geometry"] is None for f in document["features"])
            rows = locations(layer["layer"])
            validate_records(rows)
            for row in rows:
                assert row["parent_record_id"] is None or row["parent_record_id"] in ids
            cloud_paths.append(layer["files"]["geojson"]["path"])
    for view in manifest["views"]:
        ids = {f["properties"]["record_id"] for f in read(view["files"]["geojson"]["path"])["features"]}
        assert ids <= current_ids
    ali, tencent = locations("alibaba/regions-and-zones"), locations("tencent/regions-and-zones")
    assert len(ali) == 171 and len(tencent) == 97
    for vendor, rows in [("alibaba", ali), ("tencent", tencent)]:
        old = {f["properties"]["record_id"]: f["properties"] for f in read(f"data/{vendor}/regions-and-zones.20260804.geojson")["features"]}
        for row in rows:
            if row["record_id"] in old:
                assert row["first_seen"] == old[row["record_id"]]["first_seen"]
        key = "alibaba-directory" if vendor == "alibaba" else "tencent-directory"
        # Independent explicit-token extraction must equal all currently listed IDs.
        tokens = set()
        for table in soup(key).find_all("table"):
            for tr in table.find_all("tr"):
                for cell in cells(tr):
                    if re.fullmatch(r"(?:cn|ap|eu|us|me|na|sa)-[a-z0-9-]+", cell):
                        tokens.add(cell)
        observed = {r["source_record_id"] for r in rows if r["last_seen"] == "2026-10-11"}
        assert tokens == observed
    missing = next(r for r in tencent if r["source_record_id"] == "ap-shanghai-fsi-1")
    assert missing["last_seen"] == missing["retrieved_at"] == "2026-08-04"
    assert missing["lifecycle_status"] == missing["access_status"] == "unknown"
    report = read(f"data/tencent/regions-and-zones.{TAG}.report.json")
    corroboration = report["chinese_directory_corroboration"]
    assert corroboration["explicit_id_count"] == 96
    assert corroboration["ids_only_in_chinese_directory"] == corroboration["ids_only_in_english_directory"] == []
    assert sum(r["parent_record_id"] == "alibaba:cloud_region:ap-southeast-8" for r in ali) == 2
    for row in ali:
        if row["properties"].get("closure_completed_not_asserted"):
            assert row["lifecycle_status"] == "unknown"
    volcano = locations("volcano/regions-and-zones")
    assert Counter(r["entity_type"] for r in volcano) == {"cloud_region": 6, "availability_zone": 18}
    discrepancies = read(f"data/volcano/regions-and-zones.{TAG}.report.json")["source_count_discrepancies"]
    assert {d["region_id"] for d in discrepancies} == {"cn-shanghai", "ap-southeast-3"}
    huawei = locations("huawei/regions")
    assert len(huawei) == 31 and all(r["properties"]["universal_product_availability_not_asserted"] for r in huawei)
    assert len(locations("microsoft/china-cloud-regions")) == 6
    assert not any(r["entity_type"] == "availability_zone" for r in locations("microsoft/china-cloud-regions"))
    qiniu = locations("qiniu/resource-pools-and-regions")
    table_tokens = set(re.findall(r"\b(?:cn|ap|me|us|eu|grand)-[a-z0-9-]+\b", soup("qiniu-resource-pools").get_text(" ")))
    assert {r["source_record_id"] for r in qiniu if r["entity_type"] == "cloud_region"} == table_tokens
    assert len(qiniu) == 23
    assert next(r for r in qiniu if r["source_record_id"] == "cn-wulanchabu")["city"] == "Ulanqab"
    assert next(r for r in qiniu if r["source_record_id"] == "ap-northeast-1")["country_code"] is None
    registry = read(f"data/vendors/registry.{TAG}.json")
    infra = [read(f"data/infrastructure/{name}.{TAG}.json") for name in (
        "china-ai-services", "china-facilities-and-portfolios", "china-carrier-links")]
    external = current_ids | {r["record_id"] for c in [registry] + infra for r in c["records"]}
    for collection in [registry] + infra:
        validate_collection(collection, external_record_ids=external)
        assert all(r["geometry"] is None for r in collection["records"])
        for item in walk(collection):
            if isinstance(item, dict) and item.get("raw_source_ref") and item.get("source_sha256"):
                assert sha256(ROOT / item["raw_source_ref"]) == item["source_sha256"]
    bad = copy.deepcopy(infra[0])
    bad["records"][0]["relationships"] = [{"relationship_type": "offered_by", "target_record_id": "missing:vendor:identity"}]
    try:
        validate_collection(bad, external_record_ids=external)
    except ValueError:
        pass
    else:
        raise AssertionError("Unresolved external join accepted")
    identities = {r["record_id"]: r for r in registry["records"]}
    assert identities["vendor:identity:fal"]["properties"]["cohort_classification"] == "global_inference_platform"
    assert identities["vendor:identity:fal"]["country_codes"] == ["US"]
    assert identities["vendor:identity:seedance2ai"]["properties"]["cohort_classification"] == "jurisdiction_unresolved"
    ai = infra[0]["records"]
    assert len(ai) == 135
    assert sum(r["category"] == "ai_api_endpoint" for r in ai) == 48
    recognitions = [r for r in infra[1]["records"] if r["category"] == "recognized_compute_facility"]
    assert len(recognitions) == 60 and {r["properties"]["source_row"] for r in recognitions} == set(range(1, 61))
    assert all(r["lifecycle_status"] == "unknown" for r in recognitions)
    assert any("泽悦" in r["name"] and "A—1" in r["name"] for r in recognitions)
    # Validate supplier quantities against the retained filing text, not only serialized constants.
    filing = ROOT / next(s["path"] for s in read(f"data/raw/china-enrichment/catalog.{TAG}.json")["sources"] if s["source_id"] == "bilibili-2025-report")
    filing_text = subprocess.check_output(["pdftotext", "-layout", str(filing), "-"], text=True, stderr=subprocess.DEVNULL)
    assert re.search(r"telecommunications service\s+providers\s+116\s+115\s+116", filing_text)
    assert "57%" in filing_text and "10%" in filing_text
    stations = [r for r in infra[2]["records"] if r["category"] == "cable_landing_station"]
    assert len(stations) == 3 and sum("Chung Hom Kok" in r["properties"].get("locality", "") for r in stations) == 2
    network_path = f"data/network/china-vendor-evidence.{TAG}.json"
    network = read(network_path)
    validate_network_collection(network)
    assert len(network["records"]) == 42
    checks = [r for r in network["records"] if r["evidence_type"] == "reachability_observation"]
    assert len(checks) == 23 and all(r["status"] == "tls_verified" for r in checks)
    for row in checks:
        assert ipaddress.ip_address(row["properties"]["connected_ip"]).is_global
        assert row["properties"]["endpoint_record_ids"][0] in external
        assert "RTT" in row["properties"]["timing_scope"]
        assert row["properties"]["observed_at"].startswith("2026-10-12")
    for row in network["records"]:
        assert sha256(ROOT / row["raw_source_ref"]) == row["source_sha256"]
    catalog = read(f"data/raw/china-enrichment/catalog.{TAG}.json")
    assert len(catalog["sources"]) == 64
    for entry in catalog["sources"]:
        assert entry["result"] == "retrieved"
        assert sha256(ROOT / entry["path"]) == entry["sha256"]
        provenance = read(entry["path"] + ".provenance.json")
        assert provenance["sha256"] == entry["sha256"]
        assert source_bytes(entry["source_id"])
    for entry in manifest["assessments"]:
        assert sha256(ROOT / entry["path"]) == entry["sha256"]
    implementation = read(f"data/china/enrichment-implementation.{TAG}.json")
    for output in implementation["outputs"]:
        assert sha256(ROOT / output["path"]) == output["sha256"]
    parity(network_path, "schema/network-evidence.schema.json", "scripts/network-json-to-csv.jq")
    for path in [f"data/vendors/registry.{TAG}.json"] + [f"data/infrastructure/{n}.{TAG}.json" for n in ("china-ai-services", "china-facilities-and-portfolios", "china-carrier-links")]:
        parity(path, "schema/infrastructure-evidence.schema.json", "scripts/infrastructure-json-to-csv.jq")
    with tempfile.TemporaryDirectory(prefix="china-enrichment-") as temporary:
        output_root = Path(temporary)
        # Copy only historical layers needed to reproduce first_seen. Current
        # output files are generated from source rather than copied into place.
        for path in cloud_paths:
            parent = ROOT / Path(path).parent
            for historical in parent.glob("*.202608*.geojson"):
                target = output_root / historical.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(historical, target)
        for script in ("update_china_enrichment", "update_china_ai", "update_china_facilities", "update_china_carriers", "update_china_network", "report_china_enrichment"):
            subprocess.run([sys.executable, "-B", f"scripts/{script}.py", "--output-root", temporary], cwd=ROOT, check=True, capture_output=True)
        paths = [o["path"] for o in implementation["outputs"]]
        paths += [f"data/china/legacy-reconciliation.{TAG}.json", f"data/china/enrichment-implementation.{TAG}.json"]
        paths += [v["files"]["geojson"]["path"] for v in manifest["views"] if not v["layer"].startswith("russia/")]
        for path in paths:
            assert (output_root / path).read_bytes() == (ROOT / path).read_bytes(), path
    print("China enrichment validated: source IDs, scope, 60 final recognitions, bounded observations, external joins, CSV parity and offline reproduction")


if __name__ == "__main__":
    main()
