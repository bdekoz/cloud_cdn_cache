#!/usr/bin/env python3
"""Check source conservation, hierarchy, DNS/registration semantics and regeneration."""
from __future__ import annotations

import bz2
from collections import Counter
import copy
import csv
import io
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from location_common import load_validator, sha256, validate_records
from network_common import validate_network_collection
from russia_enrichment_common import (BASELINE, DATE, TAG, EXTRA, LOCATION_LAYERS, LOCATION_SCHEMA,
                                      NETWORK_LAYERS, raw_path, read, source)
from review_russia_enrichment import SOURCES
from update_cdn_comparisons import ASN_PATH, comparison_rows, lookup_registration
from update_crypto_endpoints import PATH, SCHEMA, query_result, validate
from update_russia_comparison import parse_ripe
from update_russia_providers import Tables


def must_reject(call, *args):
    try:
        call(*args)
    except ValueError:
        return
    raise AssertionError("Invalid input accepted")


def projected(path, script, schema=None):
    cmd = ["jq", "-r"]
    if schema:
        cmd += ["--slurpfile", "schema", str(schema)]
    output = subprocess.check_output(cmd + ["-f", f"scripts/{script}", str(path)], cwd=ROOT, text=True)
    return list(csv.DictReader(io.StringIO(output)))


def locations():
    layers, all_rows = {}, {}
    for layer in LOCATION_LAYERS:
        path = ROOT / f"data/{layer}.{TAG}.geojson"
        features = read(path)["features"]
        rows = [dict(f["properties"], latitude=None, longitude=None) for f in features]
        assert all(f["geometry"] is None for f in features)
        validate_records(rows, LOCATION_SCHEMA)
        assert len({r["record_id"] for r in rows}) == len(rows)
        assert all(r["record_id"] not in all_rows for r in rows)
        all_rows.update((r["record_id"], r) for r in rows)
        layers[layer] = rows
        for row in rows:
            assert row["source_sha256"] == sha256(ROOT / row["raw_source_ref"])
            assert row["coordinate_method"] == "unknown" and row["coordinate_crs"] is None
            assert not row["properties"]["facility_mapping_asserted"]
        csv_rows = projected(path, "geojson-to-csv.jq", LOCATION_SCHEMA)
        assert len(csv_rows) == len(rows)
        for original, exported in zip(rows, csv_rows):
            assert original["record_id"] == exported["record_id"]
            assert json.loads(exported["properties"]) == original["properties"]
            assert exported["latitude"] == exported["longitude"] == ""
    assert len(all_rows) == 89
    assert all(row["parent_record_id"] is None or row["parent_record_id"] in all_rows for row in all_rows.values())
    yandex = layers["yandex/regions-and-zones"]
    assert Counter(r["country_code"] for r in yandex) == {"RU": 6, "KZ": 2}
    assert {r["site_code"] for r in yandex if r["entity_type"] == "availability_zone"} == {
        "ru-central1-a", "ru-central1-b", "ru-central1-d", "ru-central1-e", "ru-central1-m", "kz1-a"}
    assert next(r for r in yandex if r["site_code"] == "ru-central1-m")["service_scope"] == ["baremetal"]
    cities = layers["yandex/cdn-cities"]
    assert len(cities) == 35 and sum(r["country_code"] == "RU" for r in cities) == 26
    simferopol = next(r for r in cities if r["city"] == "Simferopol")
    assert simferopol["country_code"] == "UA" and simferopol["properties"]["source_country_label"] == "Russia"
    assert all(r["lifecycle_status"] == "unknown" for r in yandex + cities)
    selectel = layers["selectel/russian-hierarchy"]
    assert Counter(r["entity_type"] for r in selectel) == {"cloud_region": 3, "availability_zone": 7, "cloud_resource_pool": 18}
    pool = [r for r in selectel if r["site_code"] == "ru-6"]
    assert len(pool) == 1 and len(pool[0]["properties"]["availability_zone_record_ids"]) == 3
    assert sorted(s for values in pool[0]["properties"]["segments_by_zone"].values() for s in values) == ["ru-6a", "ru-6b", "ru-6c"]
    for row in selectel:
        assert all(identifier in all_rows for identifier in row["properties"].get("availability_zone_record_ids", []))
    assert Tables("<table><tr><th>A<th>B<tr><td>one<br>two<td>three</table>").tables == [[["A", "B"], ["one two", "three"]]]
    evolution = layers["cloudru/evolution-zones"]
    assert len(evolution) == 3 and all(r["parent_record_id"] is None for r in evolution)
    validator = load_validator(LOCATION_SCHEMA)
    missing = copy.deepcopy(evolution[0])
    missing["properties"].pop("parent_identity_evidence")
    assert not validator.is_valid(missing)
    missing = copy.deepcopy(evolution[0])
    missing["schema_version"] = "1.2.0"
    assert not validator.is_valid(missing)
    assert not load_validator().is_valid(evolution[0])  # older contract stays intact
    ix = layers["ixcellerate/data-centers"]
    assert Counter(r["lifecycle_status"] for r in ix) == {"operational": 5, "planned": 3, "in_development": 2}
    assert {r["site_code"] for r in ix if r["lifecycle_status"] == "in_development"} == {"MOS7", "MOS11"}


