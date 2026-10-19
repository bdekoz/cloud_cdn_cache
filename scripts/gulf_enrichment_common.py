"""Verified inputs and stable boundaries for Gulf enrichment and source monitoring."""
from __future__ import annotations

from bs4 import BeautifulSoup

import geography_enrichment_common as geography
from location_common import REPO_ROOT, sha256

DATE, TAG = geography.DATE, geography.TAG
RAW = REPO_ROOT / "data/raw/gulf-enrichment"
CATALOG = RAW / f"catalog.{TAG}.json"
BASELINE = REPO_ROOT / f"data/raw/repository/manifest-before-gulf.{TAG}.json"
read = geography.read
GULF = {"AE", "SA", "BH", "OM", "QA", "KW"}
LAYERS = ("aws/regions-and-zones", "aws/cloudfront", "aws/local-zones", "oracle/cloud-regions")
AWS_REGIONS = {"me-central-1": "AE", "me-south-1": "BH"}
OCI_REGIONS = {"me-abudhabi-1": "AE", "me-dubai-1": "AE", "me-jeddah-1": "SA", "me-riyadh-1": "SA"}


def source(key):
    local = {s["source_id"]: s for s in read(CATALOG)["sources"]}
    if key not in local:
        return geography.source(key)
    item = local[key]
    if item["result"] != "retrieved" or sha256(REPO_ROOT / item["path"]) != item["sha256"]:
        raise ValueError(f"Unavailable or changed source: {key}")
    return item


def evidence(key):
    item = source(key)
    return {"source_id": key, "source_url": item["source_url"], "raw_source_ref": item["path"],
            "source_sha256": item["sha256"], "source_published_at": item.get("source_published_at"),
            "source_updated_at": item.get("source_updated_at"), "retrieved_at": item["retrieved_at"]}


def soup(key):
    return BeautifulSoup((REPO_ROOT / source(key)["path"]).read_bytes(), "html.parser")


def baseline():
    if sha256(BASELINE) != read(BASELINE.with_suffix(".json.provenance.json"))["sha256"]:
        raise ValueError("Frozen pre-Gulf manifest changed")
    manifest = read(BASELINE)
    for layer in manifest["layers"]:
        for item in layer["files"].values():
            if sha256(REPO_ROOT / item["path"]) != item["sha256"]:
                raise ValueError(f"Historical layer changed: {item['path']}")
    return manifest
