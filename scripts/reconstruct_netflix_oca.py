#!/usr/bin/env python3
"""Reconstruct Netflix OCA hostnames from retained legacy filename components."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data/Netflix_OCAs_02-08-2023.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data/recovered/netflix_oca.20230802.csv"
DEFAULT_REPORT = REPO_ROOT / "data/recovered/netflix_oca.20230802.recovery.json"
SNAPSHOT_DATE = "2023-08-02"

REQUIRED_FIELDS = (
    "IP Version",
    "C Number",
    "Airport Code",
    "Airport Code Number",
    "ISP Name",
    "CDN Type",
)

RECOVERY_FIELDS = (
    "observation_id",
    "hostname",
    "hostname_pattern",
    "hostname_reconstruction_status",
    "reconstruction_method",
    "reconstruction_confidence",
    "isp_slug",
    "logical_hostname_observation_count",
    "source_row_number",
    "source_snapshot_date",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reconstruct(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    ip_version = row["IP Version"].strip().lower()
    c_number = row["C Number"].strip().lower()
    airport_code = row["Airport Code"].strip().lower()
    airport_number = f"{int(row['Airport Code Number']):03d}"
    cdn_type = row["CDN Type"].strip().upper()

    if ip_version not in {"ipv4", "ipv6"}:
        raise ValueError(f"Unsupported IP version: {row['IP Version']!r}")
    if not re.fullmatch(r"c\d+", c_number):
        raise ValueError(f"Invalid C Number: {row['C Number']!r}")
    if not re.fullmatch(r"[a-z0-9]{3}", airport_code):
        raise ValueError(f"Invalid airport code: {row['Airport Code']!r}")

    prefix = f"{ip_version}-{c_number}-{airport_code}{airport_number}"
    if cdn_type == "IXP":
        hostname = f"{prefix}-ix.1.oca.nflxvideo.net"
        return hostname, hostname, "complete", "high", ""

    if cdn_type != "ISP":
        raise ValueError(f"Unsupported CDN type: {row['CDN Type']!r}")

    isp_name = row["ISP Name"].strip()
    if not isp_name:
        pattern = f"{prefix}-<isp-slug>-isp.1.oca.nflxvideo.net"
        return "", pattern, "partial", "partial", ""

    isp_slug = re.sub(r"\s+", "-", isp_name.lower())
    if not re.fullmatch(r"[a-z0-9-]+", isp_slug):
        raise ValueError(f"ISP name cannot be converted safely: {isp_name!r}")
    hostname = f"{prefix}-{isp_slug}-isp.1.oca.nflxvideo.net"
    confidence = "medium" if re.search(r"\s", isp_name) else "high"
    return hostname, hostname, "complete", confidence, isp_slug


def main() -> None:
    args = parse_args()
    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{args.input} has no CSV header")
        missing = sorted(set(REQUIRED_FIELDS) - set(reader.fieldnames))
        if missing:
            raise ValueError(
                f"{args.input} is missing required columns: {', '.join(missing)}"
            )
        input_fields = reader.fieldnames
        input_rows = list(reader)

    reconstructed: list[dict[str, str]] = []
    complete_hostnames: list[str] = []
    for source_index, row in enumerate(input_rows):
        hostname, pattern, status, confidence, isp_slug = reconstruct(row)
        if hostname:
            complete_hostnames.append(hostname)
        reconstructed.append(
            {
                "observation_id": f"netflix-oca-20230802-{source_index + 1:05d}",
                "hostname": hostname,
                "hostname_pattern": pattern,
                "hostname_reconstruction_status": status,
                "reconstruction_method": "legacy_component_template_v1",
                "reconstruction_confidence": confidence,
                "isp_slug": isp_slug,
                "source_row_number": str(source_index + 1),
                "source_snapshot_date": SNAPSHOT_DATE,
                **row,
            }
        )

    hostname_counts = Counter(complete_hostnames)
    for row in reconstructed:
        hostname = row["hostname"]
        row["logical_hostname_observation_count"] = (
            str(hostname_counts[hostname]) if hostname else ""
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_fields = list(RECOVERY_FIELDS) + input_fields
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(reconstructed)

    confidence_counts = Counter(row["reconstruction_confidence"] for row in reconstructed)
    partial_rows = [
        {
            "source_row_number": int(row["source_row_number"]),
            "hostname_pattern": row["hostname_pattern"],
            "ip_version": row["IP Version"],
            "c_number": row["C Number"],
            "airport_code": row["Airport Code"],
            "airport_code_number": row["Airport Code Number"],
            "hosting_provider": row["Hosting Provider"],
        }
        for row in reconstructed
        if row["hostname_reconstruction_status"] == "partial"
    ]
    report = {
        "dataset": "Netflix OCA 2023 hostname reconstruction",
        "input_file": str(args.input.relative_to(REPO_ROOT)),
        "input_record_count": len(input_rows),
        "input_sha256": sha256(args.input),
        "complete_reconstruction_count": len(complete_hostnames),
        "partial_reconstruction_count": len(partial_rows),
        "unique_reconstructed_hostname_count": len(hostname_counts),
        "duplicate_hostname_observation_count": len(complete_hostnames)
        - len(hostname_counts),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "partial_records": partial_rows,
        "output_file": str(args.output.relative_to(REPO_ROOT)),
        "output_sha256": sha256(args.output),
        "historical_tail_status": (
            "Unresolved: records omitted by the original SecurityTrails result cap are "
            "not recoverable from repository-local evidence."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print(
        f"Reconstructed {len(complete_hostnames)} of {len(input_rows)} Netflix rows "
        f"({len(hostname_counts)} unique hostnames); {len(partial_rows)} remain partial."
    )


if __name__ == "__main__":
    main()