def networks():
    declarations = read(f"data/network/yandex-prefixes.{TAG}.json")
    routes = read(f"data/network/yandex-routing.{TAG}.json")
    for collection in (declarations, routes):
        validate_network_collection(collection)
        assert all(r["properties"]["physical_country_code"] is None for r in collection["records"])
        assert all(r["source_sha256"] == sha256(ROOT / r["raw_source_ref"]) for r in collection["records"])
    assert len(declarations["records"]) == 164 and len(routes["records"]) == 56
    cdn = [r for r in declarations["records"] if r["service"] == "yandex_cloud_cdn"]
    assert len(cdn) == 115 and Counter(r["ip_family"] for r in cdn) == {4: 107, 6: 8}
    assert {r["prefix"] for r in cdn} == set(read(raw_path("cdn_prefixes"))["prefixes"])
    nets = [ipaddress.ip_network(r["prefix"]) for r in cdn]
    assert sum(a.version == b.version and a.overlaps(b) for i, a in enumerate(nets) for b in nets[i+1:]) == 1
    raw = read(raw_path("yandex_routes"))["data"]
    assert {r["prefix"] for r in routes["records"]} == {r["prefix"] for r in raw["prefixes"]}
    assert all(r["asn"] == 200350 and r["observed_at"] == "2026-10-19T00:00:00Z" for r in routes["records"])


def registry():
    fixture = ("2|ripencc|1780783199|3|19700101|20260606|+0200\n"
               "ripencc|*|asn|*|3|summary\n"
               "ripencc|RU|asn|100|2|20200101|allocated|example\n"
               "ripencc|US|asn|200|1|*|assigned|example\n"
               "ripencc||asn|300|2||reserved\n")
    ranges, _ = parse_ripe(fixture)
    starts = [r["start_asn"] for r in ranges]
    assert lookup_registration(101, ranges, starts)["country_code"] == "RU"
    assert all(lookup_registration(n, ranges, starts) is None for n in (99, 102, 300))
    must_reject(parse_ripe, fixture.replace("|200|1|", "|101|1|"))
    must_reject(parse_ripe, fixture.replace("|3|19700101", "|4|19700101"))
    must_reject(parse_ripe, fixture.replace("20260606", "20261019"))
    text = bz2.decompress(raw_path("ripe").read_bytes()).decode()
    ranges, profile = parse_ripe(text)
    assert profile["resource_record_counts"] == {"asn": 48682, "ipv4": 99969, "ipv6": 111157}
    path = ROOT / f"data/russia/cdn-asn-comparison.{TAG}.json"
    value = read(path)
    load_validator(ROOT / "schema/cdn-comparison.schema.json").validate(value)
    expected = comparison_rows(read(ASN_PATH)["features"], ranges)
    for row in expected:
        row["rir_registration"] = row.pop("apnic_registration")
    assert value["records"] == [r for r in expected if r["rir_registration"] and r["rir_registration"]["country_code"] == "RU"]
    assert len(value["records"]) == 280
    assert sum(r["provider_record_ids"]["apple"] is not None for r in value["records"]) == 70
    for row in value["records"]:
        registration = row["rir_registration"]
        fields = text.splitlines()[registration["source_line"] - 1].split("|")
        assert fields[:3] == ["ripencc", "RU", "asn"]
        assert int(fields[3]) <= row["asn"] < int(fields[3]) + int(fields[4])
        assert "country_code" not in row  # no physical geography field
    csv_rows = projected(path, "cdn-comparison-to-csv.jq")
    assert len(csv_rows) == len(value["records"])
    assert all(r["rir_registry"] == "ripencc" and r["rir_registration_country"] == "RU" for r in csv_rows)


def applications():
    value, raw = read(PATH), read(raw_path("dns"))["records"]
    validate(value)
    assert len(value["records"]) == len(raw) == 15 and len(value["entities"]) == 5
    assert Counter(r["query_result"] for r in value["records"]) == {"answered": 8, "noerror_no_requested_rr": 7}
    for row in value["records"]:
        original = raw[int(row["source_json_pointer"].rsplit("/", 1)[1])]
        assert row["dns_response"] == original["response"]
        assert row["observed_at"] == original["queried_at"] and row["resolver_url"] == original["resolver_url"]
        assert row["origin_country_code"] is None and row["facility_record_id"] is None
        assert not row["origin_evidence"]
        assert {a["address"] for a in row["address_observations"]} == {
            a["data"] for a in original["response"].get("Answer", []) if a["type"] in (1, 28)}
        assert all(not a["published_prefix_matches"] for a in row["address_observations"])
        for address in row["address_observations"]:
            network = address["network_attribution"]
            if network:
                assert network["registry_country_code"] == "RU" and network["physical_country_code"] is None
    bybit = next(e for e in value["entities"] if e["name"] == "Bybit")
    assert bybit["provider_declared_hosting"]["country_code"] == "SG" and bybit["origin_country_code"] is None
    assert next(e for e in value["entities"] if e["name"] == "EXMO.me")["service_status"]["reported_at"] == "2026-07-24"
    assert all(r["entity_id"] not in {"application:entity:garantex", "application:entity:grinex"} for r in value["records"])
    invalid = copy.deepcopy(value)
    invalid["records"][0]["origin_country_code"] = "RU"
    assert not load_validator(SCHEMA).is_valid(invalid)
    invalid = copy.deepcopy(value)
    invalid["records"].append(copy.deepcopy(value["records"][0]))
    must_reject(validate, invalid)
    for query, expected in [({"rrtype": "AAAA", "response": {"Status": 0}}, "noerror_no_requested_rr"),
                            ({"rrtype": "A", "response": {"Status": 3}}, "nxdomain"),
                            ({"rrtype": "A", "response": {"Status": 2}}, "dns_error"),
                            ({"error": "timeout"}, "transport_error")]:
        assert query_result(query) == expected
    csv_rows = projected(ROOT / PATH, "application-endpoint-to-csv.jq", SCHEMA)
    assert len(csv_rows) == len(value["records"])
    for original, exported in zip(value["records"], csv_rows):
        assert original["record_id"] == exported["record_id"]
        for key in ("dns_response", "address_observations", "source", "cnames"):
            assert json.loads(exported[key]) == original[key]


