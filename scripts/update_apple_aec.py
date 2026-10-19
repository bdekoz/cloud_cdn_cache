#!/usr/bin/env python3
"""Map explicit Apple cache localities and retain unlocated host/IX evidence."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess

from location_common import REPO_ROOT, load_validator, sha256, write_json
from update_apple_tv import CATALOG, DATE, TAG, INFRA as TV_INFRA, csv_target, evidence, read, row, soup, text, sources
from update_infrastructure import validate_collection

INFRA = f"data/infrastructure/apple-aec-hosts.{TAG}.json"
VIEW = f"data/apple/aec-localities.{TAG}.geojson"
REVIEW = f"data/apple/aec-review.{TAG}.json"


def assertion(key, identifier, category, host, properties, published=None, country=None):
    r = row(key, identifier, category, "Apple", f"Apple cache evidence: {host}",
            {"service": "Apple Edge Cache / host-declared Apple caching", "host_operator": host,
             "apple_tv_delivery_established": False, "cache_hardware_count": None, "cache_site_count": None,
             "locality": None, "aec_program_identity_explicit": True, **properties}, declared=True, country=country)
    r["record_id"] = "apple:aec:" + identifier
    r["parties"] = [{"name": "Apple", "role": "content_provider"}, {"name": host, "role": "declaring_host_or_exchange"}]
    r["source_published_at"] = published
    return r


def build_rows():
    rows = []
    lyon = soup("aec-franceix-lyon").get_text(" ", strip=True)
    assert all(t in lyon for t in ["Lyon/AURA", "installation de caches Apple", "ces deux caches"])
    slides_path = REPO_ROOT / sources()["aec-franceix-lyon-slides"]["path"]
    slides = subprocess.check_output(["pdftotext", "-raw", str(slides_path), "-"], text=True).split("\f")
    assert "19 juin 2025" in " ".join(slides[0].split())
    assert all(t in " ".join(slides[4].split()) for t in ["venir à Lyon", "caches hébergés par France-IX", "Les caches Microsoft et Apple sont arrivés"])
    rows.append(assertion("aec-franceix-lyon", "franceix-lyon", "cache_host_declaration", "France-IX",
        dict(locality="Lyon", country_code="FR", claim_period="2025-Q2", cache_hardware_count=2,
             cache_site_count=None, aec_program_identity_explicit=False,
             product_identity_note="Operator calls them Apple caches; the AEC program name is not explicit.",
             reported_installation=True, current_operation_not_verified=True,
             presentation_claim_date="2025-06-19",
             presentation_date_basis="PDF cover; the May date in its filename is not used as the claim date.",
             locality_corroboration_evidence={**evidence("aec-franceix-lyon-slides"), "page": 5, "date_on_page": 1},
             location_basis="Operator technical report names Lyon/AURA; no individual cache addresses."), country="FR"))
    cenet = soup("aec-cenet-deployment")
    assert "installed within CEnet" in cenet.get_text(" ", strip=True)
    ld = next(json.loads(s.get_text()) for s in cenet.find_all("script", type="application/ld+json") if '"datePublished"' in s.get_text())
    r = assertion("aec-cenet-deployment", "cenet", "cache_host_declaration", "CEnet",
        dict(reported_installation=True, traffic_example_date="2023-11-17", current_operation_not_verified=True,
             mapping_disposition="held_no_cache_city", address_not_inferred_from_office_or_member_schools=True), ld["datePublished"][:10])
    r["source_updated_at"] = ld["dateModified"][:10]
    rows.append(r)
    tenet = read(REPO_ROOT / sources()["aec-tenet-web"]["path"])
    assert "Apple Edge Cache" in str(tenet["response"])
    rows.append(assertion("aec-tenet-web", "tenet", "cache_host_declaration", "TENET",
        dict(reported_installation=True, mapping_disposition="held_no_cache_city",
             address_not_inferred_from_office_or_service_area=True,
             current_operation_not_verified=True, incident_to_cache_mapping_not_established=True), "2026-09-16"))
    for key, identifier, host, expected in [
        ("aec-lucix-members", "lucix", "LU-CIX", "Apple Edge Cache"),
        ("aec-1ix-members", "1ix", "1-IX", "Apple Edge Cache"),
        ("aec-pitix-members", "pitix", "PIT-IX", "Apple AEC")]:
        table = next(tr.get_text(" ", strip=True) for tr in soup(key).find_all("tr") if expected in tr.get_text())
        assert "31128" in table
        p = dict(declared_asn=31128, mapping_disposition="held_membership_not_cache_location",
                 remote_peering_not_excluded=True, all_exchange_sites_are_cache_sites=False)
        if identifier == "pitix":
            assert "2026-07-27" in table
            p.update(member_joined_at="2026-07-27", join_date_is_not_installation_date=True)
        if identifier == "lucix":
            assert "2*100GE" in table
            p.update(connection_capacity_as_published="2*100GE", capacity_is_not_cache_count=True)
        if identifier == "1ix":
            assert "According to peering data DB" in soup(key).get_text(" ", strip=True)
            p["not_independent_of_peeringdb"] = True
        rows.append(assertion(key, identifier, "cache_exchange_reference", host, p))
    guide = soup("aec-ixaustralia-guide").get_text(" ", strip=True)
    assert all(t in guide for t in ["QLD-IX", "Apple (AEC)", "10084:4711", "10084:4712"])
    rows.append(assertion("aec-ixaustralia-guide", "ixaustralia-qld", "cache_exchange_reference", "IX Australia",
        dict(exchange="QLD-IX", delivery_network_asn=10084, opt_in_community="10084:4712", opt_out_community="10084:4711",
             mapping_disposition="held_exchange_scope_not_cache_site", locality_not_inferred_from_exchange_name=True)))
    bix = str(read(REPO_ROOT / sources()["aec-bix-web"]["path"])["response"])
    assert "Giganet" in bix and "Pilot" in bix
    rows.append(assertion("aec-bix-web", "bix-pilot", "cache_pilot_reference", "BIX / Giganet",
        dict(claim_type="pilot_connection_opportunity", mapping_disposition="held_pilot_not_located_deployment",
             current_operation_not_verified=True), "2025-01-06"))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    rows = sorted(build_rows(), key=lambda r: r["record_id"])
    tv_path = args.output_root / TV_INFRA
    if not tv_path.exists():
        tv_path = REPO_ROOT / TV_INFRA
    tv = read(tv_path)
    collection = dict(type="InfrastructureEvidenceCollection", schema_version="1.0.0", retrieved_at=DATE,
        scope_note="Cache hosts, deployment declarations and IX participation are different units. Only explicit cache localities are mapped; current operation is unverified.",
        categories={"cache_host_declaration": "Host confirms installed Apple caching, sometimes without a location or explicit AEC product name.",
                    "cache_exchange_reference": "Apple cache access or membership at an exchange; not an installed-cache location.",
                    "cache_pilot_reference": "A dated pilot/access opportunity; not a located operational deployment."}, records=rows)
    validate_collection(collection)
    write_json(args.output_root / INFRA, collection)
    write_json((args.output_root / INFRA).with_suffix(".report.json"), dict(built_at=DATE, record_count=len(rows),
        physical_site_total=None, parser="scripts/update_apple_aec.py", derived_files=csv_target(INFRA)))
    sfmix = next(r for r in tv["records"] if r["record_id"] == "apple:tv:sfmix-aec-scl02")
    lyon = next(r for r in rows if r["record_id"] == "apple:aec:franceix-lyon")
    gazetteer = {r[0]: r for r in csv.reader(text("aec-geonames").splitlines(), delimiter="\t")}
    features = []
    for claim, gid, service in [(sfmix, "5393015", "Apple Edge Cache"),
                                 (lyon, "2996944", "Apple hosted caches; AEC program name unconfirmed")]:
        g = gazetteer[gid]
        assert g[1] == claim["properties"]["locality"]
        features.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[float(g[5]), float(g[4])]),
            properties=dict(footprint_id=f"footprint:apple:cache-hosting:{gid}", provider="Apple", vendor_id="apple",
                service=service, locality=g[1], country_code=g[8], location_precision="city",
                coordinate_method="gazetteer_reference_point", coordinate_crs="EPSG:4326", record_unit="provider_service_locality",
                physical_site_confirmed=False, lifecycle_status="not_assessed", source_record_ids=[],
                source_claim_ids=[claim["record_id"]], source_locality_labels=[g[1]],
                evidence=[{k: claim[k] for k in ("source_url", "raw_source_ref", "source_sha256", "retrieved_at")}],
                gazetteer=dict(geonames_id=gid, feature_code=g[7], admin1=g[10], name=g[1], evidence=evidence("aec-geonames"),
                               license_url="https://creativecommons.org/licenses/by/4.0/"), excluded_from_canonical_totals=True)))
    view = dict(type="FeatureCollection", schema_version="1.0.0", built_at=DATE, excluded_from_canonical_totals=True, features=features)
    load_validator(REPO_ROOT / "schema/geographic-footprint.schema.json").validate(view)
    write_json(args.output_root / VIEW, view)
    write_json((args.output_root / VIEW).with_suffix(".report.json"), dict(built_at=DATE, record_count=2,
        explicitly_named_aec_localities=1, apple_cache_localities_program_unconfirmed=1,
        physical_sites=False, excluded_from_canonical_totals=True,
        input_layers=[dict(layer="infrastructure/apple-aec-hosts", path=INFRA, sha256=sha256(args.output_root / INFRA)),
                      dict(layer="infrastructure/apple-tv-delivery", path=TV_INFRA, sha256=sha256(tv_path))],
        overlap_note="Santa Clara also appears in the Apple TV delivery view; these are overlapping service views, not additive deployments.",
        interpretation="City reference points. Santa Clara has explicit AEC/TV host evidence with unresolved lifecycle; Lyon has a Q2 2025 Apple-cache installation declaration without an explicit AEC program name.",
        derived_files=csv_target(VIEW)))
    write_json(args.output_root / REVIEW, dict(built_at=DATE, mapped_localities=2, canonical_records_added=0,
        source_catalog=dict(path=str(CATALOG.relative_to(REPO_ROOT)), sha256=sha256(CATALOG)),
        explicitly_named_aec_localities=1, apple_cache_localities_program_unconfirmed=1,
        locality_dispositions=[dict(record_id=sfmix["record_id"], host="SFMIX",
             disposition="mapped_declared_cache_site_city_current_lifecycle_unresolved")]
             + [dict(record_id=r["record_id"], host=r["properties"]["host_operator"],
             disposition=r["properties"].get("mapping_disposition", "mapped_operator_declared_city_program_unconfirmed")) for r in rows],
        retained_source_limits={"aec-peeringdb-network": "Entity-not-found response; no AS31128 network object admitted.",
            "aec-peeringdb-ix": "Empty result; not proof that AEC has no exchange relationships.",
            "aec-peeringdb-fac": "Response exceeded capture limit; filter may not be supported. No facility rows admitted.",
            "aec-tenet-deployment": "Direct HTTP capture did not expose article text; separately retained web-reader text supports the declaration.",
            "aec-bix-pilot": "Direct HTTP capture did not expose article text; separately retained web-reader text supports the pilot reference."},
        gaps=["No complete public AEC inventory; Apple AS714/6185 presence and provider geofeeds are not AEC installation lists.",
              "India, Gulf, Russia and China have no locality admitted by this bounded host review.",
              "CEnet and TENET need an explicit cache-city/site declaration. LU-CIX, 1-IX, PIT-IX and IX Australia need cache placement, not only IX membership or cache-access policy.",
              "Lyon needs an explicit AEC program identity and newer operating-status confirmation; Santa Clara needs the cache-versus-peering status and sampled-IP-to-site join resolved."],
        next_step="Retain ordinary public-preview response headers from known access networks, then join discovered cache host labels to explicit operator site declarations. Do not force unknown hosts onto office or IX coordinates."))
    print(f"Apple cache map: {len(features)} locality references, {len(rows)} host/IX assertions")


if __name__ == "__main__":
    main()
