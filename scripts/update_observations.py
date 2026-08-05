#!/usr/bin/env python3
"""Normalize the June 2026 global CDN ASN observations as a separate layer."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from location_common import (
    REPO_ROOT,
    SCHEMA_PATH,
    SCHEMA_VERSION,
    canonical_record,
    fetch,
    repo_ref,
    sha256,
    slug,
    write_layer,
    write_provenance,
)


STUDY_URL = "https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/"
DOWNLOAD_BASE = "https://cdn.anuragbhatia.com/web/post/2026/06/cdn-mapping-across-the-globe"
PUBLISHED_AT = "2026-06-06"

DATASETS = {
    "ggc": {"provider": "Google", "label": "Google GGC", "tls_domains": ["googlevideo.com"], "file": "ggc.202606.csv"},
    "oca": {"provider": "Netflix", "label": "Netflix OCA", "tls_domains": ["oca.nflxvideo.net", "assets.nflxext.com"], "file": "oca.202606.csv"},
    "fna": {"provider": "Meta", "label": "Facebook/Meta FNA", "tls_domains": ["fbcdn.net", "fna.whatsapp.net"], "file": "fna.202606.csv"},
    "akamai": {"provider": "Akamai", "label": "Akamai", "tls_domains": ["edgesuite.net", "edgekey.net", "akamaized.net", "akamaihd.net", "akamai.net"], "file": "akamai.202606.csv"},
    "microsoft": {"provider": "Microsoft", "label": "Microsoft CDN", "tls_domains": ["microsoft.com"], "file": "microsoft.202606.csv"},
    "apple": {"provider": "Apple", "label": "Apple", "tls_domains": ["apple.com", "itunes.apple.com"], "file": "apple.202606.csv"},
    "aws-cloudfront": {"provider": "Amazon Web Services", "label": "AWS CloudFront", "tls_domains": ["amazonaws.com", "awsstatic.com"], "file": "aws-cloudfront.202606.csv"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT, help="Root beneath which data/observations is written.")
    return parser.parse_args()


def raw_path(dataset: str) -> Path:
    return REPO_ROOT / "data/raw/observations" / DATASETS[dataset]["file"]


def build_records(retrieved_at: str) -> list[dict[str, Any]]:
    records = []
    for dataset, config in DATASETS.items():
        path = raw_path(dataset)
        digest = sha256(path)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            asn = row["asn"].strip()
            as_name = row["asname"].strip()
            records.append(canonical_record(
                schema_version=SCHEMA_VERSION,
                record_id=f"observation:observed_presence:{slug(dataset)}-{asn}",
                aliases=[],
                provider=config["provider"],
                service="cdn_mapping_observation",
                entity_type="observed_presence",
                parent_record_id=None,
                jurisdiction_scope="global",
                access_status="not_applicable",
                service_scope=["tls_measurement"],
                source_collection="anurag_bhatia_cdn_mapping_2026",
                source_record_id=asn,
                name=f"AS{asn} — {as_name}",
                site_code=None,
                lifecycle_status="unknown",
                source_scope="observed",
                city=None,
                metro=None,
                subdivision=None,
                country=None,
                country_code=None,
                latitude=None,
                longitude=None,
                location_precision="unknown",
                coordinate_method="unknown",
                coordinate_crs=None,
                source_url=STUDY_URL,
                raw_source_ref=repo_ref(path),
                source_sha256=digest,
                source_published_at=PUBLISHED_AT,
                retrieved_at=retrieved_at,
                first_seen=PUBLISHED_AT,
                last_seen=PUBLISHED_AT,
                confidence="medium",
                properties={
                    "as_name": as_name,
                    "asn": int(asn),
                    "dataset": config["label"],
                    "download_url": f"{DOWNLOAD_BASE}/{dataset}.csv",
                    "measurement_method": "routed-prefix TLS certificate scan",
                    "observation_scope": "asn_presence",
                    "observed_at": PUBLISHED_AT,
                    "tls_domains": config["tls_domains"],
                },
            ))
    return records


def main() -> None:
    args = parse_args()
    raw_dir = REPO_ROOT / "data/raw/observations"
    study_path = raw_dir / "cdn-mapping-study.20260804.html"
    if args.fetch:
        fetch(STUDY_URL, study_path)
        for dataset in DATASETS:
            fetch(f"{DOWNLOAD_BASE}/{dataset}.csv", raw_path(dataset))
    if not study_path.exists():
        raise FileNotFoundError(study_path)
    write_provenance(
        study_path, source_url=STUDY_URL, retrieved_at=args.retrieved_at, media_type="text/html",
        source_published_at=PUBLISHED_AT,
        notes="Methodology page for the June 2026 TLS-certificate scan. No explicit data license was found; redistribution rights require review.",
    )
    source_manifest = []
    for dataset, config in DATASETS.items():
        path = raw_path(dataset)
        if not path.exists():
            raise FileNotFoundError(path)
        download_url = f"{DOWNLOAD_BASE}/{dataset}.csv"
        write_provenance(
            path, source_url=download_url, retrieved_at=args.retrieved_at, media_type="text/csv",
            source_published_at=PUBLISHED_AT,
            notes="Positive ASN-level CDN-presence observations from the June 2026 study. No explicit data license was found; redistribution rights require review.",
        )
        with path.open(encoding="utf-8-sig", newline="") as handle:
            count = sum(1 for _ in csv.DictReader(handle))
        source_manifest.append({"dataset": config["label"], "raw_source_ref": repo_ref(path), "record_count": count, "sha256": sha256(path), "source_url": download_url})
    asn_wise_path = raw_dir / "asn-wise-cdn-mapping.202606.csv"
    if asn_wise_path.exists():
        write_provenance(
            asn_wise_path, source_url=f"{DOWNLOAD_BASE}/ASN-wise-CDN-mapping.csv",
            retrieved_at=args.retrieved_at, media_type="text/csv", source_published_at=PUBLISHED_AT,
            notes="Cross-provider ASN matrix published with the study. Retained as corroborating evidence; individual provider CSVs are the normalized inputs because this matrix omits Apple.",
        )
    records = build_records(args.retrieved_at)
    report = write_layer(
        records=records, output_dir=args.output_root / "data/observations", layer_name="cdn-mapping",
        retrieved_at=args.retrieved_at, source_url=STUDY_URL, raw_path=study_path,
        parser_name="update_observations.py", schema_path=args.schema,
        extra_report={
            "geometry_policy": "ASN observations have null geometry; the CSVs do not contain locations.",
            "license_status": "not stated in source; review before downstream redistribution",
            "observation_date": PUBLISHED_AT,
            "provider_counts": {config["provider"]: sum(row["provider"] == config["provider"] for row in records) for config in DATASETS.values()},
            "source_files": source_manifest,
        },
    )
    print(json.dumps({"record_count": report["record_count"], "geometry_null": report["geometry_null"], "provider_counts": report["provider_counts"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
