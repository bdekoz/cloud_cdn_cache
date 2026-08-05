#!/usr/bin/env python3
"""Recover the fields discarded from the simplified 2024 Meta FNA layer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data/raw/meta/fna.20240524.retrieved-20260804.csv"
DEFAULT_LEGACY = REPO_ROOT / "data/Meta_FNAs_AnuragBhatia_24-05-2024.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data/recovered/meta_fna.20240524.csv"
DEFAULT_MANIFEST = (
    REPO_ROOT / "data/raw/meta/fna.20240524.retrieved-20260804.provenance.json"
)
DEFAULT_REPORT = REPO_ROOT / "data/recovered/meta_fna.20240524.recovery.json"

SOURCE_PAGE_URL = (
    "https://anuragbhatia.com/post/2024/05/"
    "facebook-fna-update-2024-and-backbone-analysis/"
)
SOURCE_EXPORT_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTD0zNZAdQOrmUB-vcp1gsWNGbfOk-t53Hfib-ftIWcHbs-4GhCBjzw4J8ZwYjqZpYARe6TvkzF6aMV/"
    "pub?output=csv&gid=1062418616&single=true"
)
SOURCE_PUBLISHED_AT = "2024-05-24"

SOURCE_FIELDS = (
    "FNA String",
    "IPv4",
    "City",
    "Country",
    "Airport Code",
    "IPv4 ASN",
    "IPv4 AS Name",
    "IPv6",
    "IPv6 ASN",
    "IPv6 AS Name",
)

OUTPUT_FIELDS = (
    "observation_id",
    "source_record_id",
    "source_record_observation_number",
    "source_record_observation_count",
    "provider",
    "service_name",
    "hostname",
    "ipv4",
    "ipv4_asn",
    "ipv4_as_name",
    "ipv6",
    "ipv6_asn",
    "ipv6_as_name",
    "city",
    "country",
    "airport_code",
    "latitude",
    "longitude",
    "location_precision",
    "coordinate_method",
    "legacy_match_status",
    "legacy_match_method",
    "legacy_match_confidence",
    "legacy_row_number",
    "legacy_point_latitude",
    "legacy_point_longitude",
    "source_row_number",
    "source_published_at",
    "source_retrieved_at",
    "source_page_url",
    "source_export_url",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--retrieved-at", default="2026-08-04")
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no CSV header")
        return reader.fieldnames, list(reader)


def require_fields(path: Path, actual: list[str], required: tuple[str, ...]) -> None:
    missing = sorted(set(required) - set(actual))
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decimal_text(value: Decimal) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def coordinate_clusters(legacy_rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    grouped: defaultdict[str, list[tuple[Decimal, Decimal]]] = defaultdict(list)
    for row in legacy_rows:
        code = row["Airport Code"].strip().upper()
        latitude = row["Latitude"].strip()
        longitude = row["Longitude"].strip()
        if code and latitude and longitude:
            grouped[code].append((Decimal(latitude), Decimal(longitude)))

    return {
        code: (
            decimal_text(median(point[0] for point in points)),
            decimal_text(median(point[1] for point in points)),
        )
        for code, points in grouped.items()
    }


def align_by_airport_code(
    source_rows: list[dict[str, str]], legacy_rows: list[dict[str, str]]
) -> tuple[dict[int, int], list[int]]:
    source_codes = [row["Airport Code"].strip().upper() for row in source_rows]
    legacy_codes = [row["Airport Code"].strip().upper() for row in legacy_rows]
    matcher = SequenceMatcher(a=source_codes, b=legacy_codes, autojunk=False)
    matched: dict[int, int] = {}
    source_only: list[int] = []

    for tag, source_start, source_end, legacy_start, legacy_end in matcher.get_opcodes():
        if tag == "equal":
            for source_index, legacy_index in zip(
                range(source_start, source_end), range(legacy_start, legacy_end)
            ):
                matched[source_index] = legacy_index
        elif tag == "delete":
            source_only.extend(range(source_start, source_end))
        else:
            raise ValueError(
                "The retrieved Meta source can no longer be aligned losslessly with the "
                f"legacy layer: unexpected {tag} block at source rows "
                f"{source_start + 1}-{source_end}, legacy rows "
                f"{legacy_start + 1}-{legacy_end}"
            )

    if len(matched) != len(legacy_rows):
        raise ValueError(
            f"Only {len(matched)} of {len(legacy_rows)} legacy rows aligned to the source"
        )
    return matched, source_only


def observation_id(row: dict[str, str], ordinal: int) -> str:
    identity = "\x1f".join(
        (row["FNA String"], row["IPv4"], row["IPv6"], str(ordinal))
    )
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"meta-fna-20240524-{suffix}"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    source_fields, source_rows = read_csv(args.source)
    legacy_fields, legacy_rows = read_csv(args.legacy)
    require_fields(args.source, source_fields, SOURCE_FIELDS)
    require_fields(
        args.legacy, legacy_fields, ("Airport Code", "Latitude", "Longitude")
    )

    matched, source_only = align_by_airport_code(source_rows, legacy_rows)
    cluster_coordinates = coordinate_clusters(legacy_rows)
    hostname_counts = Counter(row["FNA String"].strip().lower() for row in source_rows)
    hostname_ordinals: Counter[str] = Counter()
    recovered_rows: list[dict[str, str | int]] = []

    for source_index, source in enumerate(source_rows):
        hostname = source["FNA String"].strip().lower()
        airport_code = source["Airport Code"].strip().upper()
        hostname_ordinals[hostname] += 1
        ordinal = hostname_ordinals[hostname]
        latitude, longitude = cluster_coordinates.get(airport_code, ("", ""))
        legacy_index = matched.get(source_index)
        legacy = legacy_rows[legacy_index] if legacy_index is not None else None

        recovered_rows.append(
            {
                "observation_id": observation_id(source, ordinal),
                "source_record_id": hostname,
                "source_record_observation_number": ordinal,
                "source_record_observation_count": hostname_counts[hostname],
                "provider": "Meta",
                "service_name": "Meta Network Appliance",
                "hostname": hostname,
                "ipv4": source["IPv4"].strip(),
                "ipv4_asn": source["IPv4 ASN"].strip(),
                "ipv4_as_name": source["IPv4 AS Name"].strip(),
                "ipv6": source["IPv6"].strip(),
                "ipv6_asn": source["IPv6 ASN"].strip(),
                "ipv6_as_name": source["IPv6 AS Name"].strip(),
                "city": source["City"].strip(),
                "country": source["Country"].strip(),
                "airport_code": airport_code,
                "latitude": latitude,
                "longitude": longitude,
                "location_precision": "airport_or_city",
                "coordinate_method": "median_of_legacy_airport_code_cluster",
                "legacy_match_status": "matched" if legacy else "source_only",
                "legacy_match_method": "ordered_airport_code_sequence",
                "legacy_match_confidence": "medium" if legacy else "not_applicable",
                "legacy_row_number": legacy_index + 1 if legacy_index is not None else "",
                "legacy_point_latitude": legacy["Latitude"].strip() if legacy else "",
                "legacy_point_longitude": legacy["Longitude"].strip() if legacy else "",
                "source_row_number": source_index + 1,
                "source_published_at": SOURCE_PUBLISHED_AT,
                "source_retrieved_at": args.retrieved_at,
                "source_page_url": SOURCE_PAGE_URL,
                "source_export_url": SOURCE_EXPORT_URL,
            }
        )

    missing_coordinates = [
        row["source_row_number"]
        for row in recovered_rows
        if not row["latitude"] or not row["longitude"]
    ]
    if missing_coordinates:
        raise ValueError(
            f"Recovered rows lack a coordinate cluster: {missing_coordinates[:10]}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(recovered_rows)

    source_only_details = [
        {
            "source_row_number": index + 1,
            "hostname": source_rows[index]["FNA String"].strip().lower(),
            "airport_code": source_rows[index]["Airport Code"].strip().upper(),
            "ipv4": source_rows[index]["IPv4"].strip(),
            "ipv6": source_rows[index]["IPv6"].strip(),
        }
        for index in source_only
    ]
    duplicate_hostnames = sum(count > 1 for count in hostname_counts.values())
    manifest = {
        "dataset": "Meta FNA source observations",
        "published_at": SOURCE_PUBLISHED_AT,
        "retrieved_at": args.retrieved_at,
        "source_page_url": SOURCE_PAGE_URL,
        "source_export_url": SOURCE_EXPORT_URL,
        "raw_file": str(args.source.relative_to(REPO_ROOT)),
        "raw_bytes": args.source.stat().st_size,
        "raw_sha256": sha256(args.source),
        "raw_record_count": len(source_rows),
        "raw_unique_hostname_count": len(hostname_counts),
        "license_status": "Upstream redistribution license not stated; verify before publishing.",
        "mutability_note": (
            "The published Google Sheet is mutable. This manifest identifies the exact "
            "retrieved snapshot rather than asserting it is an immutable 2024 export."
        ),
    }
    report = {
        "dataset": "Meta FNA 2024 recovery",
        "source_record_count": len(source_rows),
        "source_unique_hostname_count": len(hostname_counts),
        "source_duplicate_hostname_count": duplicate_hostnames,
        "source_duplicate_observation_count": len(source_rows) - len(hostname_counts),
        "source_unique_ipv4_asn_count": len(
            {row["IPv4 ASN"].strip() for row in source_rows if row["IPv4 ASN"].strip()}
        ),
        "source_unique_ipv6_asn_count": len(
            {row["IPv6 ASN"].strip() for row in source_rows if row["IPv6 ASN"].strip()}
        ),
        "legacy_record_count": len(legacy_rows),
        "legacy_matched_record_count": len(matched),
        "source_only_record_count": len(source_only),
        "source_only_records": source_only_details,
        "output_file": str(args.output.relative_to(REPO_ROOT)),
        "output_sha256": sha256(args.output),
        "coordinate_method": "median_of_legacy_airport_code_cluster",
        "match_warning": (
            "Legacy row matching uses ordered airport-code alignment. Repeated airport "
            "codes make the per-row link medium-confidence; recovered identity and network "
            "fields come directly from the source snapshot and do not depend on this link."
        ),
    }
    write_json(args.manifest, manifest)
    write_json(args.report, report)

    print(
        f"Recovered {len(source_rows)} Meta observations ({len(hostname_counts)} unique "
        f"hostnames); matched {len(matched)} legacy rows and retained {len(source_only)} "
        "source-only rows."
    )


if __name__ == "__main__":
    main()
