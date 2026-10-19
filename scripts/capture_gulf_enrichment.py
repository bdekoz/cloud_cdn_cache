#!/usr/bin/env python3
"""Retain public Gulf network and interconnect evidence without replacing snapshots."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from location_common import REPO_ROOT, repo_ref, sha256, write_json

DATE, TAG = "2026-10-19", "20261019"
ROOT = REPO_ROOT / "data/raw/gulf-enrichment"


def specifications():
    rows = [
        ("aws-ip-ranges", "https://ip-ranges.amazonaws.com/ip-ranges.json", "AWS public IP ranges", "Amazon Web Services", "json"),
        ("aws-geofeed", "https://ip-ranges.amazonaws.com/geo-ip-feed.csv", "AWS IP geolocation feed", "Amazon Web Services", "csv"),
        ("aws-ip-documentation", "https://docs.aws.amazon.com/vpc/latest/userguide/aws-ip-ranges.html", "AWS IP address ranges and geolocation scope", "Amazon Web Services", "html"),
        ("oracle-ip-ranges", "https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json", "OCI public IP ranges", "Oracle", "json"),
        ("oracle-ip-documentation", "https://docs.oracle.com/en-us/iaas/Content/General/Concepts/addressranges.htm", "OCI IP address ranges and service tags", "Oracle", "html"),
        ("equinix-dx1", "https://www.equinix.com/data-centers/europe-colocation/united-arab-emirates-colocation/dubai-data-centers/dx1", "Equinix DX1 Dubai", "Equinix", "html"),
        ("equinix-mc1", "https://www.equinix.com/data-centers/europe-colocation/oman-colocation/muscat-data-centers/mc1", "Equinix MC1 Muscat, Barka", "Equinix", "html"),
    ]
    return [dict(source_id=k, source_url=u, title=t, publisher=p, extension=e,
                 role="Gulf implementation evidence", source_published_at=None, source_updated_at=None)
            for k, u, t, p, e in rows]


def fetch(spec):
    path = ROOT / f"{spec['source_id']}.{TAG}.{spec['extension']}"
    sidecar = Path(str(path) + ".provenance.json")
    if path.exists():
        previous = json.loads(sidecar.read_text())
        if sha256(path) != previous["sha256"]:
            raise ValueError(f"Changed retained source: {path}")
        return previous, None
    item = {k: v for k, v in spec.items() if k != "extension"}
    request = Request(spec["source_url"], headers={"User-Agent": "cloud-cdn-cache source capture"})
    with urlopen(request, timeout=45) as response:
        body = response.read()
        item.update(final_url=response.url, content_type=response.headers.get("Content-Type"),
                    http_last_modified=response.headers.get("Last-Modified"))
    import hashlib
    if spec["source_id"] == "aws-ip-ranges":
        item["source_published_at"] = json.loads(body)["createDate"][:10]
    elif spec["source_id"] == "oracle-ip-ranges":
        item["source_updated_at"] = json.loads(body)["last_updated_timestamp"][:10]
    item.update(result="retrieved", path=repo_ref(path), raw_source_ref=repo_ref(path),
                sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), retrieved_at=DATE,
                captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), capture_method="http_response")
    return item, body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    catalog = ROOT / f"catalog.{TAG}.json"
    existing = {s["source_id"]: s for s in json.loads(catalog.read_text())["sources"]} if catalog.exists() else {}
    selected = [s for s in specifications() if not args.only or s["source_id"] in args.only]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for item, body in pool.map(fetch, selected):
            if body is not None:
                path = REPO_ROOT / item["path"]
                path.write_bytes(body)
                write_json(Path(str(path) + ".provenance.json"), item)
            existing[item["source_id"]] = item
            print(item["source_id"], item["bytes"], flush=True)
    write_json(catalog, {"retrieved_at": DATE, "sources": [existing[k] for k in sorted(existing)]})


if __name__ == "__main__":
    main()
