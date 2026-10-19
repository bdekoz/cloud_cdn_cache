#!/usr/bin/env python3
"""Join June CDN observations to June RIPE ASN registration intervals."""
from __future__ import annotations

import argparse
import bz2
from collections import Counter
from datetime import datetime
from pathlib import Path
import re

from location_common import REPO_ROOT, load_validator, repo_ref, write_json
from russia_enrichment_common import DATE, TAG, raw_path, source
from update_cdn_comparisons import (ASN_PATH, DATASETS, PUBLISHED_AT, SCHEMA_PATH,
    comparison_rows, csv_ref, load_features, source_ref)


def parse_ripe(text: str):
    lines = [(number, line.split("|")) for number, line in enumerate(text.splitlines(), 1)
             if line.strip() and not line.startswith("#")]
    header = lines[0][1] if lines else []
    if len(header) != 7 or header[:2] != ["2", "ripencc"] or header[5] != "20260606":
        raise ValueError("Expected RIPE extended snapshot through June 6, 2026")
    data = [(number, fields) for number, fields in lines[1:] if fields[-1] != "summary"]
    summary = {fields[2]: int(fields[4]) for _, fields in lines[1:] if fields[-1] == "summary"}
    counts = Counter(fields[2] for _, fields in data)
    if len(data) != int(header[3]) or dict(counts) != summary:
        raise ValueError("RIPE header/resource summary disagrees with file")
    ranges = []
    for number, fields in data:
        if fields[2] != "asn":
            continue
        if len(fields) not in (7, 8) or fields[0] != "ripencc":
            raise ValueError(f"Invalid RIPE ASN record at line {number}")
        if fields[6] not in {"allocated", "assigned"}:
            continue
        if len(fields) != 8:
            raise ValueError(f"Missing RIPE allocation identifier at line {number}")
        start, count = int(fields[3]), int(fields[4])
        if start < 1 or count < 1 or start + count - 1 > 4_294_967_295:
            raise ValueError(f"Invalid ASN interval at line {number}")
        country = fields[1] if fields[1] not in {"", "*", "ZZ"} else None
        if country is not None and not re.fullmatch(r"[A-Z]{2}", country):
            raise ValueError(f"Invalid country at line {number}")
        date = None if fields[5] in {"", "*", "00000000"} else datetime.strptime(fields[5], "%Y%m%d").date().isoformat()
        ranges.append({"registry": "ripencc", "country_code": country, "start_asn": start,
                       "asn_count": count, "delegated_at": date, "status": fields[6], "source_line": number})
    ranges.sort(key=lambda row: row["start_asn"])
    if any(a["start_asn"] + a["asn_count"] > b["start_asn"] for a, b in zip(ranges, ranges[1:])):
        raise ValueError("Overlapping RIPE ASN intervals")
    return ranges, {"registry": "ripencc", "serial": header[2], "records_through": "2026-06-06",
                    "timezone": header[6], "resource_record_counts": dict(sorted(counts.items())),
                    "delegated_asn_range_count": len(ranges),
                    "ru_delegated_asn_count": sum(r["asn_count"] for r in ranges if r["country_code"] == "RU")}


def run(root: Path):
    receipt = source("ripe")
    ranges, profile = parse_ripe(bz2.decompress(raw_path("ripe").read_bytes()).decode("utf-8"))
    all_rows = comparison_rows(load_features(ASN_PATH), ranges)
    for row in all_rows:
        row["rir_registration"] = row.pop("apnic_registration")
    rows = [row for row in all_rows if row["rir_registration"] and row["rir_registration"]["country_code"] == "RU"]
    sources = [source_ref(ASN_PATH, "provider_asn_observations", PUBLISHED_AT, "2026-08-04"),
               source_ref(repo_ref(raw_path("ripe")), "asn_registration_country", "2026-06-06", DATE)
               | {"source_url": receipt["source_url"]}]
    collection = {"type": "CdnAsnComparison", "schema_version": "1.1.0", "built_at": DATE,
                  "view_of": "observations/cdn-mapping", "selection": "ripe_registration_country_RU",
                  "excluded_from_canonical_totals": True,
                  "missing_provider_semantics": "not_observed_in_this_snapshot",
                  "registration_country_is_not_geolocation": True,
                  "provider_columns": [{"key": key, "provider": config["provider"], "dataset": config["label"]}
                                       for key, config in DATASETS.items()], "sources": sources, "records": rows}
    load_validator(SCHEMA_PATH).validate(collection)
    path = f"data/russia/cdn-asn-comparison.{TAG}.json"
    write_json(root / path, collection)
    write_json((root / path).with_suffix(".report.json"), {
        "layer": "russia/cdn-asn-comparison", "built_at": DATE, "parser": "update_russia_comparison.py",
        "view_of": collection["view_of"], "view_excluded_from_canonical_totals": True,
        "selection": collection["selection"], "record_count": len(rows), "record_unit": "distinct_asn",
        "provider_counts": {key: sum(row["provider_record_ids"][key] is not None for row in rows) for key in DATASETS},
        "input_distinct_asn_count": len(all_rows),
        "input_asns_without_eligible_ripe_match": sum(row["rir_registration"] is None for row in all_rows),
        "ripe_snapshot": profile, "sources": sources, "schema": repo_ref(SCHEMA_PATH), "schema_version": "1.1.0",
        "source_date_note": "Registry file through June 6 and June study publication; measurement times are not individually published. October build is not a new scan.",
        "rights_note": "Study downloads have no stated data license; registry source terms apply.",
        "generated_files": [path], "derived_files": csv_ref(path)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    run(parser.parse_args().output_root)
