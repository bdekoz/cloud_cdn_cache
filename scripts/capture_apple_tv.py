#!/usr/bin/env python3
"""Retain public Apple TV delivery evidence; never request paid media or keys."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from location_common import REPO_ROOT, repo_ref, sha256, write_json

DATE, TAG = "2026-10-19", "20261019"
ROOT = REPO_ROOT / "data/raw/apple-tv"
CATALOG = ROOT / f"catalog.{TAG}.json"


def documents():
    return [dict(source_id=k, source_url=u, title=t, publisher=p, extension="html",
                 role=role, method="GET", source_published_at=None, source_updated_at=None)
            for k, u, t, p, role in [
        ("tv-home", "https://tv.apple.com/", "Apple TV public web application", "Apple", "Discover exact web, artwork and public preview resources. Storefront and marketing geography are not infrastructure locations."),
        ("tv-ted-lasso", "https://tv.apple.com/us/show/ted-lasso/umc.cmc.vtoh0mn0xn7t3c643xqonfzy", "Apple TV Ted Lasso public show page", "Apple", "Public show page and preview metadata; no subscriber playback or DRM key requests."),
        ("apple-enterprise-network", "https://support.apple.com/en-us/101555", "Use Apple products on enterprise networks", "Apple", "General service domain guidance, not a TV deployment inventory."),
        ("apple-cdn-engineer", "https://jobs.apple.com/en-us/details/200672206-0836/cdn-solutions-engineer", "Apple CDN Solutions Engineer role", "Apple", "Provider description of media delivery architecture. Platform count is not TV CDN market share or a PoP count."),
        ("apple-aec-program", "https://cache.edge.apple.com/", "Apple Edge Cache program", "Apple", "Apple-managed ISP cache program; no TV-specific deployment inventory."),
    ]]


def capture(spec):
    path = ROOT / f"{spec['source_id']}.{TAG}.{spec['extension']}"
    sidecar = Path(str(path) + ".provenance.json")
    if path.exists():
        item = json.loads(sidecar.read_text())
        if sha256(path) != item["sha256"] or item["source_url"] != spec["source_url"]:
            raise ValueError(f"Retained source changed: {path}")
        return item
    item = {k: v for k, v in spec.items() if k != "extension"}
    item.update(retrieved_at=DATE, captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    request = Request(spec["source_url"], method=spec.get("method", "GET"),
                      headers={"User-Agent": "cloud-cdn-cache public delivery evidence review", "Accept-Encoding": "identity"})
    try:
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            # This is the peer of this HTTP connection, not a separately resolved IP.
            try:
                peer_address = response.fp.raw._sock.getpeername()[0]
            except (AttributeError, OSError):
                peer_address = None
            body = response.read(8 * 1024 * 1024 + 1)
            if len(body) > 8 * 1024 * 1024:
                raise ValueError("Source exceeds 8 MiB capture limit")
            # Cookies are unnecessary for reproducibility or delivery attribution.
            headers = {k.lower(): v for k, v in response.headers.items() if k.lower() not in {"set-cookie", "set-cookie2"}}
            item.update(http_status=response.status, final_url=response.url, response_headers=headers,
                        content_type=response.headers.get("Content-Type"), content_encoding=response.headers.get("Content-Encoding"),
                        http_peer_address=peer_address, measurement_vantage_country_code=None)
        if spec.get("method") == "HEAD":
            body = (json.dumps({"url": spec["source_url"], "observed_at": item["captured_at"],
                                "status": item["http_status"], "headers": headers}, indent=2) + "\n").encode()
        item.update(result="retrieved" if 200 <= item["http_status"] < 300 else "http_error",
                    path=repo_ref(path), raw_source_ref=repo_ref(path), sha256=hashlib.sha256(body).hexdigest(),
                    bytes=len(body), capture_method="http_headers" if spec.get("method") == "HEAD" else "http_response")
        path.write_bytes(body)
        write_json(sidecar, item)
    except (OSError, ValueError) as exc:
        item.update(result="unavailable", error=f"{type(exc).__name__}: {exc}")
    return item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specifications", type=Path, help="Explicit public resource capture specifications; default: Apple documents")
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    specs = json.loads(args.specifications.read_text()) if args.specifications else documents()
    existing = {s["source_id"]: s for s in json.loads(CATALOG.read_text())["sources"]} if CATALOG.exists() else {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for item in pool.map(capture, specs):
            existing[item["source_id"]] = item
            print(item["source_id"], item["result"], item.get("bytes", item.get("error")), flush=True)
    write_json(CATALOG, {"retrieved_at": DATE, "sources": [existing[k] for k in sorted(existing)]})


if __name__ == "__main__":
    main()
