#!/usr/bin/env python3
"""Build Apple TV delivery assertions from retained public manifests and HTTP traces."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from functools import lru_cache
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from capture_apple_tv import CATALOG, DATE, TAG
from location_common import REPO_ROOT, load_validator, repo_ref, sha256, write_json
from network_common import canonical_network_record, write_network_layer
from update_infrastructure import validate_collection
from update_network import utc_datetime

BASELINE = REPO_ROOT / f"data/raw/repository/manifest-before-apple-tv.{TAG}.json"
INFRA = f"data/infrastructure/apple-tv-delivery.{TAG}.json"
VIEW = f"data/apple/tv-delivery-localities.{TAG}.geojson"
ASSESSMENT = f"data/apple/tv-delivery-review.{TAG}.json"
CDNS = {"vod-ap-aoc.tv.apple.com": ("Apple", "aapl"),
        "vod-ak-aoc.tv.apple.com": ("Akamai", "akam"),
        "vod-fa-aoc.tv.apple.com": ("Fastly", "fsly")}


def read(path):
    return json.loads(path.read_text())


@lru_cache
def sources():
    items = read(CATALOG)["sources"]
    for s in items:
        if s.get("path"):
            if sha256(REPO_ROOT / s["path"]) != s["sha256"]:
                raise ValueError(f"Changed source: {s['source_id']}")
            if read(REPO_ROOT / (s["path"] + ".provenance.json")) != s:
                raise ValueError(f"Changed source metadata: {s['source_id']}")
    return {s["source_id"]: s for s in items}


def source(key):
    s = sources()[key]
    if s["result"] != "retrieved":
        raise ValueError(f"Unavailable source: {key}")
    return s


def text(key):
    return (REPO_ROOT / source(key)["path"]).read_text()


def soup(key):
    return BeautifulSoup(text(key), "html.parser")


def evidence(key, metadata=False):
    s = source(key)
    ref = s["path"] + (".provenance.json" if metadata else "")
    return dict(source_url=s["source_url"], raw_source_ref=ref, source_sha256=sha256(REPO_ROOT / ref),
                source_published_at=s.get("source_published_at"), source_updated_at=s.get("source_updated_at"),
                retrieved_at=s["retrieved_at"])


def row(key, identifier, category, provider, name, properties, *, metadata=False,
        declared=False, country=None, confidence="high", relationships=()):
    return dict(record_id="apple:tv:" + identifier, category=category, unit="assertion", name=name,
                provider=provider, parties=[{"name": "Apple", "role": "service_provider"},
                                           {"name": provider, "role": "delivery_or_hosting_party"}],
                country_codes=[country] if country else [],
                country_scope="explicit_locality_reference" if country else "not_geolocated",
                lifecycle_status="unknown", source_scope="provider_declared" if declared else "observed",
                **evidence(key, metadata), confidence=confidence, geometry=None, spatial_representation="none",
                relationships=list(relationships), properties={"service": "Apple TV content delivery",
                    "physical_site_count_not_asserted": True, "origin_facility_not_asserted": True, **properties})


def build_infrastructure():
    rows = []
    server_data = json.loads(soup("tv-ted-lasso").find("script", id="serialized-server-data").string)
    # Preserve discovery through Preview objects, rather than guessing media hosts.
    masters = []
    for index in (0, 3):
        key = f"tv-preview-{index}"
        s = source(key)
        obj = server_data
        for part in s["discovery_pointer"].split("/")[1:]:
            obj = obj[int(part)] if isinstance(obj, list) else obj[part]
        assert obj == s["source_url"]
        shelf = server_data["data"][1]["data"]["shelves"][2]
        playable = shelf["playlistItems"][index]["playable"]
        assert shelf["items"][index]["type"] == "Preview" and playable["entitlementReason"] == "Free"
        body = text(key)
        assert body.startswith("#EXTM3U\n")
        urls = re.findall(r'https://[^\s"<>]+', body)
        hosts = Counter(urlparse(u).hostname for u in urls if urlparse(u).hostname in CDNS)
        assert set(hosts) == set(CDNS)
        masters.append(dict(source_id=key, title=playable["title"], content_type="Preview",
                            entitlement_reason="Free", discovery_pointer=s["discovery_pointer"],
                            advertised_cdn_hosts=dict(sorted(hosts.items())),
                            content_steering_tag_present="#EXT-X-CONTENT-STEERING:" in body,
                            evidence=evidence(key), discovery_evidence=evidence("tv-ted-lasso")))
        for host, count in sorted(hosts.items()):
            rows.append(row(key, f"preview-{index}-{host.split('.')[0]}", "media_delivery_path",
                            CDNS[host][0], f"{playable['title']}: {host}",
                            dict(hostname=host, manifest_url_reference_count=count, title=playable["title"],
                                 browser_path_selection_not_observed=True, subscription_playback_not_tested=True,
                                 discovery_pointer=s["discovery_pointer"], discovery_evidence=evidence("tv-ted-lasso"))))
    samples = [("tv-home", "web_frontend", "Akamai"), ("tv-javascript", "web_javascript", "Akamai"),
               ("tv-artwork-headers", "artwork", "Apple")]
    samples += [("tv-variant-" + h.split(".")[0], "public_preview_video_playlist", p[0]) for h, p in CDNS.items()]
    for key, role, provider in samples:
        s = source(key)
        h = s["response_headers"]
        assert s["http_status"] == 200
        if role == "public_preview_video_playlist":
            host = urlparse(s["source_url"]).hostname
            assert h["cdn-server"] == CDNS[host][1]
            assert source("tv-preview-0")["path"] and s["source_url"] == text("tv-preview-0").splitlines()[s["discovery_line"] - 1]
        elif provider == "Akamai":
            assert "akamai" in json.dumps(h).lower()
        else:
            assert "applecdn" in h["x-cache"] and ".ts.apple.com" in h["via"]
        rows.append(row(key, key, "service_delivery_observation", provider, f"Apple TV {role}: {provider}",
                        dict(endpoint_role=role, hostname=urlparse(s["source_url"]).hostname,
                             observed_at=s["captured_at"], http_status=s["http_status"],
                             http_peer_address=s.get("http_peer_address"),
                             measurement_vantage_country_code=None, method=s["method"],
                             response_headers={k: h[k] for k in ("cdn-server", "x-cdn", "x-cache", "x-served-by", "via", "date", "age", "x-city") if k in h},
                             content_evidence=evidence(key), cached_header_dates_are_not_observation_times=True,
                             server_header_alone_not_used_for_cdn_attribution=True), metadata=True))
    # API and telemetry roles are extracted from published application metadata, not probed as playback origins.
    for host, role, key in [("uts-api.itunes.apple.com", "catalog_api", "tv-ted-lasso"),
                            ("play-edge.itunes.apple.com", "playback_manifest_service", "tv-ted-lasso"),
                            ("mediaservices.cdn-apple.com", "player_telemetry_configuration", "tv-javascript")]:
        assert host in text(key)
        rows.append(row(key, "endpoint-" + host.split(".")[0], "service_endpoint_reference", "Apple",
                        f"Apple TV {role}: {host}", dict(hostname=host, endpoint_role=role,
                            role_basis="public_application_metadata", video_origin_not_asserted=True)))
    headers = source("tv-variant-vod-fa-aoc")["response_headers"]
    node = headers["x-served-by"]
    assert "," not in node
    code = node.rsplit("-", 1)[-1]
    cells = next([c.get_text(" ", strip=True) for c in tr.find_all("td")]
                 for tr in soup("fastly-pop-directory").find_all("tr")
                 if any(td.get_text(strip=True) == code for td in tr.find_all("td")))
    assert cells[0] == "Palo Alto" and cells[1] == "PAO"
    rows.append(row("tv-variant-vod-fa-aoc", "fastly-pao", "cdn_pop_observation", "Fastly",
                    "Apple TV public preview delivery through Fastly PAO", dict(locality=cells[0], pop_code=code,
                        observed_node_label=node, observed_at=source("tv-variant-vod-fa-aoc")["captured_at"],
                        pop_directory_evidence=evidence("fastly-pop-directory"), header_semantics_evidence=evidence("fastly-served-by"),
                        shielding_evidence=evidence("fastly-shielding"), facility_address=None,
                        one_response_not_global_coverage=True), metadata=True, country="US"))
    card = next(c.get_text(" ", strip=True) for c in soup("sfmix-cache-network").select(".source")
                if "Apple Edge Cache" in c.get_text())
    address_cells = next([c.get_text(" ", strip=True) for c in tr.find_all("td")]
                         for tr in soup("sfmix-locations").find_all("tr") if "scl02 / 5" in tr.get_text())
    status = next(tr.get_text(" ", strip=True) for tr in soup("sfmix-participants").find_all("tr")
                  if "31128" in tr.get_text())
    assert all(t in card for t in ["Apple TV+", "SCL02", "AS31128"])
    assert "2972 Stender Way, Santa Clara" in address_cells[1] and "Inactive" in status
    rows.append(row("sfmix-cache-network", "sfmix-aec-scl02", "cache_host_declaration", "Apple",
                    "SFMIX declares Apple TV+ on Apple Edge Cache at SCL02", dict(locality="Santa Clara",
                        host_operator="SFMIX", declared_cache_asn=31128, delivery_network_asn=40271,
                        site_code="SCL02", address_as_published=address_cells[1], facility_operator=address_cells[2],
                        site_directory_evidence=evidence("sfmix-locations"), participant_status="Inactive",
                        participant_status_evidence=evidence("sfmix-participants"),
                        status_resolution="Cache hosting declaration and IX membership have different scopes; current site lifecycle unresolved.",
                        sampled_peer_to_site_mapping_asserted=False,
                        all_sfmix_sites_are_apple_caches=False), declared=True, country="US", confidence="medium"))
    rows.append(row("sfmix-participants", "sfmix-apple-membership", "peering_status_reference", "SFMIX",
                    "SFMIX Apple Cache AS31128 participant entry", dict(participant_name="Apple Cache", asn=31128,
                        participant_status="Inactive", site_code=None, cache_delivery_inactivity_not_inferred=True,
                        conflicting_scope_evidence=evidence("sfmix-cache-network")), declared=True))
    return sorted(rows, key=lambda r: r["record_id"]), masters


def resolution_review():
    feed = []
    for lineno, cells in enumerate(csv.reader(text("apple-geofeed").splitlines()), 1):
        if not cells or cells[0].startswith("#"):
            continue
        feed.append((ipaddress.ip_network(cells[0]), cells, lineno))
    def match(address):
        ip = ipaddress.ip_address(address)
        matches = sorted((r for r in feed if ip in r[0]), key=lambda r: r[0].prefixlen, reverse=True)
        if not matches:
            return None
        _, cells, lineno = matches[0]
        return dict(prefix=cells[0], country_code=cells[1], subdivision=cells[2], city=cells[3],
                    source_line=lineno, evidence=evidence("apple-geofeed"), physical_pop_not_confirmed=True)
    observations = []
    for key, s in sorted(sources().items()):
        if not key.startswith("dns-"):
            continue
        data = json.loads(text(key))
        assert data["Status"] == 0
        observations.append(dict(hostname=s["queried_hostname"], rrtype=s["rrtype"], observed_at=s["captured_at"],
            resolver="Google Public DNS", measurement_vantage_country_code=None, ecs="0.0.0.0/0",
            cnames=[a["data"] for a in data.get("Answer", []) if a["type"] == 5],
            addresses=[dict(address=a["data"], provider_geofeed_match=match(a["data"]))
                       for a in data.get("Answer", []) if a["type"] in (1, 28)], evidence=evidence(key)))
    return observations, match(source("tv-variant-vod-ap-aoc")["http_peer_address"])


def build_network(output):
    records = []
    pairs = [("tv-variant-vod-ap-aoc", "SFMIX", "http_peer"), ("tv-variant-vod-ak-aoc", "Akamai", "http_peer"),
             ("tv-variant-vod-fa-aoc", "Fastly", "http_peer"), ("dns-vod-ap-aoc-tv-apple-com-a", "Apple", "resolver_answer")]
    for key, provider, basis in pairs:
        s = source(key)
        address = s["http_peer_address"] if basis == "http_peer" else next(a["data"] for a in json.loads(text(key))["Answer"] if a["type"] == 1)
        route_key = "routing-" + address.replace(".", "-")
        payload = json.loads(text(route_key))
        prefix, asns = payload["data"]["prefix"], payload["data"]["asns"]
        assert ipaddress.ip_address(address) in ipaddress.ip_network(prefix)
        for asn in asns:
            e = evidence(route_key)
            e.pop("source_updated_at")
            records.append(canonical_network_record(record_id=f"network:apple-tv:routing-{address}-{asn}", evidence_type="routing_origin",
                subject_type="prefix", subject_id=prefix, provider=provider, service="apple_tv_delivery",
                prefix=prefix, ip_family=ipaddress.ip_address(address).version, asn=int(asn), relationship_type="originates_prefix",
                object_type="asn", object_id=f"AS{asn}", status="announced", source_scope="observed", **e,
                observed_at=utc_datetime(payload["time"]), valid_from=None, valid_to=None, confidence="high",
                properties=dict(sample_address=address, address_basis=basis, address_evidence=evidence(key, basis == "http_peer"),
                    delivery_provider="Apple" if provider == "SFMIX" else provider, network_owner_is_not_cache_vendor=True,
                    physical_location_not_asserted=True, service_health_not_asserted=True)))
    write_network_layer(records=records, layer_name="apple-tv-routing", retrieved_at=DATE,
                        parser_name="scripts/update_apple_tv.py", output_root=output)
    return records


def csv_target(path):
    target = str(Path(path).with_suffix(".csv"))
    return {"csv": {"path": target, "source": path, "generator": "make " + target}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    output = args.output_root
    rows, masters = build_infrastructure()
    categories = {
        "media_delivery_path": "One advertised CDN hostname per public preview manifest; repeated renditions are not separate sites.",
        "service_delivery_observation": "One bounded HTTP response for a specified Apple TV content role.",
        "service_endpoint_reference": "A role-specific endpoint published by the web application, without an origin-location claim.",
        "cdn_pop_observation": "A sampled response cache code joined to the delivery provider's city directory.",
        "cache_host_declaration": "An explicit host declaration of Apple TV cache service at a named site, with status caveats.",
        "peering_status_reference": "IX membership status kept separate from cache-hosting and delivery observations.",
    }
    collection = dict(type="InfrastructureEvidenceCollection", schema_version="1.0.0", retrieved_at=DATE,
        scope_note="Apple TV web, artwork and public-preview delivery evidence; no subscriber/live-stream coverage or physical-site total.",
        categories=categories, records=rows)
    validate_collection(collection)
    write_json(output / INFRA, collection)
    write_json((output / INFRA).with_suffix(".report.json"), dict(built_at=DATE, record_count=len(rows),
        category_counts=dict(sorted(Counter(r["category"] for r in rows).items())), physical_site_total=None,
        parser="scripts/update_apple_tv.py", derived_files=csv_target(INFRA)))
    gazetteer = {r[0]: r for r in csv.reader(text("geonames-localities").splitlines(), delimiter="\t")}
    features = []
    for rid, gid, vendor, provider, label in [("sfmix-aec-scl02", "5393015", "apple", "Apple", "SCL02 / Santa Clara"),
                                            ("fastly-pao", "5380748", "fastly", "Fastly", "PAO / Palo Alto")]:
        claim = next(r for r in rows if r["record_id"] == "apple:tv:" + rid)
        r = gazetteer[gid]
        assert r[8] == "US" and r[10] == "CA" and r[7] == "PPL"
        features.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[float(r[5]), float(r[4])]),
            properties=dict(footprint_id=f"footprint:{vendor}:apple-tv:{gid}", provider=provider, vendor_id=vendor,
                service="Apple TV content delivery", locality=r[1], country_code="US", location_precision="city",
                coordinate_method="gazetteer_reference_point", coordinate_crs="EPSG:4326", record_unit="provider_service_locality",
                physical_site_confirmed=False, lifecycle_status="not_assessed", source_record_ids=[],
                source_claim_ids=[claim["record_id"]], source_locality_labels=[label],
                evidence=[{k: claim[k] for k in ("source_url", "raw_source_ref", "source_sha256", "retrieved_at")}],
                gazetteer=dict(geonames_id=gid, feature_code=r[7], admin1=r[10], name=r[1],
                    evidence=evidence("geonames-localities"), license_url="https://creativecommons.org/licenses/by/4.0/"),
                excluded_from_canonical_totals=True)))
    view = dict(type="FeatureCollection", schema_version="1.0.0", built_at=DATE,
                excluded_from_canonical_totals=True, features=features)
    load_validator(REPO_ROOT / "schema/geographic-footprint.schema.json").validate(view)
    write_json(output / VIEW, view)
    write_json((output / VIEW).with_suffix(".report.json"), dict(built_at=DATE, record_count=len(features),
        excluded_from_canonical_totals=True, physical_sites=False,
        input_layers=[dict(layer="infrastructure/apple-tv-delivery", path=INFRA, sha256=sha256(output / INFRA))],
        interpretation="Palo Alto is a sampled Fastly delivery locality; Santa Clara is a host-declared AEC locality with unresolved peering/cache status. City reference points only.",
        derived_files=csv_target(VIEW)))
    network = build_network(output)
    resolutions, peer_match = resolution_review()
    write_json(output / ASSESSMENT, dict(built_at=DATE, service="Apple TV content delivery", scope="public_web_and_preview",
        baseline_manifest=dict(path=repo_ref(BASELINE), sha256=sha256(BASELINE)),
        source_catalog=dict(path=repo_ref(CATALOG), sha256=sha256(CATALOG)),
        infrastructure_assertions_added=len(rows), network_records_added=len(network), locality_points_added=len(features),
        canonical_records_added=0, sampled_master_playlists=masters, advertised_video_cdns=sorted(p[0] for p in CDNS.values()),
        video_renditions_identical=len({source("tv-variant-" + h.split('.')[0])["sha256"] for h in CDNS}) == 1,
        apple_http_peer_geofeed_match=peer_match, delivery_resolution_observations=resolutions,
        limitations=["One execution environment with unverified physical vantage; public recursive DNS has a separate unknown vantage.",
            "Two US-storefront previews of one show; no paid episode, live sport, or global reachability census.",
            "No video segments, playback sessions, DRM licenses or authenticated endpoints were requested.",
            "Akamai ZZZ is unmapped; Apple cache names are retained as labels, not decoded into facility coordinates.",
            "Apple HTTP peer is outside the Apple geofeed. Resolver-only Chicago matches do not locate that HTTP connection.",
            "SFMIX site declaration does not establish that the sampled peer resides at SCL02. Inactive AS31128 IX membership is not proof of inactive AS40271 cache service.",
            "S3-style x-amz headers do not establish AWS hosting; Apple object-store headers also occur in the same responses.",
            "All ASN714/6185 facilities, global Fastly/Akamai POP lists, and country storefronts are excluded from TV deployment counts."],
        source_review_only={"apple-enterprise-network": "General Apple network requirements, not TV-specific geography.",
            "apple-cdn-engineer": "Retrieved application shell does not retain the indexed job description; no six-platform claim admitted.",
            "apple-cdn-jobs-list": "Retrieved results do not retain the target role; no indexed snippet promoted to dataset evidence.",
            "apple-aec-program": "Program definition only; specific host and TV evidence comes from SFMIX and observed manifests."},
        next_evidence=["Repeat the public-manifest and response-header method from known Indian, Gulf, Russian and other access networks, retaining observer ASN, time and region.",
            "For authorized subscriber or live-sport sessions, retain sanitized CDN hostnames, response headers and public metadata; exclude cookies, tokens, licenses and media bodies.",
            "Resolve SFMIX cache/peering status and obtain an explicit IP-to-site mapping before promoting a physical location.",
            "Use provider-maintained POP-code maps or host declarations before decoding Apple cache labels or admitting CDN facilities."]))
    print(f"Apple TV: {len(rows)} assertions, {len(network)} routing samples, {len(features)} locality reference points")


if __name__ == "__main__":
    main()
