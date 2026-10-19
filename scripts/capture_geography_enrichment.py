#!/usr/bin/env python3
"""Capture the reviewed China/Gulf sources; never overwrite retained evidence."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

from location_common import REPO_ROOT, repo_ref, write_json

DATE, TAG = "2026-10-19", "20261019"
ROOT = REPO_ROOT / "data/raw/geography-enrichment"


def specifications():
    records = []

    def add(key, url, title, publisher, role, published=None, extension="html"):
        records.append(dict(source_id=key, source_url=url, title=title, publisher=publisher,
                            role=role, source_published_at=published, source_updated_at=None,
                            extension=extension))

    base = "https://www.chindatagroup.com"
    add("chindata-directory", base + "/global.html", "Chindata regional directory", "Chindata", "directory traversal")
    for label, number in [("north", 34), ("yangtze", 58), ("greater-bay", 59),
                          ("qingyang", 494), ("zhongwei", 495), ("ulanqab", 517), ("yichang", 522)]:
        add("chindata-" + label, base + f"/portal/article/index/cid/28/id/{number}.html",
            "Chindata regional directory: " + label, "Chindata", "code or named-locality directory evidence")
    for number in [65, 35, 42, 41, 216, 214, 188, 73, 71, 498, 500]:
        add(f"chindata-gallery-{number}", base + f"/global/base/{number}.html",
            f"Chindata code detail gallery {number}", "Chindata", "identity review; no inferred photographic geolocation")
    for number, label, published in [(192, "Sangyuan campus opening", "2020-01-17"),
                                      (194, "Huailai campus development", "2020-02-08"),
                                      (533, "Sangyuan SST system entering service", "2026-07-02")]:
        add(f"chindata-news-{number}", base + f"/media/news/{number}.html", label, "Chindata",
            "named campus locality or dated lifecycle evidence", published)
    add("lingqiu-government-2026", "https://www.lingqiu.gov.cn/lqxrmzfz/zfgzbg/202604/4377a3fe37a042bb9cca483a93d7ac5f.shtml",
        "Lingqiu County 2026 government work report", "Lingqiu County Government", "phase-specific project evidence", "2026-04-01")
    add("alibaba-directory", "https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones",
        "Alibaba Cloud regions and zones", "Alibaba Cloud", "current directory reconciliation; not building coordinates")
    add("geonames-cities15000", "https://download.geonames.org/export/dump/cities15000.zip",
        "GeoNames cities15000 gazetteer", "GeoNames", "locality reference points only", extension="zip")
    add("geonames-cn", "https://download.geonames.org/export/dump/CN.zip",
        "GeoNames China gazetteer", "GeoNames", "county identity review; selected rows retained separately", extension="zip")
    add("geonames-readme", "https://download.geonames.org/export/dump/readme.txt",
        "GeoNames export format and license", "GeoNames", "field definitions, WGS84 and CC BY attribution", extension="txt")
    add("aws-regions", "https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.md",
        "AWS Regions", "Amazon Web Services", "current region identifiers and country scope", extension="md")
    add("aws-availability-zones", "https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.md",
        "AWS Availability Zones", "Amazon Web Services", "stable AZ identifiers; not physical addresses", extension="md")
    add("aws-cloudfront", "https://aws.amazon.com/cloudfront/features/", "Amazon CloudFront features and network",
        "Amazon Web Services", "edge-location coverage reconciliation")
    add("aws-local-zones", "https://aws.amazon.com/about-aws/global-infrastructure/localzones/locations/",
        "AWS Local Zones locations", "Amazon Web Services", "live versus announced Local Zones")
    add("aws-local-zones-guide", "https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html",
        "Available AWS Local Zones", "Amazon Web Services", "itemized Local Zone IDs and parent regions")
    add("aws-direct-connect", "https://aws.amazon.com/directconnect/locations/", "AWS Direct Connect locations",
        "Amazon Web Services", "interconnect sites distinct from cloud region data centers")
    add("aws-uae-launch", "https://aws.amazon.com/blogs/aws/now-open-aws-region-in-the-united-arab-emirates-uae/",
        "Now Open: AWS Region in the United Arab Emirates", "Amazon Web Services", "historical launch and Fujairah edge evidence", "2022-08-29")
    add("aws-saudi-plan", "https://aws.amazon.com/blogs/migration-and-modernization/how-to-plan-your-migration-to-the-aws-region-in-saudi-arabia/",
        "How to plan your migration to the AWS Region in Saudi Arabia", "Amazon Web Services", "planned December 2026 launch; not live as of review", "2026-10-15")
    add("oracle-regions", "https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm",
        "OCI Regions and Availability Domains", "Oracle", "public regions, realms and AD counts")
    add("oracle-sdk-regions", "https://raw.githubusercontent.com/oracle/oci-java-sdk/master/bmc-common/src/main/java/com/oracle/bmc/Region.java",
        "OCI Java SDK region registry", "Oracle", "realm-qualified region identity corroboration; registration is not launch proof", extension="java")
    add("oracle-fastconnect", "https://www.oracle.com/cloud/networking/fastconnect/locations/",
        "Oracle FastConnect locations", "Oracle", "network interconnect sites; not region buildings")
    add("oracle-fastconnect-partners", "https://www.oracle.com/cloud/networking/fastconnect/partners/",
        "Oracle FastConnect partners and locations", "Oracle", "network interconnect location and region associations")
    add("oracle-epm-realms", "https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/tsepm/opc_gen_2_regions.html",
        "EPM Cloud Geographic, Data, and Air-gapped Regions", "Oracle", "product-scoped dedicated realms; not general public availability")
    return records


def fetch(spec):
    item = {k: v for k, v in spec.items() if k != "extension"}
    extension = "tsv" if spec["source_id"] == "geonames-cn" else spec["extension"]
    path = ROOT / f"{spec['source_id']}.{TAG}.{extension}"
    provenance = Path(str(path) + ".provenance.json")
    if path.exists():
        previous = json.loads(provenance.read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != previous["sha256"]:
            raise ValueError(f"Retained digest mismatch: {path}")
        return previous, None
    try:
        request = Request(spec["source_url"], headers={"User-Agent": "cloud-cdn-cache research source capture"})
        with urlopen(request, timeout=45) as response:
            body = response.read()
            if spec["source_id"] == "geonames-cn":
                item["download_sha256"] = hashlib.sha256(body).hexdigest()
                item["download_bytes"] = len(body)
                item["archive_member"] = "CN.txt"
                item["selected_geonames_ids"] = ["1803485", "2036767"]
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    body = b"".join(line for line in archive.read("CN.txt").splitlines(keepends=True)
                                    if line.split(b"\t", 1)[0].decode() in item["selected_geonames_ids"])
                if len(body.splitlines()) != 2:
                    raise ValueError("Missing reviewed county rows in GeoNames China dump")
            item.update(result="retrieved", path=repo_ref(path), bytes=len(body),
                        raw_source_ref=repo_ref(path),
                        sha256=hashlib.sha256(body).hexdigest(), final_url=response.url,
                        content_type=response.headers.get("Content-Type"),
                        http_last_modified=response.headers.get("Last-Modified"))
        item.update(retrieved_at=DATE, capture_method="verbatim_selected_archive_rows" if spec["source_id"] == "geonames-cn" else "http_response")
        return item, body
    except Exception as error:
        item.update(result="unavailable", path=None, sha256=None, retrieved_at=DATE,
                    capture_method="http_response", error=str(error))
        return item, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    selected = [s for s in specifications() if not args.only or s["source_id"] in args.only]
    ROOT.mkdir(parents=True, exist_ok=True)
    catalog = ROOT / f"catalog.{TAG}.json"
    existing = {s["source_id"]: s for s in json.loads(catalog.read_text())["sources"]} if catalog.exists() else {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for item, body in pool.map(fetch, selected):
            if body is not None:
                path = REPO_ROOT / item["path"]
                path.write_bytes(body)
                write_json(Path(str(path) + ".provenance.json"), item)
            existing[item["source_id"]] = item
            print(item["source_id"], item["result"], item.get("bytes", item.get("error")), flush=True)
    write_json(catalog, {"retrieved_at": DATE, "sources": [existing[k] for k in sorted(existing)]})


if __name__ == "__main__":
    main()