def manifests_and_regeneration():
    baseline, current = read(BASELINE), read(f"data/manifest.{TAG}.json")
    frozen = read(f"data/raw/repository/manifest-before-geography.{TAG}.json")
    assert frozen["layers"][:33] == baseline["layers"]
    assert current["network_evidence_layers"][:4] == baseline["network_evidence_layers"]
    assert current["observation_comparison_views"][:2] == baseline["observation_comparison_views"]
    assert frozen["record_count"] == 28019 and frozen["layer_count"] == 39
    assert current["record_count"] == sum(l["record_count"] for l in current["layers"])
    assert current["layers"][33:] == frozen["layers"][33:]
    assert frozen["network_evidence_record_count"] == 3387 and frozen["network_evidence_layer_count"] == 6
    assert current["network_evidence_layers"][:6] == frozen["network_evidence_layers"]
    assert current["application_endpoint_record_count"] == 15 and current["application_entity_count"] == 5
    assert current["observation_comparison_view_count"] == 3
    assert current["schema"]["path"] == "schema/location-v1.3.schema.json"
    all_features = [f for layer in current["layers"] for f in read(layer["files"]["geojson"]["path"])["features"]]
    view = read(f"data/russia/locations-and-observations.{TAG}.geojson")["features"]
    assert view == sorted([f for f in all_features if f["properties"]["country_code"] == "RU"], key=lambda f: f["properties"]["record_id"])
    assert len(view) == 178 and sum(f["geometry"] is None for f in view) == 86
    assert len({f["properties"]["record_id"] for f in view}) == len(view)
    assert read(f"data/russia/enrichment-assessment.{TAG}.json")["baseline"]["ru_record_count"] == 100
    names = [f"data/{layer}.{TAG}.{suffix}" for layer in (*LOCATION_LAYERS, "russia/locations-and-observations")
             for suffix in ("geojson", "report.json")]
    names += [f"data/network/{layer}.{TAG}.{suffix}" for layer in NETWORK_LAYERS for suffix in ("json", "report.json")]
    names += [f"data/{layer}.{TAG}.{suffix}" for layer in ("applications/crypto-endpoints", "russia/cdn-asn-comparison")
              for suffix in ("json", "report.json")]
    names.append(f"data/russia/enrichment-implementation.{TAG}.json")
    for section in ("layers", "views", "network_evidence_layers", "application_endpoint_layers", "observation_comparison_views"):
        for entry in current[section]:
            for file in entry["files"].values():
                assert file["sha256"] == sha256(ROOT / file["path"])
    for key in set(SOURCES) | set(EXTRA):
        source(key)
    receipt = read(BASELINE + ".provenance.json")
    assert receipt["sha256"] == sha256(ROOT / BASELINE)
    assert sha256(ROOT / "data/manifest.20261011.json") == "f408815674b2e195bc98a9b911b70154ec1b33847b3501147da102fcae964730"
    with tempfile.TemporaryDirectory(prefix="russia-enrichment-") as temp:
        subprocess.run([sys.executable, "-B", "scripts/update_russia_enrichment.py", "--output-root", temp], cwd=ROOT, check=True)
        for name in names:
            assert (ROOT / name).read_bytes() == (Path(temp) / name).read_bytes(), name
        subprocess.run([sys.executable, "-B", "scripts/review_russia_enrichment.py", "--output-root", temp],
                       cwd=ROOT, check=True, capture_output=True)
        name = f"data/russia/enrichment-assessment.{TAG}.json"
        assert (ROOT / name).read_bytes() == (Path(temp) / name).read_bytes()
        assert not list(Path(temp).rglob("*.csv"))


if __name__ == "__main__":
    locations()
    networks()
    registry()
    applications()
    manifests_and_regeneration()
    print("Validated 89 new location records, 220 network records, 15 DNS queries, 280 RU-registered ASN comparisons and the 178-record geographic view; prior layers preserved.")
