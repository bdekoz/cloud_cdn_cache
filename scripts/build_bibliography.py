#!/usr/bin/env python3
"""Index retained enrichment sources, including unavailable and review-only leads."""
from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from geography_enrichment_common import BASELINE, CATALOG, CLOUD_LAYERS, DATE, TAG, baseline_layers, read
from location_common import REPO_ROOT, repo_ref, sha256, write_json

PUBLISHERS = {
    "chindatagroup.com": "Chindata", "lingqiu.gov.cn": "Lingqiu County Government",
    "geonames.org": "GeoNames", "amazon.com": "Amazon Web Services", "oracle.com": "Oracle",
    "alibabacloud.com": "Alibaba Cloud", "tencentcloud.com": "Tencent Cloud",
    "huaweicloud.com": "Huawei Cloud", "microsoft.com": "Microsoft", "baidu.com": "Baidu",
    "volcengine.com": "Volcano Engine", "ksyun.com": "Kingsoft Cloud", "jdcloud.com": "JD Cloud",
    "ctyun.cn": "China Telecom / Tianyi Cloud", "qiniu.com": "Qiniu", "anuragbhatia.com": "Anurag Bhatia",
    "apple.com": "Apple", "ripe.net": "RIPE NCC", "apnic.net": "APNIC", "yandex.com": "Yandex",
    "yandex.ru": "Yandex", "yandex.cloud": "Yandex Cloud", "selectel.ru": "Selectel",
    "cloud.ru": "Cloud.ru", "ixcellerate.ru": "IXcellerate", "miit.gov.cn": "Ministry of Industry and Information Technology, China",
}


def title_for(item, path):
    if item.get("title"):
        return item["title"]
    if path and ".html" in path.name:
        body = path.read_bytes()
        if body.startswith(b"\x1f\x8b"):
            body = gzip.decompress(body)
        title = BeautifulSoup(body, "html.parser").find("title")
        if title:
            return " ".join(title.get_text(" ", strip=True).split())[:240]
    return item.get("source_id") or (path.name if path else item["source_url"])


