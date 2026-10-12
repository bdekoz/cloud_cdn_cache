#!/usr/bin/env python3
"""Serialize the reviewed Russian Federation inventory and Yandex image assessment."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from location_common import REPO_ROOT, canonical_record, repo_ref, sha256, write_json, write_layer, write_provenance

DATE = "2026-10-11"
TAG = "20261011"
POST_URL = "https://x.com/CrimeanVoyager/status/2109158415402479630"
SOURCES = {
    "iso": ("yandex/iso-27001", "pdf", "https://storage.yandexcloud.net/yc-compliance/certificates-2025/ISO/INT/ISO-27001-01-2025-EN.pdf", "2025-10-23"),
    "pci": ("yandex/pci-dss-2023", "pdf", "https://storage.yandexcloud.net/yc-compliance/certificates/20230921_Yandex_DC_AOC.pdf", "2023-09-28"),
    "status": ("yandex/provider-status", "html", "https://yandex.ru/company/news/09-10-2026-01", "2026-10-09"),
    "post": ("yandex/x-post", "json", "https://cdn.syndication.twimg.com/tweet-result?id=2109158415402479630&lang=en&token=0", DATE),
    "image": ("yandex/x-post-image", "jpg", "https://pbs.twimg.com/media/HUU8ZWdXsAAL2ny.jpg?name=orig", DATE),
    "selectel": ("russia/selectel-locations", "html", "https://docs.selectel.ru/infrastructure/locations/", "2026-10-05"),
    "ixcellerate": ("russia/ixcellerate-scalability", "html", "https://ixcellerate.ru/why-ixcellerate/scalability/", None),
    "advanced": ("russia/cloudru-advanced-zones", "html", "https://cloud.ru/docs/advanced/overview/az-and-endpoints", None),
    "evolution": ("russia/cloudru-evolution-vm", "html", "https://cloud.ru/docs/virtual-machines/ug/topics/concepts__virtual-machines", None),
    "cloudflare": ("russia/cloudflare-components", "json", "https://www.cloudflarestatus.com/api/v2/components.json", None),
    "cachefly": ("russia/cachefly-network", "html", "https://www.cachefly.com/network-map/", None),
    "mws": ("russia/mws-cloud-platform", "html", "https://mws.ru/cloud-platform-for-business/", None),
}


def raw_path(key: str) -> Path:
    stem, suffix, _, _ = SOURCES[key]
    return REPO_ROOT / f"data/raw/{stem}.{TAG}.{suffix}"


def evidence(key: str) -> dict:
    return {
        "raw_source_ref": repo_ref(raw_path(key)), "source_sha256": sha256(raw_path(key)),
        "source_url": SOURCES[key][2], "source_published_at": SOURCES[key][3], "retrieved_at": DATE,
    }


def html_text(key: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(raw_path(key).read_bytes(), "html.parser").get_text(" ", strip=True))


def pdf_text(key: str) -> str:
    return subprocess.run(["pdftotext", "-layout", str(raw_path(key)), "-"], check=True, capture_output=True, text=True).stdout


def yandex_records() -> list[dict]:
    pci = pdf_text("pci")
    pci_scope = pci.split("Part 2d. In-Scope Locations/Facilities", 1)[1].split("Part 2e.", 1)[0]
    assert re.search(r"Data centers\s+5\s+Ivanteevka", pci_scope), "Expected the five-location PCI facility scope"
    iso = pdf_text("iso").split("following colocation Data Centers:", 1)[1]
    status = html_text("status")
    assert "September 28, 2023" in pci and "Vienna, 2025-10-23" in iso
    assert "11.10.2026" in status and "полностью остановлена" in status and "Часть инфраструктуры вышла из строя" in status
    localities = [
        ("Kaluga", "kaluga", "Kaluga Oblast", "iso", "partially_disrupted", 1),
        ("Vladimir", "vladimir", "Vladimir Oblast", "iso", "temporarily_stopped", 2),
        ("Sasovo", "sasovo", "Ryazan Oblast", "iso", "temporarily_stopped", 3),
        ("Mytishchi", "mytishchi", "Moscow Oblast", "iso", None, 4),
        ("Ivanteevka", "ivanteevka", "Moscow Oblast", "pci", None, 5),
    ]
    rows = []
    for city, identifier, subdivision, key, operational_report, card in localities:
        assert city in pci_scope, city
        if key == "iso":
            assert city in iso, city
        properties = {
            "representation": "certificate_named_data_center_locality",
            "identity_basis": "provider_hosted_certification_scope",
            "identity_source_date": SOURCES[key][3],
            "current_operational_status_verified": False,
            "capacity_mw": None,
            "image_card_number": card,
            "image_claim_review_ref": f"data/yandex/image-claim-review.{TAG}.json",
            "pci_scope_evidence": evidence("pci"),
            "historical_identity_only": key == "pci",
        }
        if operational_report:
            properties["provider_operational_report"] = {
                **evidence("status"), "provider_updated_at": DATE, "status": operational_report,
                "semantics": "time_bound_provider_statement_not_permanent_retirement",
            }
        rows.append(canonical_record(
            schema_version="1.2.0", record_id=f"yandex:data_center:{identifier}", aliases=[],
            provider="Yandex", service="yandex_data_centers", entity_type="data_center",
            parent_record_id=None, jurisdiction_scope="other", access_status="not_applicable", service_scope=["colocation"],
            source_collection="yandex_provider_hosted_certification_scope", source_record_id=None,
            name=f"Yandex {city}", site_code=None, lifecycle_status="unknown", source_scope="provider_declared",
            city=city, metro=None, subdivision=subdivision, country="Russia", country_code="RU",
            latitude=None, longitude=None, location_precision="unknown", coordinate_method="unknown", coordinate_crs=None,
            source_url=SOURCES[key][2], raw_source_ref=repo_ref(raw_path(key)), source_sha256=sha256(raw_path(key)),
            source_published_at=SOURCES[key][3], retrieved_at=DATE, first_seen=DATE, last_seen=DATE,
            confidence="medium", properties=properties,
        ))
    return rows


def image_review() -> dict:
    post = json.loads(raw_path("post").read_text())
    assert post["id_str"] == "2109158415402479630" and post["created_at"].startswith(DATE)
    assert len(post["photos"]) == 1 and post["photos"][0]["url"].endswith("HUU8ZWdXsAAL2ny.jpg")
    names = ["Kaluga", "Vladimir (Energetik)", "Sasovo (Ryazan region)", "Mytishchi", "Ivanteevka", "Moscow region facility", "additional site", "cloud zone facility", "backup / regional center"]
    ids = ["kaluga", "vladimir", "sasovo", "mytishchi", "ivanteevka"]
    capacities = [63, 63, None, 52, 45, 80, 35, 60, 40]
    return {
        "retrieved_at": DATE, "post_url": POST_URL, "source_image": evidence("image"), "source_post": evidence("post"),
        "extraction_method": "human_visual_review_of_original_image; reviewed_claims_not_provider_inventory",
        "image_card_count": 9, "named_identities_corroborated": 5, "unnamed_cards_not_normalized": 4,
        "capacity_claims_verified": 0, "facility_photos_authenticated": False,
        "issues": [
            "Vladimir subtitle repeats Kaluga's Grabtsevo label and 63 MW figure; not accepted as Vladimir metadata.",
            "Similar or repeated building illustrations do not establish separate photographed facilities or imagery provenance.",
            "Four unnamed cards cannot establish distinct facility identity, ownership, locality, or lifecycle.",
            "Image annotations do not establish full destruction, retirement, or complete operating status.",
        ],
        "cards": [
            {"card_number": index + 1, "image_label": name, "image_capacity_claim_mw": capacities[index],
             "image_capacity_is_approximate": capacities[index] is not None,
             "capacity_verification": "unverified" if capacities[index] is not None else "not_stated",
             "matched_record_id": f"yandex:data_center:{ids[index]}" if index < 5 else None,
             "identity_review": "corroborated_in_provider_hosted_certification" if index < 5 else "insufficient_identity_not_normalized"}
            for index, name in enumerate(names)
        ],
    }


def provider_review() -> list[dict]:
    assert "26 пулов" in html_text("selectel")
    tables = BeautifulSoup(raw_path("selectel").read_bytes(), "html.parser").find_all("table")
    assert [len(set(re.findall(r"Зона доступности (\d+)", table.get_text(" ", strip=True)))) for table in tables[:3]] == [2, 4, 1]
    assert all(code in html_text("ixcellerate") for code in ("MOS1", "MOS2", "MOS3", "MOS4", "MOS5", "MOS7", "MOS11", "MOS12"))
    advanced = html_text("advanced")
    evolution = html_text("evolution")
    assert all(code in advanced for code in ("ru-moscow-1a", "ru-moscow-1b", "ru-moscow-1c", "ru-moscow-1e"))
    assert all(code in evolution for code in ("ru.AZ-1", "ru.AZ-2", "ru.AZ-3"))
    return [
        {"provider": "Yandex", "class": "owned_data_centers", "result": "five_named_certification_localities_normalized", "sources": [evidence("iso"), evidence("pci"), evidence("status")], "limit": "Four names appear in 2025 ISO scope; Ivanteevka has 2023 evidence only. Not an exhaustive current operating inventory."},
        {"provider": "Selectel", "class": "cloud_and_data_center_groups", "result": "itemized_hierarchy_ready_for_connector", "sources": [evidence("selectel")], "russian_regions": ["Saint Petersburg", "Moscow", "Novosibirsk"], "russian_availability_zone_count": 7, "global_claim": {"countries": 4, "regions": 6, "availability_zones": 11, "pools": 26}, "limit": "Three Russian regions have 2/4/1 zones. Groups, partner sites, pools and segments are not individual owned facilities; global totals are not Russia totals."},
        {"provider": "Cloud.ru Advanced", "class": "product_scoped_cloud", "result": "stable_region_zone_ids_ready_for_connector", "sources": [evidence("advanced")], "region_id": "ru-moscow-1", "zone_ids": ["ru-moscow-1a", "ru-moscow-1b", "ru-moscow-1c", "ru-moscow-1e"], "limit": "Advanced is separate from Evolution; endpoint names do not identify owned buildings."},
        {"provider": "Cloud.ru Evolution", "class": "product_scoped_cloud", "result": "stable_zone_uuids_ready_for_connector", "sources": [evidence("evolution")], "zone_names": ["ru.AZ-1", "ru.AZ-2", "ru.AZ-3"], "limit": "Preserve published UUIDs and product scope; do not assume correspondence with Advanced zones."},
        {"provider": "IXcellerate", "class": "colocation", "result": "itemized_lifecycle_ready_for_connector", "sources": [evidence("ixcellerate")], "operating_site_codes": ["MOS1", "MOS2", "MOS3", "MOS4", "MOS5"], "development_or_planning_codes": ["MOS6", "MOS7", "MOS8", "MOS11", "MOS12"], "limit": "MOS6 design, MOS7 preparing to launch and MOS8 future plans remain distinct; MOS11 preparing launch and MOS12 campus plan do not prove operational status. Campus capacity is not a building count."},
        {"provider": "MTS Web Services / MWS", "class": "cloud_and_colocation", "result": "provider_confirmed_complete_site_directory_missing", "sources": [evidence("mws")], "limit": "A product page cannot establish an exhaustive stable site/zone directory or an owned-versus-partner split."},
        {"provider": "VK Cloud", "class": "cloud", "result": "documentation_source_discovered_not_normalized", "source_url": "https://github.com/vk-cs/docs-public", "limit": "Resolve exact Russian zone identifiers from the provider's documentation; keep Kazakhstan separate and do not infer facility ownership."},
        {"provider": "Rostelecom-DC / DataLine", "class": "colocation_and_cloud", "result": "source_access_gap", "source_url": "https://rt-dc.ru/", "retrieved_at": DATE, "access_result": "HTTP 403 in web reader", "limit": "No guessed facility rows; resolve current parent/subsidiary and campus/building identities before counting."},
        {"provider": "3data", "class": "colocation_and_cloud", "result": "provider_service_verified_directory_capture_gap", "source_url": "https://3data.ru/services/colocation", "retrieved_at": DATE, "access_result": "web reader succeeded; raw snapshot fetch returned HTTP 403", "limit": "Named directory cards and ownership/partner relationships remain to be normalized. No rows inferred from marketing aggregates."},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    root = args.output_root
    for key, (_, suffix, url, published) in SOURCES.items():
        write_provenance(raw_path(key), source_url=url, retrieved_at=DATE,
                         source_published_at=published, media_type={"pdf": "application/pdf", "html": "text/html", "json": "application/json", "jpg": "image/jpeg"}[suffix],
                         notes="Retained public evidence. Certification scope and social-image claims are not exhaustive current operating inventories. Source-specific redistribution terms apply.")
    rows = yandex_records()
    write_json(root / f"data/yandex/image-claim-review.{TAG}.json", image_review())
    report = write_layer(records=rows, output_dir=root / "data/yandex", layer_name="data-centers", retrieved_at=DATE,
                        source_url=SOURCES["iso"][2], raw_path=raw_path("iso"), parser_name="update_russia.py:yandex",
                        schema_version="1.2.0", extra_report={"completeness": "partial_certification_scope", "operational_status_not_inferred": True,
                        "enrichment_sources": [evidence(key) | {"source_scope": "observed" if key in ("post", "image") else "provider_declared"} for key in ("pci", "status", "post", "image")]})
    report["geojson_sha256"] = sha256(root / f"data/yandex/data-centers.{TAG}.geojson")
    write_json(root / f"data/yandex/data-centers.{TAG}.report.json", report)
    manifest = json.loads((REPO_ROOT / f"data/manifest.{TAG}.json").read_text())
    features = []
    layer_counts = {}
    source_layers = []
    for layer in manifest["layers"]:
        if layer["layer"] == "yandex/data-centers":
            continue
        path = REPO_ROOT / layer["files"]["geojson"]["path"]
        selected = [f for f in json.loads(path.read_text())["features"] if f["properties"]["country_code"] == "RU"]
        if selected:
            features.extend(selected)
            layer_counts[layer["layer"]] = len(selected)
            source_layers.append({"layer": layer["layer"], "path": repo_ref(path), "sha256": sha256(path)})
    yandex_path = root / f"data/yandex/data-centers.{TAG}.geojson"
    features.extend(json.loads(yandex_path.read_text())["features"])
    features.sort(key=lambda f: f["properties"]["record_id"])
    assert len(features) == len({f["properties"]["record_id"] for f in features})
    view_path = root / f"data/russia/locations-and-observations.{TAG}.geojson"
    write_json(view_path, {
        "type": "FeatureCollection", "metadata": {"view": "country_code=RU", "built_at": DATE,
        "scope": "retained_declarations_certification_identities_and_observations; not_current_operating_facility_total"}, "features": features,
    })
    write_json(view_path.with_suffix(".report.json"), {
        "layer": "russia/locations-and-observations", "retrieved_at": DATE,
        "record_count": len(features), "geojson_sha256": sha256(view_path),
        "view_of": [source["layer"] for source in source_layers] + ["yandex/data-centers"],
        "view_excluded_from_canonical_totals": True,
        "generated_files": [repo_ref(view_path)],
        "derived_files": {"csv": {"path": repo_ref(view_path.with_suffix(".csv")), "source": repo_ref(view_path),
                                   "generator": f"make {repo_ref(view_path.with_suffix('.csv'))}"}},
    })
    components = json.loads(raw_path("cloudflare").read_text())
    russian_components = [{"name": r["name"], "status": r["status"], "component_updated_at": r["updated_at"]}
                          for r in components["components"] if ", Russia" in r["name"]]
    assert "Russia: Moscow" in html_text("cachefly") and "St. Petersburg" in html_text("cachefly")
    write_json(root / f"data/russia/provider-assessment.{TAG}.json", {
        "retrieved_at": DATE, "scope": "Russian Federation country_code RU; bounded provider cohort, not a market census",
        "baseline_layer_counts": layer_counts, "baseline_sources": source_layers,
        "new_yandex_named_localities": len(rows), "derived_view_record_count": len(features),
        "derived_view_entity_types": dict(sorted(Counter(f["properties"]["entity_type"] for f in features).items())),
        "view_excluded_from_canonical_totals": True, "provider_review": provider_review(),
        "edge_rechecks": {
            "Google": {"listed_metros": ["Moscow", "Saint Petersburg"], "source_ref": "data/raw/google/peering-infrastructure.20261011.html", "precision": "metro"},
            "Cloudflare": {"source": evidence("cloudflare"), "page_updated_at": components["page"]["updated_at"], "russian_components": russian_components,
                           "retained_code_missing_from_returned_feed": "KJA", "missing_listing_is_not_proof_of_closure": True},
            "CacheFly": {"source": evidence("cachefly"), "listed_metros": ["Moscow", "St. Petersburg"]},
        },
        "limits": ["79 inherited Google city geolocations are observations, not owned facilities.",
                   "Seven retained edge declarations are metro/component assertions, not building counts.",
                   "No precise facility geometry or image capacity claim is manufactured.",
                   "No cloud-zone-to-building relationship is inferred from names or photographs.",
                   "Historical 2023 Russian labels in legacy CSVs remain separate from the reviewed inventory.",
                   "Provider access failures and source age remain explicit; registry relationships do not establish ownership."],
    })
    print(json.dumps({"yandex_named_localities": len(rows), "russia_view_records": len(features), "reviewed_provider_surfaces": len(provider_review())}))


if __name__ == "__main__":
    main()
