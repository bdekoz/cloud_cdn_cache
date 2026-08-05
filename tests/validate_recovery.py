#!/usr/bin/env python3
"""Validate the checked-in Meta and Netflix recovery artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_meta() -> None:
    raw_path = REPO_ROOT / "data/raw/meta/fna.20240524.retrieved-20260804.csv"
    manifest_path = raw_path.with_suffix(".provenance.json")
    output_path = REPO_ROOT / "data/recovered/meta_fna.20240524.csv"
    report_path = REPO_ROOT / "data/recovered/meta_fna.20240524.recovery.json"
    raw = read_csv(raw_path)
    recovered = read_csv(output_path)
    manifest = read_json(manifest_path)
    report = read_json(report_path)

    assert len(raw) == 8360
    assert len(recovered) == 8360
    assert len({row["FNA String"] for row in raw}) == 8008
    assert len({row["source_record_id"] for row in recovered}) == 8008
    assert all(int(row["source_record_observation_count"]) >= 1 for row in recovered)
    assert all(
        int(row["source_record_observation_number"])
        <= int(row["source_record_observation_count"])
        for row in recovered
    )
    assert sum(row["legacy_match_status"] == "matched" for row in recovered) == 8353
    assert sum(row["legacy_match_status"] == "source_only" for row in recovered) == 7
    assert Counter(
        row["airport_code"]
        for row in recovered
        if row["legacy_match_status"] == "source_only"
    ) == Counter({"REC": 3, "LIM": 2, "BNU": 1, "TFL": 1})
    assert len({row["ipv4_asn"] for row in recovered if row["ipv4_asn"]}) == 1795
    assert len({row["ipv6_asn"] for row in recovered if row["ipv6_asn"]}) == 1748
    assert all(row["latitude"] and row["longitude"] for row in recovered)
    assert manifest["raw_sha256"] == sha256(raw_path)
    assert manifest["raw_record_count"] == len(raw)
    assert report["output_sha256"] == sha256(output_path)


def validate_netflix() -> None:
    output_path = REPO_ROOT / "data/recovered/netflix_oca.20230802.csv"
    report_path = REPO_ROOT / "data/recovered/netflix_oca.20230802.recovery.json"
    recovered = read_csv(output_path)
    report = read_json(report_path)
    complete = [
        row for row in recovered if row["hostname_reconstruction_status"] == "complete"
    ]
    partial = [
        row for row in recovered if row["hostname_reconstruction_status"] == "partial"
    ]
    hostname_pattern = re.compile(
        r"^ipv[46]-c\d+-[a-z0-9]{3}\d{3}-(?:ix|[a-z0-9-]+-isp)"
        r"\.1\.oca\.nflxvideo\.net$"
    )

    assert len(recovered) == 9507
    assert len(complete) == 9501
    assert len(partial) == 6
    assert len({row["hostname"] for row in complete}) == 9044
    assert Counter(row["reconstruction_confidence"] for row in recovered) == Counter(
        {"high": 8546, "medium": 955, "partial": 6}
    )
    assert all(hostname_pattern.fullmatch(row["hostname"]) for row in complete)
    assert all("<isp-slug>" in row["hostname_pattern"] for row in partial)
    assert report["output_sha256"] == sha256(output_path)


def main() -> None:
    validate_meta()
    validate_netflix()
    print("Recovery validation passed: Meta 8,360 rows; Netflix 9,501 complete + 6 partial.")


if __name__ == "__main__":
    main()
