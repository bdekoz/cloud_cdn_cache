#!/usr/bin/env python3
"""Reproduce the evidence audit for quarantined, unsupported location claims."""

from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup

from location_common import REPO_ROOT, repo_ref, sha256, write_json, write_provenance


RETRIEVED_AT = "2026-08-04"
BAIDU_URL = "https://cloud.baidu.com/doc/Reference/s/2jwvz23xx/"
BAIDU_PUBLISHED_AT = "2024-04-19"


def feature_count(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8")).get("features", []))


def main() -> None:
    raw_baidu = REPO_ROOT / "data/raw/baidu/service-regions.20260804.html"
    legacy_baidu = REPO_ROOT / "data/quarantine/baidu_cloud_data_centers_2.geojson"
    speculative_alibaba = REPO_ROOT / "data/quarantine/alibaba_cloud_data_centers_3.geojson"
    soup = BeautifulSoup(raw_baidu.read_bytes(), "html.parser")
    service_table = soup.find_all("table")[1]
    headers = [cell.get_text(" ", strip=True) for cell in service_table.find("tr").find_all(["th", "td"])]
    official_regions = [header for header in headers[2:] if header]
    if len(official_regions) != 8:
        raise ValueError(f"expected eight Baidu service-region columns, found {len(official_regions)}")
    write_provenance(
        raw_baidu, source_url=BAIDU_URL, retrieved_at=RETRIEVED_AT, media_type="text/html",
        source_published_at=BAIDU_PUBLISHED_AT,
        notes="Official Baidu AI Cloud service-region matrix used to audit the unsupported global legacy layer.",
    )
    output = REPO_ROOT / "data/quarantine/audit.20260804.json"
    write_json(output, {
        "alibaba_speculative_layer": {
            "feature_count": feature_count(speculative_alibaba),
            "path": repo_ref(speculative_alibaba),
            "reason": "Contains uncited estimated node, overlay, and power-capacity values; excluded from the authoritative Alibaba rebuild.",
            "sha256": sha256(speculative_alibaba),
        },
        "baidu": {
            "legacy_claim_count": feature_count(legacy_baidu),
            "legacy_path": repo_ref(legacy_baidu),
            "legacy_sha256": sha256(legacy_baidu),
            "official_region_column_count": len(official_regions),
            "official_region_labels_zh": official_regions,
            "raw_source_ref": repo_ref(raw_baidu),
            "source_sha256": sha256(raw_baidu),
            "source_published_at": BAIDU_PUBLISHED_AT,
            "source_url": BAIDU_URL,
        },
        "decision": "Exclude both quarantined files from current provider-declared views; retain them unchanged for auditability.",
        "retrieved_at": RETRIEVED_AT,
    })
    print(output.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
