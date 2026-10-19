#!/usr/bin/env python3
"""Offline Chindata directory expansion and conservative China locality views."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urljoin
import zipfile

from geography_enrichment_common import (
    BASELINE, CATALOG, CLOUD_LAYERS, DATE, RAW, TAG, baseline_layers, evidence,
    read, record_evidence, source, soup,
)
from location_common import REPO_ROOT, canonical_record, load_validator, repo_ref, sha256, slug, write_json, write_layer

REGIONAL_KEYS = ["north", "yangtze", "greater-bay", "qingyang", "zhongwei", "ulanqab", "yichang"]
SELECTION = RAW / f"locality-selections.{TAG}.json"
SCHEMA = REPO_ROOT / "schema/geographic-footprint.schema.json"


def save(output_root, relative, payload):
    write_json(output_root / relative, payload)


def chindata(output_root):
    previous = {f["properties"]["record_id"]: f["properties"] for f in
                read(REPO_ROOT / "data/chindata/data-centers.20261011.geojson")["features"]}
    rows, traversed, named_bases = {}, [], []
    links = {urljoin(source("chindata-directory")["source_url"], a["href"])
             for a in soup("chindata-directory").find_all("a", href=True)}
    for region in REGIONAL_KEYS:
        key = "chindata-" + region
        if source(key)["source_url"] not in links:
            raise ValueError(f"Regional link not present on directory: {key}")
        bases = []
        for anchor in soup(key).find_all("a", href=True):
            match = re.fullmatch(r"/global/base/(\d+)\.html", anchor["href"])
            if not match:
                continue
            name = " ".join(anchor.get_text(" ", strip=True).split())
            gallery_key = "chindata-gallery-" + match[1]
            detail = evidence(gallery_key)
            base = {"source_name": name, "detail_source": detail, "regional_source": evidence(key)}
            if base not in bases:
                bases.append(base)
            if not re.fullmatch(r"China(?:North|East|South) [HW]\d+", name):
                named_bases.append(base)
                continue
            rid = "chindata:data_center:" + slug(name)
            if rid in rows:
                if rows[rid]["source_url"] != source(key)["source_url"]:
                    raise ValueError(f"Code listed in multiple regions, review required: {name}")
                continue
            src = evidence(key)
            src.pop("source_id")
            src.pop("source_updated_at")
            rows[rid] = canonical_record(
                schema_version="1.2.0", record_id=rid, aliases=[], provider="Chindata",
                service="chindata_colocation", entity_type="data_center", parent_record_id=None,
                jurisdiction_scope="mainland_china", access_status="not_applicable",
                service_scope=["colocation"], source_collection="chindata_chindata_colocation_directory",
                source_record_id=name, name=name, site_code=name, lifecycle_status="unknown",
                source_scope="provider_declared", city=None, metro=None, subdivision=None,
                country="China", country_code="CN", latitude=None, longitude=None,
                location_precision="unknown", coordinate_method="unknown", coordinate_crs=None,
                **src, first_seen=previous.get(rid, {}).get("first_seen", DATE), last_seen=DATE,
                confidence="high", properties={"regional_directory": region,
                    "code_to_campus_alias_not_established": True,
                    "directory_listing_does_not_establish_current_lifecycle": True,
                    "directory_completeness_not_asserted": True, "detail_evidence": detail,
                    "source_updated_at": None})
        traversed.append({"source_id": key, "source": evidence(key), "base_entries": bases,
                          "code_count": sum(bool(re.fullmatch(r"China(?:North|East|South) [HW]\d+", b["source_name"])) for b in bases)})
    if not set(previous) <= set(rows):
        raise ValueError("Historical Chindata code disappeared; reconcile before publication")
    # Gallery photographs are retained for review, never treated as coordinates.
    report = write_layer(records=list(rows.values()), output_dir=output_root / "data/chindata",
        layer_name="data-centers", retrieved_at=DATE,
        source_url=source("chindata-directory")["source_url"], raw_path=REPO_ROOT / source("chindata-directory")["path"],
        parser_name="update_geography_enrichment.py:chindata", extra_report={
            "traversed_regional_pages": traversed, "named_bases_separate_from_code_inventory": named_bases,
            "previous_record_count": len(previous), "new_code_count": len(rows) - len(previous),
            "enrichment_sources": [{**evidence("chindata-" + k), "source_scope": "provider_declared"} for k in REGIONAL_KEYS],
            "generated_files": [f"data/chindata/data-centers.{TAG}.geojson"],
            "derived_files": {"csv": {"path": f"data/chindata/data-centers.{TAG}.csv",
                "source": f"data/chindata/data-centers.{TAG}.geojson",
                "generator": f"make data/chindata/data-centers.{TAG}.csv"}},
        })
    return list(rows.values()), report


def campus_claims(output_root, codes):
    claims = []

    def add(identifier, names, locality, key, claim, *, kind="named_campus", date=None, phase=None, extra_keys=()):
        text = soup(key).get_text(" ", strip=True)
        # The selector is reviewed and explicit; a vanished name fails closed.
        if not any(name in text for name in names):
            raise ValueError(f"Named claim no longer present: {identifier}")
        claims.append({"claim_id": "chindata:locality-claim:" + identifier,
            "source_names": [n for n in names if n in text],
            "search_aliases_not_established_by_this_source": [n for n in names if n not in text],
            "provider": "Chindata", "operator_legal_entity": None,
            "operator_identity_note": "Provider brand is established; no legal-entity or property-title join inferred",
            "claim_type": kind, "phase": phase, "country_code": "CN", "locality": locality,
            "claim": claim, "claim_as_of": date, "current_lifecycle_status": "unknown",
            "address": None, "physical_site_confirmed": False, "canonical_code_match": None,
            "canonical_code_match_status": "unresolved", "evidence": [evidence(key)] + [evidence(k) for k in extra_keys]})

    add("sangyuan", ["Sangyuan Cloud Computing Campus", "桑园"], "Huailai", "chindata-news-192",
        "Campus inaugurated in Huailai, Zhangjiakou on 2020-01-14; the separate 2026 article reports an SST system in service at the named campus.",
        date="2020-01-14", extra_keys=("chindata-news-533",))
    add("donghuayuan", ["Donghuayuan", "东花园"], "Huailai", "chindata-news-194",
        "Named among Huailai's three campuses; exact relation to the Guanting Lake campus remains a candidate alias.", date="2020-02-08")
    add("guanting-lake", ["Guanting Lake", "官厅湖"], "Huailai", "chindata-news-192",
        "The article reports operation beginning in 2017; this is historical campus evidence.", date="2020-01-17")
    add("cunrui", ["Cunrui", "存瑞"], "Huailai", "chindata-news-194",
        "Campus described as about to enter use in February 2020; no present-day completion inferred.", date="2020-02-08")
    add("lingqiu-phase-9", ["秦淮数据9期"], "Lingqiu", "lingqiu-government-2026",
        "Phase 9 reported in production in the 2025 retrospective, presented 2025-12-28 and published 2026-04-01.",
        kind="project_phase", date="2025-12-28", phase="9")
    add("lingqiu-phase-10", ["秦淮10期"], "Lingqiu", "lingqiu-government-2026",
        "The 2026 work program calls for accelerating phase 10 construction; completion and present status are unestablished.",
        kind="project_phase", date="2025-12-28", phase="10")
    for key, cn, en in [("qingyang", "庆阳", "Qingyang"), ("zhongwei", "中卫", "Zhongwei")]:
        add(key + "-base", [cn], en, "chindata-" + key,
            "Named base link in the regional directory; no operating status, building count or code alias established.", kind="named_directory_base")
    payload = {"built_at": DATE, "record_unit": "dated_name_or_phase_assertion",
        "excluded_from_canonical_totals": True, "claims": claims,
        "code_matches": [{"record_id": r["record_id"], "source_name": r["name"], "match_status": "unresolved",
                          "campus_claim_id": None, "reason": "No explicit code-to-campus crosswalk in retained sources"} for r in sorted(codes, key=lambda r: r["record_id"])],
        "alias_relationships": [{"left_claim_id": "chindata:locality-claim:donghuayuan",
            "right_claim_id": "chindata:locality-claim:guanting-lake", "match_status": "candidate",
            "reason": "Same three-campus context, but no explicit equivalence statement", "evidence": [evidence("chindata-news-194")]}],
        "held_directory_areas": [{"source_id": "chindata-" + k, "reason": "Regional marketing page contains no named base entry; no deployed locality asserted"}
                                  for k in ("ulanqab", "yichang")],
        "interpretation": "Names and phases can overlap. Neither claim count nor locality count is a count of facilities."}
    save(output_root, f"data/chindata/campus-alias-review.{TAG}.json", payload)
    return payload


def gazetteer():
    selections = read(SELECTION)
    rows = {}
    info = source("geonames-cities15000")
    with zipfile.ZipFile(REPO_ROOT / info["path"]) as archive:
        for row in csv.reader(io.StringIO(archive.read("cities15000.txt").decode("utf-8")), delimiter="\t"):
            rows[row[0]] = (row, "geonames-cities15000")
    info = source("geonames-cn")
    for row in csv.reader((REPO_ROOT / info["path"]).open(), delimiter="\t"):
        rows[row[0]] = (row, "geonames-cn")
    lookup = {}
    for selected in selections["places"]:
        row, source_id = rows[selected["geonames_id"]]
        expected = [selected[k] for k in ("expected_name", "country_code", "expected_feature_code", "expected_admin1", "expected_admin2")]
        if [row[1], row[8], row[7], row[10], row[11]] != expected:
            raise ValueError(f"Reviewed gazetteer identity changed: {selected}")
        if selected["location_precision"] == "county" and row[7] != "ADM3":
            raise ValueError("County point must use reviewed county, not its town seat")
        if selected["location_precision"] == "city" and row[6] != "P":
            raise ValueError("City point must use reviewed populated place")
        lookup[(selected["country_code"], selected["source_locality"])] = (selected, row, source_id)
    return lookup


def footprints(output_root, campus_review):
    places, groups, held, inputs, excluded_zones = gazetteer(), {}, [], [], []
    canonical_count = 0

    def add(vendor, provider, service, country, locality, record_id, claim_id, refs):
        identity = places.get((country, locality))
        if not identity:
            held.append({"vendor_id": vendor, "record_id": record_id, "claim_id": claim_id,
                         "country_code": country, "source_locality": locality,
                         "reason": "No reviewed city/county identity; broad or missing labels stay unlocated"})
            return
        selected, place, key = identity
        group_key = (vendor, service, place[0])
        if group_key not in groups:
            groups[group_key] = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(place[5]), float(place[4])]},
                "properties": {"footprint_id": f"{vendor}:locality:{service}:{place[0]}",
                    "vendor_id": vendor, "provider": provider, "service": service, "locality": locality,
                    "country_code": country, "location_precision": selected["location_precision"],
                    "coordinate_method": "gazetteer_reference_point", "coordinate_crs": "EPSG:4326",
                    "record_unit": "provider_service_locality", "physical_site_confirmed": False,
                    "lifecycle_status": "not_assessed", "source_record_ids": [], "source_claim_ids": [],
                    "source_locality_labels": [], "evidence": [], "excluded_from_canonical_totals": True,
                    "gazetteer": {"geonames_id": place[0], "name": place[1], "feature_code": place[7],
                        "admin1": place[10], "evidence": evidence(key),
                        "license_url": "https://creativecommons.org/licenses/by/4.0/"}}}
        p = groups[group_key]["properties"]
        for field, value in [("source_record_ids", record_id), ("source_claim_ids", claim_id), ("source_locality_labels", locality)]:
            if value and value not in p[field]:
                p[field].append(value)
        for ref in refs:
            if ref not in p["evidence"]:
                p["evidence"].append(ref)

    layers = baseline_layers()
    for name in CLOUD_LAYERS:
        info = layers[name]["files"]["geojson"]
        inputs.append({"layer": name, **info})
        for feature in read(REPO_ROOT / info["path"])["features"]:
            row = feature["properties"]
            canonical_count += 1
            if row["entity_type"] == "availability_zone":
                excluded_zones.append(row["record_id"])
                continue
            add(name.split("/")[0], row["provider"], row["service"], row["country_code"], row["city"],
                row["record_id"], None, [record_evidence(row)])
    for claim in campus_review["claims"]:
        add("chindata", "Chindata", "chindata_colocation", claim["country_code"], claim["locality"],
            None, claim["claim_id"], claim["evidence"])
    features = [groups[k] for k in sorted(groups)]
    for f in features:
        p = f["properties"]
        for key in ["source_record_ids", "source_claim_ids", "source_locality_labels"]:
            p[key].sort()
        p["evidence"].sort(key=lambda r: r["raw_source_ref"])
    collection = {"type": "FeatureCollection", "schema_version": "1.0.0", "built_at": DATE,
                  "excluded_from_canonical_totals": True, "features": features}
    load_validator(SCHEMA).validate(collection)
    path = f"data/china/provider-localities.{TAG}.geojson"
    save(output_root, path, collection)
    report = {"built_at": DATE, "record_count": len(features), "record_unit": "provider_service_locality",
        "excluded_from_canonical_totals": True, "canonical_input_count": canonical_count,
        "located_source_record_count": sum(len(f["properties"]["source_record_ids"]) for f in features),
        "located_claim_count": sum(len(f["properties"]["source_claim_ids"]) for f in features),
        "excluded_availability_zone_ids": sorted(excluded_zones), "held_records": held,
        "input_layers": inputs, "vendor_counts": dict(sorted(Counter(f["properties"]["vendor_id"] for f in features).items())),
        "selection": {"path": repo_ref(SELECTION), "sha256": sha256(SELECTION)},
        "gazetteer_sources": [evidence(k) for k in ("geonames-cities15000", "geonames-cn", "geonames-readme")],
        "interpretation": "Locality reference points are cartographic aids, not facility coordinates. AZs are excluded, same-provider/service/locality memberships are grouped, source dates remain unchanged, and current operation is not reassessed.",
        "derived_files": {"csv": {"path": path.replace(".geojson", ".csv"), "source": path,
            "generator": "make " + path.replace(".geojson", ".csv")}}}
    save(output_root, f"data/china/provider-localities.{TAG}.report.json", report)
    return report


def assessment(output_root, report, chindata_report):
    plan = read(REPO_ROOT / "data/china/enrichment-plan.20261011.json")
    old_catalog = read(REPO_ROOT / "data/raw/china-enrichment/catalog.20261011.json")
    prior_ali = next(s for s in old_catalog["sources"] if s["source_id"] == "alibaba-directory")
    from bs4 import BeautifulSoup

    def directory_tables(document):
        return [{"heading": " ".join(t.find_previous(["h2", "h3", "h4"]).get_text(" ", strip=True).split()),
                 "rows": [[" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"], recursive=False)]
                          for tr in t.find_all("tr")]} for t in document.find_all("table")]

    previous_tables = directory_tables(BeautifulSoup((REPO_ROOT / prior_ali["path"]).read_bytes(), "html.parser"))
    current_tables = directory_tables(soup("alibaba-directory"))
    if not current_tables or previous_tables != current_tables:
        raise ValueError("Alibaba directory tables changed: parse/reconcile before keeping previous hierarchy")
    layers = baseline_layers()
    vendors = []
    for vendor in plan["vendors"]:
        key = vendor["vendor_id"]
        owned = [layer for name, layer in layers.items() if name.split("/")[0] == key]
        if key == "chindata":
            count, unlocated = chindata_report["record_count"], chindata_report["geometry_null"]
        else:
            count, unlocated = sum(l["record_count"] for l in owned), sum(l["geometry_null"] for l in owned)
        if key in {n.split("/")[0] for n in CLOUD_LAYERS}:
            next_step = "Resolve held region/pool labels against provider product directories; add explicit region/AZ identities only when published. Keep locality points separate from physical facilities."
        elif key == "chindata":
            next_step = "Join code labels to legal operator, campus, address and phase using provider crosswalks and local permits; validate original coordinate CRS before any facility geometry."
        elif "colocation" in vendor["vendor_class"] or "facility_operator" in vendor["vendor_class"]:
            next_step = "Reconcile existing recognition/portfolio evidence to itemized campus, legal-operator and address records; seek planning, EIA and completion documents with explicit project IDs."
        elif key in {"wangsu", "baishan", "bilibili"}:
            next_step = "Capture itemized POP directories and provider geofeeds; corroborate dated routing and facility relationships. Fleet totals and CDN observations do not establish owned buildings."
        elif key in {"china-mobile", "china-unicom", "ucloud"}:
            next_step = "Capture product resource-pool/region APIs and named facility lists; separate carrier network, GPU product availability and physical deployment evidence."
        else:
            next_step = "Seek explicit hosting/operator/region statements and dated service endpoints; model availability, headquarters and domain registration do not establish physical hosting."
        vendors.append({"vendor_id": key, "name": vendor["name"], "vendor_class": vendor["vendor_class"],
            "canonical_location_records": count, "canonical_geometry_null": unlocated,
            "derived_locality_points": report["vendor_counts"].get(key, 0),
            "held_non_zone_records": sum(r["vendor_id"] == key for r in report["held_records"]),
            "source_snapshot_dates": [DATE] if key == "chindata" else sorted({d for l in owned for d in l["retrieved_at"]}),
            "existing_review_source_ids": vendor["reviewed_source_ids"], "next_step": next_step,
            "review_scope": "existing China-review cohort; inclusion is not an ownership or nationality assertion"})
    payload = {"built_at": DATE, "baseline_manifest": {"path": repo_ref(BASELINE), "sha256": sha256(BASELINE)},
        "source_catalog": {"path": repo_ref(CATALOG), "sha256": sha256(CATALOG)},
        "vendors": vendors, "vendor_count": len(vendors), "locality_points": report["record_count"],
        "chindata_code_count": chindata_report["record_count"], "chindata_new_codes": chindata_report["new_code_count"],
        "alibaba_reconciliation": {"reviewed_at": DATE, "directory_tables_equal_to_20261011": True,
            "comparison_method": "Ordered table cells and immediately preceding section headings, whitespace normalized; scripts excluded",
            "table_count": len(current_tables),
            "normalized_tables_sha256": hashlib.sha256(json.dumps(current_tables, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "fresh_source": evidence("alibaba-directory"), "previous_directory_sha256": prior_ali["sha256"],
            "canonical_layer_retained": layers["alibaba/regions-and-zones"]["files"]["geojson"],
            "region_count": layers["alibaba/regions-and-zones"]["entity_types"]["cloud_region"],
            "availability_zone_count": layers["alibaba/regions-and-zones"]["entity_types"]["availability_zone"],
            "note": "Fresh directory tables match; raw pages differ in tracking script values. Original canonical dates remain intact. Johor zone-count conflict and broad city labels remain unresolved."},
        "scope_note": "This implementation expands Chindata and adds cartographic locality views for nine existing China cloud directories. The 31-vendor assessment records remaining work; it does not claim every vendor has newly verified physical sites."}
    save(output_root, f"data/china/geography-enrichment.{TAG}.json", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    codes, chindata_report = chindata(args.output_root)
    claims = campus_claims(args.output_root, codes)
    report = footprints(args.output_root, claims)
    result = assessment(args.output_root, report, chindata_report)
    print(json.dumps({"chindata_codes": len(codes), "locality_points": report["record_count"],
                      "vendors_reviewed": result["vendor_count"], "mapped_vendors": report["vendor_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
