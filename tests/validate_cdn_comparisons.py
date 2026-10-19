#!/usr/bin/env python3
"""Check ASN joins, registry boundaries, view identity, CSVs and regeneration."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
import copy
import csv
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from location_common import load_validator, sha256
from update_cdn_comparisons import (
    APNIC_PATH, ASN_PATH, CITY_PATH, DATASETS, SCHEMA_PATH, TAG,
    comparison_rows, lookup_registration, parse_apnic,
)


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def must_reject(function, *args) -> None:
    try:
        function(*args)
    except ValueError:
        return
    raise AssertionError("invalid input was accepted")


def validate_registry() -> None:
    # The second ASN in an allocated range must match; the next ASN must not.
    fixture = ("2.3|apnic|20260606|3||20260605|+1000\n"
               "apnic|*|asn|*|3|summary\n"
               "apnic|IN|asn|100|2|20200101|allocated|example\n"
               "apnic|US|asn|200|1|*|assigned|example\n"
               "apnic|IN|asn|300|2|*|reserved|example\n")
    ranges, _ = parse_apnic(fixture)
    starts = [row["start_asn"] for row in ranges]
    assert lookup_registration(99, ranges, starts) is None
    assert lookup_registration(101, ranges, starts)["country_code"] == "IN"
    assert lookup_registration(102, ranges, starts) is None
    assert lookup_registration(200, ranges, starts)["country_code"] == "US"
    assert lookup_registration(200, ranges, starts)["delegated_at"] is None
    assert lookup_registration(300, ranges, starts) is None
    must_reject(parse_apnic, fixture.replace("|3||", "|4||"))
    must_reject(parse_apnic, fixture.replace("|200|1|", "|101|1|"))
    must_reject(parse_apnic, fixture.replace("20260606", "20261019"))


def validate_comparisons() -> None:
    source = read(ASN_PATH)["features"]
    source_ids = {f["properties"]["record_id"]: f["properties"] for f in source}
    matrix = read(f"data/observations/cdn-asn-comparison.{TAG}.json")
    india = read(f"data/india/cdn-asn-comparison.{TAG}.json")
    validator = load_validator(SCHEMA_PATH)
    validator.validate(matrix)
    validator.validate(india)
    rows = matrix["records"]
    asns = [r["asn"] for r in rows]
    assert asns == sorted(set(asns)) and len(rows) == 6564
    assert len(india["records"]) == 279
    assert india["records"] == [r for r in rows if r["apnic_registration"] is not None
                                 and r["apnic_registration"]["country_code"] == "IN"]
    links = [record_id for row in rows for record_id in row["provider_record_ids"].values() if record_id]
    assert len(links) == len(set(links)) == 13631
    assert set(links) == set(source_ids)
    for row in rows:
        names = set()
        for key, record_id in row["provider_record_ids"].items():
            if record_id is None:
                continue
            original = source_ids[record_id]
            assert original["properties"]["asn"] == row["asn"]
            assert original["provider"] == DATASETS[key]["provider"]
            names.add(original["properties"]["as_name"])
        assert row["as_names"] == sorted(names)
    assert sum(row["provider_record_ids"]["apple"] is not None for row in rows) == 973
    published_matrix = ROOT / "data/raw/observations/asn-wise-cdn-mapping.202606.csv"
    with published_matrix.open(newline="") as handle:
        published_asns = {int(r["ASN"]) for r in csv.DictReader(handle)}
    added = set(asns) - published_asns
    assert len(added) == 98
    assert all(r["provider_record_ids"]["apple"] is not None for r in rows if r["asn"] in added)
    expected_india = {"ggc": 249, "oca": 115, "fna": 198, "akamai": 65,
                      "microsoft": 20, "apple": 10, "aws-cloudfront": 1}
    assert {key: sum(r["provider_record_ids"][key] is not None for r in india["records"])
            for key in DATASETS} == expected_india
    assert {r["asn"] for r in india["records"] if r["provider_record_ids"]["apple"]} == {
        9498, 9829, 17813, 24309, 38266, 55410, 55836, 133619, 152586, 153914,
    }
    apnic = gzip.decompress((ROOT / APNIC_PATH).read_bytes()).decode("utf-8")
    apnic_lines = apnic.splitlines()
    for row in rows:
        registration = row["apnic_registration"]
        if registration is None:
            continue
        fields = apnic_lines[registration["source_line"] - 1].split("|")
        assert fields[0] == "apnic" and fields[2] == "asn"
        assert int(fields[3]) <= row["asn"] < int(fields[3]) + int(fields[4])
        assert fields[1] == (registration["country_code"] or fields[1])
        assert fields[6] == registration["status"]
    ranges, _ = parse_apnic(apnic)
    starts = [r["start_asn"] for r in ranges]
    # Independently ensure unmatched ASNs have no containing delegated range.
    for row in rows:
        if row["apnic_registration"] is None:
            position = bisect_right(starts, row["asn"]) - 1
            assert position < 0 or row["asn"] >= starts[position] + ranges[position]["asn_count"]
    duplicate = copy.deepcopy(source[0])
    duplicate["properties"]["record_id"] += "-duplicate"
    must_reject(comparison_rows, [source[0], duplicate], ranges)
    invalid = copy.deepcopy(source[0])
    invalid["properties"]["properties"]["asn"] = 0
    must_reject(comparison_rows, [invalid], ranges)
    located = copy.deepcopy(source[0])
    located["properties"]["country_code"] = "IN"
    must_reject(comparison_rows, [located], ranges)
    for collection in (matrix, india):
        assert collection["provider_columns"] == [
            {"key": key, "provider": config["provider"], "dataset": config["label"]}
            for key, config in DATASETS.items()]
        for source_ref in collection["sources"]:
            assert sha256(ROOT / source_ref["path"]) == source_ref["sha256"]
        completed = subprocess.run(["jq", "-r", "-f", "scripts/cdn-comparison-to-csv.jq"],
                                   input=json.dumps(collection), cwd=ROOT, check=True, capture_output=True, text=True)
        projected = list(csv.DictReader(io.StringIO(completed.stdout)))
        assert len(projected) == len(collection["records"])
        for original, projected_row in zip(collection["records"], projected):
            assert int(projected_row["asn"]) == original["asn"]
            assert json.loads(projected_row["as_names"]) == original["as_names"]
            assert json.loads(projected_row["source_record_ids"]) == original["provider_record_ids"]
            for key, config in DATASETS.items():
                assert projected_row[config["label"]] == ("observed" if original["provider_record_ids"][key]
                                                          else "not_observed_in_this_snapshot")


def validate_views_and_manifest() -> None:
    apple = read(f"data/observations/apple-asn.{TAG}.geojson")["features"]
    india = read(f"data/india/cdn-cities.{TAG}.geojson")["features"]
    asn_source = read(ASN_PATH)["features"]
    city_source = read(CITY_PATH)["features"]
    assert apple == [f for f in asn_source if f["properties"]["provider"] == "Apple"]
    assert india == [f for f in city_source if f["properties"]["country_code"] == "IN"]
    assert len(apple) == 973 and all(f["geometry"] is None for f in apple)
    assert all(f["properties"]["country_code"] is None for f in apple)
    assert len(india) == 515
    assert Counter(f["properties"]["provider"] for f in india) == {"Google": 211, "Meta": 146, "Netflix": 158}
    assert len({f["properties"]["properties"]["asn"] for f in india}) == 203
    previous, current = read("data/manifest.20261011.json"), read(f"data/manifest.{TAG}.json")
    # Other enrichment can add canonical layers in the same manifest. These
    # comparison views must preserve prior layers and never enter their totals.
    current_layers = {layer["layer"]: layer for layer in current["layers"]}
    frozen = read("data/raw/repository/manifest-before-geography.20261019.json")
    frozen_layers = {layer["layer"]: layer for layer in frozen["layers"]}
    assert all(frozen_layers[layer["layer"]] == layer for layer in previous["layers"])
    # The geography suite separately verifies the sole intentional refresh,
    # Chindata, against this retained manifest and all historical file hashes.
    assert all(current_layers[name] == layer for name, layer in frozen_layers.items()
               if name != "chindata/data-centers")
    assert current["record_count"] == sum(layer["record_count"] for layer in current["layers"])
    assert {"observations/apple-asn", "india/cdn-cities", "observations/cdn-asn-comparison",
            "india/cdn-asn-comparison"}.isdisjoint(current_layers)
    for key in ("infrastructure_evidence_layers", "vendor_registry", "infrastructure_evidence_record_count"):
        assert previous[key] == current[key], key
    current_network = {layer["layer"]: layer for layer in current["network_evidence_layers"]}
    assert all(current_network[layer["layer"]] == layer for layer in previous["network_evidence_layers"])
    assert current["network_evidence_record_count"] == sum(layer["record_count"] for layer in current_network.values())
    assert current["view_count"] == previous["view_count"] + 2 == 10
    assert current["observation_comparison_view_count"] == len(current["observation_comparison_views"])
    assert {"observations/cdn-asn-comparison", "india/cdn-asn-comparison"} <= {
        layer["layer"] for layer in current["observation_comparison_views"]}
    for entry in current["views"] + current["observation_comparison_views"]:
        for file in entry["files"].values():
            assert sha256(ROOT / file["path"]) == file["sha256"]
    assert sha256(SCHEMA_PATH) == current["observation_comparison_schema"]["sha256"]


def validate_regeneration() -> None:
    names = [f"data/{stem}.{TAG}.{suffix}" for stem, suffixes in (
        ("observations/cdn-asn-comparison", ("json", "report.json")),
        ("india/cdn-asn-comparison", ("json", "report.json")),
        ("observations/apple-asn", ("geojson", "report.json")),
        ("india/cdn-cities", ("geojson", "report.json")),
    ) for suffix in suffixes]
    with tempfile.TemporaryDirectory(prefix="cdn-comparison-") as temp:
        subprocess.run([sys.executable, "-B", "scripts/update_cdn_comparisons.py", "--output-root", temp],
                       cwd=ROOT, check=True, capture_output=True)
        for name in names:
            assert (ROOT / name).read_bytes() == (Path(temp) / name).read_bytes(), name
        assert not list(Path(temp).rglob("*.csv"))
        for date in ("2026-10-11", "2026-10-19"):
            output = Path(temp) / "manifest.json"
            subprocess.run([sys.executable, "-B", "scripts/build_manifest.py", "--retrieved-at", date,
                            "--output", str(output)], cwd=ROOT, check=True, capture_output=True)
            assert output.read_bytes() == (ROOT / f"data/manifest.{date.replace('-', '')}.json").read_bytes()


def main() -> None:
    validate_registry()
    validate_comparisons()
    validate_views_and_manifest()
    validate_regeneration()
    print("Validated 6,564 ASN comparisons, 279 APNIC India ASNs, 973 Apple observations and 515 India city observations; comparison views excluded from canonical totals.")


if __name__ == "__main__":
    main()
