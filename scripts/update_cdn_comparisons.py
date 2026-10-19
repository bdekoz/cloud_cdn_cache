#!/usr/bin/env python3
"""Derive Apple and India views without adding observations or location claims."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime
import gzip
import json
from pathlib import Path
import re

from location_common import REPO_ROOT, load_validator, repo_ref, sha256, write_json
from update_observations import DATASETS, PUBLISHED_AT


DATE = "2026-10-19"
TAG = "20261019"
ASN_PATH = "data/observations/cdn-mapping.20260804.geojson"
CITY_PATH = "data/observations/cdn-mapping-cities.20260805.geojson"
APNIC_PATH = "data/raw/apnic/delegated-apnic-extended.20260606.gz"
SCHEMA_PATH = REPO_ROOT / "schema/cdn-comparison.schema.json"
PROVIDER_KEYS = tuple(DATASETS)


def parse_apnic(text: str) -> tuple[list[dict], dict]:
    """Read delegated ASN ranges; registration country never supplies geometry."""
    lines = [(i, line.split("|")) for i, line in enumerate(text.splitlines(), 1)
             if line.strip() and not line.startswith("#")]
    header = lines[0][1] if lines else []
    if len(header) != 7 or header[:3] != ["2.3", "apnic", "20260606"]:
        raise ValueError("expected APNIC extended snapshot serial 20260606")
    data = [(i, fields) for i, fields in lines[1:] if fields[-1] != "summary"]
    if len(data) != int(header[3]):
        raise ValueError("APNIC header record count disagrees with file")
    summary = {p[2]: int(p[4]) for _, p in lines[1:] if p[-1] == "summary"}
    counts = Counter(p[2] for _, p in data)
    if dict(counts) != summary:
        raise ValueError("APNIC resource summary disagrees with data rows")
    ranges = []
    for line_number, fields in data:
        if fields[2] != "asn":
            continue
        if len(fields) < 8 or fields[0] != "apnic":
            raise ValueError(f"invalid APNIC ASN record at line {line_number}")
        if fields[6] not in {"allocated", "assigned"}:
            continue
        start, count = int(fields[3]), int(fields[4])
        if start < 1 or count < 1 or start + count - 1 > 4_294_967_295:
            raise ValueError(f"invalid ASN range at line {line_number}")
        cc = fields[1]
        if cc not in {"", "*", "ZZ"} and not re.fullmatch(r"[A-Z]{2}", cc):
            raise ValueError(f"invalid country at line {line_number}")
        delegated_at = None
        if fields[5] not in {"", "*", "00000000"}:
            delegated_at = datetime.strptime(fields[5], "%Y%m%d").date().isoformat()
        ranges.append({
            "country_code": cc if cc not in {"", "*", "ZZ"} else None,
            "start_asn": start, "asn_count": count, "delegated_at": delegated_at,
            "status": fields[6], "source_line": line_number,
        })
    ranges.sort(key=lambda row: row["start_asn"])
    for left, right in zip(ranges, ranges[1:]):
        if left["start_asn"] + left["asn_count"] > right["start_asn"]:
            raise ValueError("overlapping APNIC delegated ASN ranges")
    return ranges, {
        "serial": header[2], "records_through": datetime.strptime(header[5], "%Y%m%d").date().isoformat(),
        "timezone": header[6], "resource_record_counts": dict(sorted(counts.items())),
        "delegated_asn_range_count": len(ranges),
        "india_delegated_asn_count": sum(r["asn_count"] for r in ranges if r["country_code"] == "IN"),
    }


def lookup_registration(asn: int, ranges: list[dict], starts: list[int]) -> dict | None:
    position = bisect_right(starts, asn) - 1
    if position < 0:
        return None
    row = ranges[position]
    return dict(row) if asn < row["start_asn"] + row["asn_count"] else None


def source_ref(path: str, role: str, published: str, retrieved: str) -> dict:
    return {"path": path, "sha256": sha256(REPO_ROOT / path), "role": role,
            "source_published_at": published, "retrieved_at": retrieved}


def load_features(path: str) -> list[dict]:
    features = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))["features"]
    ids = [f["properties"]["record_id"] for f in features]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate source record ID in {path}")
    return features


def comparison_rows(features: list[dict], ranges: list[dict]) -> list[dict]:
    by_provider = {config["provider"]: key for key, config in DATASETS.items()}
    starts = [r["start_asn"] for r in ranges]
    grouped = {}
    for feature in features:
        row = feature["properties"]
        detail = row["properties"]
        key = by_provider[row["provider"]]
        asn = detail["asn"]
        if (type(asn) is not int or not 1 <= asn <= 4_294_967_295
                or row["service"] != "cdn_mapping_observation"
                or detail["dataset"] != DATASETS[key]["label"]
                or row["source_published_at"] != PUBLISHED_AT
                or feature["geometry"] is not None or row["country_code"] is not None):
            raise ValueError(f"unexpected ASN observation semantics: {row['record_id']}")
        result = grouped.setdefault(asn, {
            "asn": asn, "as_names": set(),
            "apnic_registration": lookup_registration(asn, ranges, starts),
            "provider_record_ids": dict.fromkeys(PROVIDER_KEYS),
        })
        if result["provider_record_ids"][key] is not None:
            raise ValueError(f"duplicate provider/ASN observation: {key}/AS{asn}")
        result["as_names"].add(detail["as_name"])
        result["provider_record_ids"][key] = row["record_id"]
    return [{**grouped[asn], "as_names": sorted(grouped[asn]["as_names"])} for asn in sorted(grouped)]


def csv_ref(path: str) -> dict:
    csv_path = str(Path(path).with_suffix(".csv"))
    return {"csv": {"path": csv_path, "source": path, "generator": f"make {csv_path}"}}


def write_comparison(output_root: Path, name: str, rows: list[dict], sources: list[dict],
                     apnic_profile: dict, selection: str) -> dict:
    path = f"data/{name}.{TAG}.json"
    collection = {
        "type": "CdnAsnComparison", "schema_version": "1.0.0", "built_at": DATE,
        "view_of": "observations/cdn-mapping", "selection": selection,
        "excluded_from_canonical_totals": True,
        "missing_provider_semantics": "not_observed_in_this_snapshot",
        "registration_country_is_not_geolocation": True,
        "provider_columns": [{"key": key, "provider": config["provider"], "dataset": config["label"]}
                             for key, config in DATASETS.items()],
        "sources": sources, "records": rows,
    }
    load_validator(SCHEMA_PATH).validate(collection)
    write_json(output_root / path, collection)
    report = {
        "layer": name, "built_at": DATE, "parser": "update_cdn_comparisons.py",
        "view_of": collection["view_of"], "view_excluded_from_canonical_totals": True,
        "selection": selection, "record_count": len(rows), "record_unit": "distinct_asn",
        "provider_counts": {key: sum(r["provider_record_ids"][key] is not None for r in rows)
                            for key in PROVIDER_KEYS},
        "apple_only_asn_count": sum(r["provider_record_ids"]["apple"] is not None
                                    and all(v is None for k, v in r["provider_record_ids"].items() if k != "apple")
                                    for r in rows),
        "unmatched_apnic_asn_count": sum(r["apnic_registration"] is None for r in rows),
        "unknown_apnic_country_count": sum(r["apnic_registration"] is not None
                                           and r["apnic_registration"]["country_code"] is None for r in rows),
        "apnic_snapshot": apnic_profile, "sources": sources,
        "schema": repo_ref(SCHEMA_PATH), "schema_version": "1.0.0",
        "source_date_note": "June publication and registry snapshot; October derivation is not a new scan.",
        "rights_note": "Study downloads have no stated data license; APNIC conditions remain in the raw header.",
        "generated_files": [path], "derived_files": csv_ref(path),
    }
    write_json((output_root / path).with_suffix(".report.json"), report)
    return report


def write_feature_view(output_root: Path, name: str, features: list[dict], source: dict,
                       view_of: str, selection: str) -> None:
    path = f"data/{name}.{TAG}.geojson"
    features = sorted(features, key=lambda f: f["properties"]["record_id"])
    write_json(output_root / path, {
        "type": "FeatureCollection", "metadata": {
            "built_at": DATE, "view_of": view_of, "selection": selection,
            "excluded_from_canonical_totals": True, "source": source,
        }, "features": features,
    })
    write_json((output_root / path).with_suffix(".report.json"), {
        "layer": name, "built_at": DATE, "view_of": view_of, "selection": selection,
        "view_excluded_from_canonical_totals": True, "record_count": len(features),
        "provider_counts": dict(sorted(Counter(f["properties"]["provider"] for f in features).items())),
        "geometry_null": sum(f["geometry"] is None for f in features),
        "sources": [source], "generated_files": [path], "derived_files": csv_ref(path),
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    apnic_path = REPO_ROOT / APNIC_PATH
    provenance = json.loads(Path(str(apnic_path) + ".provenance.json").read_text())
    if provenance["sha256"] != sha256(apnic_path):
        raise ValueError("APNIC snapshot digest disagrees with retained provenance")
    ranges, profile = parse_apnic(gzip.decompress(apnic_path.read_bytes()).decode("utf-8"))
    asn_features, city_features = load_features(ASN_PATH), load_features(CITY_PATH)
    rows = comparison_rows(asn_features, ranges)
    asn_source = source_ref(ASN_PATH, "provider_asn_observations", PUBLISHED_AT, "2026-08-04")
    registry_source = {**source_ref(APNIC_PATH, "asn_registration_country", "2026-06-06", DATE),
                       "source_url": provenance["source_url"]}
    sources = [asn_source, registry_source]
    global_report = write_comparison(args.output_root, "observations/cdn-asn-comparison", rows,
                                     sources, profile, "all_observed_asns")
    india = [r for r in rows if r["apnic_registration"] is not None
             and r["apnic_registration"]["country_code"] == "IN"]
    india_report = write_comparison(args.output_root, "india/cdn-asn-comparison", india,
                                    sources, profile, "apnic_registration_country_IN")
    write_feature_view(args.output_root, "observations/apple-asn",
                       [f for f in asn_features if f["properties"]["provider"] == "Apple"],
                       asn_source, "observations/cdn-mapping", "provider=Apple")
    write_feature_view(args.output_root, "india/cdn-cities",
                       [f for f in city_features if f["properties"]["country_code"] == "IN"],
                       source_ref(CITY_PATH, "provider_city_observations", PUBLISHED_AT, "2026-08-05"),
                       "observations/cdn-mapping-cities", "country_code=IN")
    print(json.dumps({"global_asns": global_report["record_count"],
                      "india_registered_asns": india_report["record_count"],
                      "india_provider_counts": india_report["provider_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
