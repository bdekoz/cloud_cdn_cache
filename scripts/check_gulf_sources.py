#!/usr/bin/env python3
"""Compare reviewed Gulf sources with fresh captures; never promote changes automatically."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import ipaddress
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from assess_gulf_coverage import cells
from gulf_enrichment_common import DATE, GULF, TAG, read, source
from location_common import REPO_ROOT, write_json

KEYS = ("aws-regions", "aws-availability-zones", "aws-cloudfront", "aws-local-zones-guide",
        "aws-direct-connect", "aws-saudi-plan", "oracle-regions", "oracle-fastconnect-partners",
        "oracle-epm-realms", "aws-ip-ranges", "aws-geofeed", "oracle-ip-ranges")
GULF_LABEL = re.compile(r"\b(?:UAE|Emirates|Bahrain|Manama|Oman|Muscat|Barka|Saudi|Riyadh|Jeddah|Qatar|Doha|Kuwait|Dubai|Abu Dhabi|Fujairah)\b", re.I)


def semantic_rows(key, body):
    """Compare meaningful table/feed rows, ignoring page scripts and feed timestamps."""
    rows = []
    if key == "aws-ip-ranges":
        value = json.loads(body)
        if not value["prefixes"] or not value["ipv6_prefixes"]:
            raise ValueError("Missing AWS address family")
        for collection, field in [("prefixes", "ip_prefix"), ("ipv6_prefixes", "ipv6_prefix")]:
            for row in value[collection]:
                ipaddress.ip_network(row[field], strict=True)
                if row["region"].startswith("me-"):
                    rows.append([row[field], row["region"], row["service"], row["network_border_group"]])
    elif key == "oracle-ip-ranges":
        value = json.loads(body)
        if not value["regions"] or not value["last_updated_timestamp"]:
            raise ValueError("Missing OCI region feed metadata")
        for region in value["regions"]:
            for row in region["cidrs"] + region.get("ipv6_cidrs", []):
                ipaddress.ip_network(row["cidr"], strict=True)
                if region["region"].startswith("me-"):
                    rows.append([region["region"], row["cidr"], sorted(row["tags"])])
    elif key == "aws-geofeed":
        parsed = 0
        for row in csv.reader(io.StringIO(body.decode("utf-8"))):
            if not row or row[0].startswith("#"):
                continue
            if len(row) != 5:
                raise ValueError("Geofeed field count changed")
            ipaddress.ip_network(row[0], strict=True)
            parsed += 1
            if row[1] in GULF:
                rows.append(row)
        if not parsed:
            raise ValueError("Empty geofeed")
    elif key in {"aws-regions", "aws-availability-zones"}:
        parsed = 0
        for line in body.decode("utf-8").splitlines():
            row = [c.strip() for c in line.strip().strip("|").split("|")]
            if key == "aws-regions" and len(row) >= 4 and re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d+", row[0]):
                int(re.sub(r"[\s*†‡]", "", row[2]))
                parsed += 1
                if GULF_LABEL.search(" ".join(row)):
                    rows.append(row)
            elif key == "aws-availability-zones" and len(row) == 3 and re.fullmatch(r"[a-z0-9]+-az\d+", row[0]):
                parsed += 1
                if row[1].startswith("me-"):
                    rows.append(row)
        if not parsed:
            raise ValueError("AWS Markdown directory shape changed")
    else:
        page = BeautifulSoup(body, "html.parser")
        if key == "aws-cloudfront":
            found = 0
            for paragraph in page.find_all("p"):
                text = " ".join(paragraph.get_text(" ", strip=True).split())
                label, separator, places = text.partition(":")
                if separator and label in {"Bahrain", "Kingdom of Saudi Arabia", "United Arab Emirates", "Oman", "Qatar", "Kuwait"}:
                    found += 1
                    rows.extend([[label, city.strip()] for city in places.split(",")])
            if not found:
                raise ValueError("CloudFront country list missing")
        elif key == "aws-saudi-plan":
            rows = [[" ".join(p.get_text(" ", strip=True).split())] for p in page.find_all("p")
                    if "Saudi Arabia" in p.get_text() and re.search(r"\bregion\b", p.get_text(), re.I)]
            if not rows:
                raise ValueError("Saudi migration guidance text missing")
        else:
            header = {"aws-local-zones-guide": "Local Zone ID", "aws-direct-connect": "AWS Direct Connect Location",
                      "oracle-regions": "Region Identifier", "oracle-fastconnect-partners": "Data Center Provider",
                      "oracle-epm-realms": "Geographical Region (Realm)"}[key]
            width = {"aws-local-zones-guide": 7, "aws-direct-connect": 2, "oracle-regions": 6,
                     "oracle-fastconnect-partners": 4, "oracle-epm-realms": 4}[key]
            tables = [t for t in page.find_all("table") if header in cells(t.find("tr"))]
            if not tables:
                raise ValueError(f"Directory header missing: {header}")
            parsed = 0
            for table in tables:
                realm = ""
                for tr in table.find_all("tr")[1:]:
                    row = cells(tr)
                    if len(row) != width:
                        raise ValueError(f"Directory width changed for {key}: {row}")
                    parsed += 1
                    if key == "oracle-epm-realms":
                        realm = row[0] or realm
                        row = [realm, *row[1:]]
                        if row[2].startswith("me-"):
                            rows.append(row)
                    elif GULF_LABEL.search(" ".join(row)):
                        rows.append(row)
            if not parsed:
                raise ValueError("Empty directory tables")
    result = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows]
    if len(result) != len(set(result)):
        raise ValueError(f"Duplicate semantic row in {key}")
    return sorted(result)


def compare_rows(before, after):
    old, new = set(before), set(after)
    return {"baseline_row_count": len(old), "current_row_count": len(new),
            "added_rows": [json.loads(r) for r in sorted(new - old)],
            "removed_rows": [json.loads(r) for r in sorted(old - new)], "semantic_changed": old != new}


def check_one(key, output_dir, offline, as_of):
    item = source(key)
    before = (REPO_ROOT / item["path"]).read_bytes()
    result = {"source_id": key, "source_url": item["source_url"], "baseline_raw_source_ref": item["path"],
        "baseline_sha256": item["sha256"], "baseline_retrieved_at": item["retrieved_at"],
        "baseline_age_days": (as_of - date.fromisoformat(item["retrieved_at"])).days,
        "source_published_at": item.get("source_published_at"), "checked_at": as_of.isoformat()}
    try:
        old = semantic_rows(key, before)
        if offline:
            body, capture = before, None
        else:
            request = Request(item["source_url"], headers={"User-Agent": "cloud-cdn-cache weekly source review"})
            with urlopen(request, timeout=45) as response:
                body = response.read(20 * 1024 * 1024 + 1)
                if len(body) > 20 * 1024 * 1024:
                    raise ValueError("Source exceeds 20 MiB capture limit")
                capture = {"source_url": item["source_url"], "final_url": response.url,
                    "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "http_last_modified": response.headers.get("Last-Modified"),
                    "content_type": response.headers.get("Content-Type"), "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(), "capture_method": "http_response"}
            target = output_dir / "raw" / (key + ".bin")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            capture["artifact_path"] = "raw/" + target.name
            write_json(target.with_suffix(".provenance.json"), capture)
        result.update(current_sha256=hashlib.sha256(body).hexdigest(), capture=capture)
        result.update(compare_rows(old, semantic_rows(key, body)))
        result["raw_changed"] = result["current_sha256"] != result["baseline_sha256"]
        result["status"] = "review_required" if result["semantic_changed"] else "unchanged_scope"
        if key in {"aws-ip-ranges", "oracle-ip-ranges"}:
            payload = json.loads(body)
            result["current_feed_timestamp"] = payload.get("createDate", payload.get("last_updated_timestamp"))
            result["current_feed_age_days"] = (as_of - date.fromisoformat(result["current_feed_timestamp"][:10])).days
    except Exception as error:
        result.update(status="capture_or_parser_error", error=str(error))
    return result


def markdown(report):
    lines = ["# Gulf source review", "", f"Checked {report['checked_at']} ({report['mode']}). {report['review_required_count']} changed sources; {report['error_count']} errors.", "",
        "Changes require evidence review. This job does not change canonical records or establish a region launch.", "",
        "| Source | Status | Previous rows | Current rows | Baseline age (days) |", "| --- | --- | ---: | ---: | ---: |"]
    for row in report["sources"]:
        lines.append(f"| {row['source_id']} | {row['status']} | {row.get('baseline_row_count', '—')} | {row.get('current_row_count', '—')} | {row['baseline_age_days']} |")
    lines += ["", f"Saudi launch review due: {report['saudi_launch_watch']['review_due']}; overdue: {report['saudi_launch_watch']['review_overdue']}.",
              "The JSON report contains added/removed rows and errors. Fresh HTTP bodies and capture metadata accompany live runs.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Validate retained baselines without any network access")
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be empty so previous captures cannot be overwritten")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(lambda k: check_one(k, args.output_dir, args.offline, args.as_of), KEYS))
    implementation = read(REPO_ROOT / f"data/gulf/enrichment-implementation.{TAG}.json")
    watch = implementation["saudi_launch_watch"]
    report = {"checked_at": args.as_of.isoformat(), "mode": "retained_baseline_validation" if args.offline else "live_comparison",
        "review_required_count": sum(s["status"] == "review_required" for s in sources),
        "error_count": sum(s["status"] == "capture_or_parser_error" for s in sources), "sources": sources,
        "canonical_updates_applied": False, "review_baseline_date": DATE,
        "last_reviewed_coverage": {k: implementation[k] for k in ["reviewed_canonical_count", "current_directory_reconfirmed_count",
            "historical_unconfirmed_count", "geometry_null_count", "locality_count", "locality_held_count"]},
        "saudi_launch_watch": {**watch, "review_overdue": args.as_of >= date.fromisoformat(watch["review_due"]),
                               "status_not_reassessed_by_this_job": True}}
    write_json(args.output_dir / "report.json", report)
    (args.output_dir / "summary.md").write_text(markdown(report), encoding="utf-8")
    print(f"{len(sources)} sources: {report['review_required_count']} changes, {report['error_count']} errors; report {args.output_dir / 'report.json'}")
    raise SystemExit(2 if report["error_count"] else 1 if report["review_required_count"] or (not args.offline and report["saudi_launch_watch"]["review_overdue"]) else 0)


if __name__ == "__main__":
    main()
