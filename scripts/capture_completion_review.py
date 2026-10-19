#!/usr/bin/env python3
"""Capture follow-up evidence once, retaining exact bytes and unsuccessful leads."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from location_common import REPO_ROOT, repo_ref, sha256, write_json

DATE, TAG = "2026-10-19", "20261019"
ROOT = REPO_ROOT / "data/raw/completion-review"


def specifications():
    rows = [
        ("grinex-identity-review", "https://grinex.io/", "Grinex candidate domain identity review", "Unverified candidate domain", "html", "Candidate endpoint only; retrieval or DNS availability does not establish exchange identity or origin hosting."),
        ("peeringdb-mc1", "https://www.peeringdb.com/api/fac?name__icontains=Equinix%20MC1", "PeeringDB Equinix MC1 facility lookup", "PeeringDB / facility registrant", "json", "Public registry lookup; an exact operator-code match is required for address admission."),
        ("jio-cdn-datasheet", "https://myjiostatic.cdn.jio.com/cms/assets/enterprise-cloud/resources/JioCloud_NetworkandConnectivity_ContentDeliveryNetwork(CDN)_Datasheet.pdf", "Jio Cloud CDN datasheet", "Jio", "pdf", "Public datasheet linked by the retained Jio CDN page; service features alone do not establish deployment cities."),
        ("jio-cdn-brochure", "https://myjiostatic.cdn.jio.com/cms/assets/enterprise-cloud/resources/JioCloud_NetworkandConnectivity_ContentDeliveryNetwork(CDN)_Brochure.pdf", "Jio Cloud CDN brochure", "Jio", "pdf", "Public brochure linked by the retained Jio CDN page; itemized service-specific deployment evidence is required for locations."),
        ("cst-latency-data", "https://www.cst.gov.sa/-/media/cst-website-app/data/media/cloud-latency-2026-interactive-report/cloud-latency-2026/cloud-script.js?v=20260930a", "CST cloud latency dashboard data and methodology, first half 2026", "Communications, Space and Technology Commission", "js", "Public script linked by the retained regulator dashboard; parse data without executing JavaScript. Latency is a country-wide weighted access measurement, not an exact facility location."),
        ("cst-latency-dashboard", "https://www.cst.gov.sa/en/knowledge-center/reports/cloud-latency-report-26-dashboard", "CST cloud access latency dashboard, first half 2026", "Communications, Space and Technology Commission", "html", "Public passive measurement report; country-wide weighted access latency is not a facility locator or an October service-health observation."),
        ("vnet-q2-2026", "https://ir.vnet.com/news-releases/news-release-details/vnet-reports-unaudited-second-quarter-2026-financial-results", "VNET second quarter 2026 financial results", "VNET", "html", "Explicit campus-code activity at June 30, 2026; aggregate MW and code abbreviations do not identify addresses."),
        ("peeringdb-dx1", "https://www.peeringdb.com/api/fac/1355", "PeeringDB Equinix DX1 facility registration", "PeeringDB / facility registrant", "json", "Self-reported facility address tied to explicit DX1 code; independent of cloud-provider directories but not a surveyed building location."),
        ("cloudru-third-zone", "https://cloud.ru/blog/cloud-ru-otkryl-tretyu-zonu-dostupnosti-i-attestoval-platformu-cloud-ru-evolution", "Cloud.ru Evolution third availability zone announcement", "Cloud.ru", "html", "Review for explicit Evolution parent-region identity; an AZ definition is not a named region."),
        ("gds-portfolio-presentation", "https://investors.gds-services.com/static-files/46fa60b6-5dc1-4616-89e7-dc8c38658eed", "GDS data-center portfolio presentation", "GDS", "pdf", "Investor disclosure candidate for itemized campus codes; reporting period and grouped labels must be retained."),
        ("equinix-sustainability-2025", "https://delivery-p112322-e1154416.adobeaemcloud.com/adobe/assets/deliver/urn:aaid:aem:e277427d-df16-4720-b4cd-4a30adbefa26/QRG_IBX-Sustainability-Quick-Reference.pdf", "Equinix IBX Sustainability Quick Reference Guide, FY2025", "Equinix", "pdf", "Current official document-center link replacing the unavailable FY2024 URL; site codes and addresses, not cloud-region buildings."),
        ("chindata-acquisition-legal", "https://static.cninfo.com.cn/finalpage/2026-07-21/1225433429.PDF", "Chindata acquisition legal opinion, June 2026, disclosed July 21", "Jiayuan Law / Guangdong HEC Technology", "pdf", "Project, legal-entity and property-title evidence; not a public H/W-code crosswalk or proof of current operation."),
        ("chindata-acquisition-supplement", "https://static.cninfo.com.cn/finalpage/2026-09-23/1225577150.PDF", "Chindata acquisition valuation inquiry reply, September 2026", "Chongqing Kunyuan Asset Appraisal / Guangdong HEC Technology", "pdf", "Appraiser's exchange-inquiry reply, including project-compliance disclosures; pending approvals must not be represented as operational status."),
        ("equinix-sustainability-addresses", "https://sustainability.equinix.com/wp-content/uploads/2025/04/QRG_IBX-Sustainability-Quick-Reference.pdf", "Equinix IBX sustainability quick reference, FY2024", "Equinix", "pdf", "Operator facility codes and addresses; no cloud-region building inference."),
        ("equinix-ad1-specification", "https://www.equinix.com.br/content/dam/eqxcorp/en_us/documents/resources/ibx-tech-specs/ibx_ad1_en.pdf", "Equinix AD1 specification", "Equinix", "pdf", "Abu Dhabi operator facility candidate; not an established Oracle endpoint join."),
        ("eand-smarthub", "https://www.eand.ae/smarthub.html", "SmartHub data centres", "e& UAE", "html", "Operator declarations; explicit site identity is required before joining a cloud endpoint."),
        ("cst-latency-report", "https://www.cst.gov.sa/en/knowledge-center/reports/cloud-services-latency-performance-report-2026", "Cloud services latency performance report 2026 landing page", "Communications, Space and Technology Commission", "html", "Report-discovery lead; a landing page alone supplies no latency measurements."),
        ("tata-cdn-map-landing", "https://www.tatacommunications.com/resourcehub/cdn/cdn-pop-map", "Tata Communications CDN PoP map landing page", "Tata Communications", "html", "Landing-page date is not the linked map's publication or deployment date."),
        ("tata-cdn-map", "https://www.tatacommunications.com/hubfs/TaCO-2024/cdn/doc/cdn-poplist-map.pdf", "Tata Communications CDN PoP map", "Tata Communications", "pdf", "Historical city declarations, active versus planned as depicted; no current site count or building coordinates."),
        ("jio-cdn-product", "https://www.jio.com/enterprisecloud/services/ai-cloud/network/content-delivery-network/", "Jio Cloud Content Delivery Network", "Jio", "html", "Product and deployment-list discovery; aggregate coverage is not a site inventory."),
        ("apple-aec-program", "https://cache.edge.apple.com/", "Apple Edge Cache program", "Apple", "html", "Program eligibility does not identify deployed caches or attribute ASN-labelled measurements."),
        ("huawei-chinese-global", "https://www.huaweicloud.com/intl/zh-cn/global/", "Huawei Cloud global infrastructure, Chinese edition", "Huawei Cloud", "html", "Explicit city-to-region tooltip evidence; no building location inference."),
        ("tencent-cls-regions", "https://www.tencentcloud.com/document/product/614/18940", "Tencent Cloud CLS available regions", "Tencent Cloud", "html", "Product-scoped region labels and identifiers; no facility coordinates."),
        ("unicom-redis-regions", "https://support.cucloud.cn/document/127/580/501.html?arcid=759&id=501", "Unicom Cloud Redis region documentation", "China Unicom Cloud", "html", "Product-specific regional availability; not necessarily a public-cloud region directory."),
        ("yandex-incident-review", "https://yandex.ru/company/news/09-10-2026-01", "Yandex data-centre incident update, rechecked", "Yandex", "html", "The page's last update date controls the incident claim; a later retrieval does not prove recovery."),
    ]
    return [dict(source_id=k, source_url=u, title=t, publisher=p, extension=e, role=r,
                 source_published_at=None, source_updated_at=None) for k, u, t, p, e, r in rows]


def fetch(spec):
    path = ROOT / f"{spec['source_id']}.{TAG}.{spec['extension']}"
    sidecar = Path(str(path) + ".provenance.json")
    if path.exists():
        item = json.loads(sidecar.read_text())
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Retained source changed: {path}")
        return item, None
    item = {k: v for k, v in spec.items() if k != "extension"}
    item.update(retrieved_at=DATE, captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        with urlopen(Request(spec["source_url"], headers={"User-Agent": "cloud-cdn-cache evidence review"}), timeout=45) as response:
            body = response.read(32 * 1024 * 1024 + 1)
            if len(body) > 32 * 1024 * 1024:
                raise ValueError("Source exceeds 32 MiB capture limit")
            item.update(final_url=response.url, content_type=response.headers.get("Content-Type"),
                        content_encoding=response.headers.get("Content-Encoding"),
                        http_last_modified=response.headers.get("Last-Modified"))
        item.update(result="retrieved", path=repo_ref(path), raw_source_ref=repo_ref(path),
                    sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), capture_method="http_response")
        return item, body
    except (OSError, ValueError) as exc:
        item.update(result="unavailable", error=f"{type(exc).__name__}: {exc}")
        return item, None


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
            print(item["source_id"], item["result"], item.get("bytes", item.get("error")), flush=True)
    write_json(catalog, {"retrieved_at": DATE, "sources": [existing[k] for k in sorted(existing)]})


if __name__ == "__main__":
    main()
