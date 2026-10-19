"""Verified retained-source access for the October 19 geography work."""
from __future__ import annotations

import json
from bs4 import BeautifulSoup

from location_common import REPO_ROOT, sha256

DATE, TAG = "2026-10-19", "20261019"
RAW = REPO_ROOT / "data/raw/geography-enrichment"
CATALOG = RAW / f"catalog.{TAG}.json"
BASELINE = REPO_ROOT / f"data/raw/repository/manifest-before-geography.{TAG}.json"
CLOUD_LAYERS = (
    "alibaba/regions-and-zones", "tencent/regions-and-zones", "huawei/regions",
    "baidu/regions-and-zones", "volcano/regions-and-zones",
    "kingsoft/mainland-regions-and-zones", "jd/mainland-regions-and-zones",
    "tianyi/vpc-resource-pools", "qiniu/resource-pools-and-regions",
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(key):
    item = next(s for s in read(CATALOG)["sources"] if s["source_id"] == key)
    if item["result"] != "retrieved" or sha256(REPO_ROOT / item["path"]) != item["sha256"]:
        raise ValueError(f"Unavailable or changed source: {key}")
    return item


def evidence(key):
    item = source(key)
    return {"source_id": key, "source_url": item["source_url"],
            "raw_source_ref": item["path"], "source_sha256": item["sha256"],
            "source_published_at": item.get("source_published_at"),
            "source_updated_at": item.get("source_updated_at"), "retrieved_at": item["retrieved_at"]}


def soup(key):
    return BeautifulSoup((REPO_ROOT / source(key)["path"]).read_bytes(), "html.parser")


def record_evidence(row):
    return {key: row[key] for key in ("source_url", "raw_source_ref", "source_sha256",
                                     "source_published_at", "retrieved_at")}


def baseline_layers():
    provenance = read(BASELINE.with_suffix(".json.provenance.json"))
    if sha256(BASELINE) != provenance["sha256"]:
        raise ValueError("Frozen geography baseline changed")
    layers = {layer["layer"]: layer for layer in read(BASELINE)["layers"]}
    for layer in layers.values():
        for item in layer["files"].values():
            if sha256(REPO_ROOT / item["path"]) != item["sha256"]:
                raise ValueError(f"Historical layer changed: {item['path']}")
    return layers