def build():
    entries = {}

    def add(item, group, default_role):
        url = item.get("source_url")
        if not url:
            return
        ref = item.get("path") or item.get("raw_source_ref")
        path = REPO_ROOT / ref if ref else None
        digest = item.get("sha256") or item.get("source_sha256")
        available = path is not None and path.is_file() and digest is not None
        if available and sha256(path) != digest:
            raise ValueError(f"Bibliography digest mismatch: {ref}")
        identity = (url, ref or item.get("source_id"))
        if identity in entries:
            return
        host = urlparse(url).hostname or "local repository"
        publisher = item.get("publisher") or next((v for k, v in PUBLISHERS.items() if host == k or host.endswith("." + k)), host)
        usage = "prior_enrichment_reference"
        key = item.get("source_id", "")
        if group == "China geography and Gulf review":
            usage = "assessment_only" if key.startswith(("aws-", "oracle-", "alibaba-")) else "geography_enrichment"
            if key.startswith(("aws-", "oracle-")):
                usage = "gulf_enrichment_and_status_review"
            if key in {"chindata-ulanqab", "chindata-yichang"} or "gallery" in key:
                usage = "review_only_no_location_admitted"
        if not available:
            usage = "unavailable_no_evidence_admitted"
        elif group == "Gulf network and interconnect enrichment":
            usage = "gulf_enrichment"
        elif group.startswith("Apple TV delivery:"):
            usage = "apple_tv_and_cache_host_review"
            if item.get("result") == "http_error":
                usage = "failed_retrieval_receipt_no_evidence_admitted"
        entry = {"reference_id": "ref-" + hashlib.sha256((url + "|" + str(ref or item.get("source_id"))).encode()).hexdigest()[:16],
            "group": group, "source_id": key or None, "title": title_for(item, path if available else None),
            "publisher": publisher, "publisher_identity_basis": "explicit source metadata or provider domain" if publisher != host else "source hostname; authorship not independently normalized",
            "source_url": url, "retrieved_at": item.get("retrieved_at"),
            "source_published_at": item.get("source_published_at"), "source_updated_at": item.get("source_updated_at"),
            "raw_source_ref": ref if available else None, "sha256": digest if available else None,
            "availability": "retained" if available else "unavailable", "usage": usage,
            "role_and_limits": item.get("role") or item.get("notes") or default_role,
            "capture_method": item.get("capture_method", "retained_source"),
            "error": item.get("error") if not available else None}
        for field in ["download_sha256", "archive_member", "selected_geonames_ids"]:
            if field in item:
                entry[field] = item[field]
        if "geonames" in key:
            entry["license_url"] = "https://creativecommons.org/licenses/by/4.0/"
        entries[identity] = entry

    for catalog, group in [(CATALOG, "China geography and Gulf review"),
                            (REPO_ROOT / "data/raw/apple-tv/catalog.20261019.json", "Apple TV delivery: web, artwork, public previews and cache hosts"),
                            (REPO_ROOT / "data/raw/completion-review/catalog.20261019.json", "Completion review: China, India, Apple, Gulf and Russia"),
                            (REPO_ROOT / "data/raw/gulf-enrichment/catalog.20261019.json", "Gulf network and interconnect enrichment"),
                            (REPO_ROOT / "data/raw/china-enrichment/catalog.20261011.json", "Earlier China enrichment")]:
        for item in read(catalog)["sources"]:
            add(item, group, "Retained prior China source; consult the associated implementation for scope and admission decisions")
    for directory in ["cartography-restoration", "observations", "apnic", "russia", "yandex", "crypto"]:
        for sidecar in sorted((REPO_ROOT / "data/raw" / directory).glob("*.provenance.json")):
            add(read(sidecar), "CDN, India, Apple and Russia references", "Prior enrichment reference; preserve source-specific scope")
    # Include every older source used by the new locality view and Gulf baseline.
    layers = baseline_layers()
    for name, layer in layers.items():
        if name not in CLOUD_LAYERS and not name.startswith(("aws/", "oracle/")):
            continue
        for feature in read(REPO_ROOT / layer["files"]["geojson"]["path"])["features"]:
            row = feature["properties"]
            ref = row["raw_source_ref"]
            sidecar = REPO_ROOT / (ref + ".provenance.json")
            item = read(sidecar) if sidecar.exists() else row
            add(item, "Earlier location inputs", "Original provider declaration used for locality or Gulf comparison; retrieval dates are not refreshed")
    return {"built_at": DATE, "scope": "Sources retained for Apple TV delivery/cache hosts, China geography, Gulf implementation, completion review, and earlier China, India/Apple, CDN and Russia enrichment",
        "date_policy": "Null means no publication/update date established; retrieval, publication and claim-as-of dates are distinct.",
        "rights_note": "Bibliographic inclusion is not a grant of redistribution rights. GeoNames reference coordinates are CC BY 4.0; other source-specific terms remain applicable.",
        "reference_count": len(entries), "references": sorted(entries.values(), key=lambda e: (e["group"], e["publisher"], e["title"], e["raw_source_ref"] or ""))}


def markdown(payload):
    lines = ["# Enrichment bibliography", "", f"Built {DATE}. {payload['reference_count']} retained-source or unavailable-reference entries.", "",
        "The [machine-readable index](../data/references/bibliography.20261019.json) records the full SHA-256, raw path, source dates, publisher, role and admission limits for every entry. Retrieval dates do not establish a current deployment. Failed URLs and held evidence are included explicitly.", "",
        "GeoNames coordinates are locality reference points under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), not infrastructure coordinates. Bibliographic inclusion does not change any source's redistribution terms.", ""]
    group = None
    for entry in payload["references"]:
        if entry["group"] != group:
            group = entry["group"]
            lines.extend(["## " + group, ""])
        title = entry["title"].replace("[", "(").replace("]", ")")
        raw = f"[retained source](../{entry['raw_source_ref']})" if entry["raw_source_ref"] else "unavailable"
        dates = f"retrieved {entry['retrieved_at'] or 'unknown'}"
        if entry["source_published_at"]:
            dates += f"; published {entry['source_published_at']}"
        if entry["source_updated_at"]:
            dates += f"; updated {entry['source_updated_at']}"
        citation = f"[{title}]({entry['source_url']})" if entry["source_url"].startswith(("https://", "http://")) else f"{title} (`{entry['source_url']}`)"
        lines.extend([f"- **{entry['publisher']}** — {citation}. {dates}; {raw}. `{entry['reference_id']}`. {entry['role_and_limits']}", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    result = build()
    write_json(args.output_root / f"data/references/bibliography.{TAG}.json", result)
    doc = args.output_root / f"docs/bibliography.{TAG}.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(markdown(result), encoding="utf-8")
    print(f"Bibliography: {result['reference_count']} source entries")


if __name__ == "__main__":
    main()
