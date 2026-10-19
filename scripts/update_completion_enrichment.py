#!/usr/bin/env python3
"""Build scoped follow-up assertions, locality views and a complete disposition ledger."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from functools import lru_cache
import io
import html
import json
from pathlib import Path
import re
import subprocess
import zipfile

from capture_completion_review import ROOT as RAW, DATE, TAG
import geography_enrichment_common as geography
from location_common import REPO_ROOT, load_validator, repo_ref, sha256, slug, write_json
from network_common import write_network_layer
from update_infrastructure import validate_collection
from update_network import build_ripestat_records

BASELINE = REPO_ROOT / f"data/raw/repository/manifest-before-completion.{TAG}.json"
CATALOG = RAW / f"catalog.{TAG}.json"
INFRA = f"data/infrastructure/completion-evidence.{TAG}.json"
VIEW = f"data/enrichment/provider-localities.{TAG}.geojson"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(key):
    item = next(s for s in read(CATALOG)["sources"] if s["source_id"] == key)
    if item["result"] != "retrieved" or sha256(REPO_ROOT / item["path"]) != item["sha256"]:
        raise ValueError(f"Unavailable or changed source: {key}")
    return item


def evidence(key):
    s = source(key)
    return dict(source_id=key, source_url=s["source_url"], raw_source_ref=s["path"],
                source_sha256=s["sha256"], source_published_at=s.get("source_published_at"),
                source_updated_at=s.get("source_updated_at"), retrieved_at=s["retrieved_at"])


@lru_cache
def pdf_pages(key):
    return subprocess.check_output(["pdftotext", "-raw", str(REPO_ROOT / source(key)["path"]), "-"],
                                   text=True).split("\f")


def guard_pdf(key, page, *tokens):
    text = re.sub(r"\s+", "", pdf_pages(key)[page - 1])
    for token in tokens:
        if re.sub(r"\s+", "", token) not in text:
            raise ValueError(f"PDF assertion absent: {key} page {page}: {token}")


def record(key, identifier, category, name, provider, country, properties, *,
           unit="assertion", scope="provider_declared", relationships=(), parties=None, confidence="high"):
    e = evidence(key)
    return dict(record_id=identifier, category=category, unit=unit, name=name, provider=provider,
                parties=parties or [{"name": provider, "role": "declared_provider"}],
                country_codes=[country], country_scope="explicit_source_geography",
                lifecycle_status="unknown", source_scope=scope,
                **{k: v for k, v in e.items() if k != "source_id"}, confidence=confidence,
                geometry=None, spatial_representation="none", relationships=list(relationships),
                properties={"physical_site_count_not_asserted": True, **properties})


# Reviewed rows from the environmental-approval table, physical PDF pages 105–106.
# Phase ranges remain grouped exactly as disclosed; an approval is not operation.
PROJECTS = [
    ("donghuayuan-1-4", "东花园 1 至 4 期", "河北秦淮数据有限公司", "河北秦淮", 105, "怀环审（2017）45号", "2017-12-01"),
    ("donghuayuan-5-6", "东花园 5 至 6 期", "怀来斯达歌数据有限公司", "斯达歌", 105, "张行审字[2023]147号", "2023-04-17"),
    ("cunrui-1", "存瑞 1 期", "河北秦淮数据有限公司", "河北秦淮", 105, "张行审立字[2019]566号", "2019-05-27"),
    ("cunrui-2", "存瑞 2 期", "怀来斯达惠数据有限公司", "斯达惠", 105, "张行审字[2022]330号", "2022-12-05"),
    ("cunrui-3", "存瑞 3 期", "怀来斯达俊数据有限公司", "斯达俊", 105, "张行审字（2023）338号", "2023-09-01"),
    ("cunrui-4", "存瑞 4 期", "怀来斯达皓数据有限公司", "斯达", 105, "张行审字（2023）339号", "2023-09-01"),
    ("sangyuan-1", "桑园 1 期", "河北秦淮数据有限公司", "河北秦淮", 106, "张行审立字[2019]565号", "2019-05-27"),
    ("sangyuan-2", "桑园 2 期", "怀来斯达智数据科技有限公司", "斯达智", 106, "张行审字[2023]156号", "2023-04-25"),
    ("sangyuan-3", "桑园 3 期", "怀来斯达昕数据有限公司", "斯达昕", 106, "怀行审建环字[2026]4号", "2026-03-16"),
    ("nantong-1", "南通 1 期", "江苏秦淮数据科技有限公司", "江苏秦淮", 106, "201832061100000130", "2018-06-05"),
    ("nantong-2", "南通 2 期", "江苏思达歌数据科技有限公司", "江苏思达歌", 106, "201832061100000131", "2018-06-05"),
    ("lingqiu-1-2", "灵丘 1、2 期", "大同秦淮数据有限公司", "大同秦淮", 106, "灵环函〔2019〕63号", "2019-07-09"),
    ("lingqiu-3", "灵丘 3 期", "大同秦淮数据有限公司", "大同秦淮", 106, "灵环函〔2020〕36号", "2020-06-17"),
    ("lingqiu-4", "灵丘 4 期", "大同秦淮数据有限公司", "大同秦淮", 106, "灵环函〔2020〕59号", "2020-08-21"),
    ("lingqiu-5-7", "灵丘 5 至 7 期", "大同秦淮数据有限公司", "大同秦淮", 106, "无需办理环评手续", "2022-09-02"),
    ("lingqiu-8-13", "灵丘 8 至 13 期", "大同秦淮数据有限公司", "大同秦淮", 106, "无需办理环评手续", "2022-08-22"),
    ("headquarters-1", "总部基地 1 期", "怀来斯达科数据有限公司", "斯达科", 106, "张行审字[2020]163号", "2020-03-11"),
    ("headquarters-2", "总部基地 2 期", "怀来斯达东数据有限公司", "斯达东", 106, "张行审立字[2022]331号", "2022-12-05"),
    ("headquarters-3", "总部基地 3 期", "怀来斯达华数据有限公司", "斯达华", 106, "张行审字[2023]260号", "2023-06-20"),
    ("headquarters-4", "总部基地 4 期", "怀来斯达铎数据有限公司", "斯达铎", 106, "张行审字[2024]22号", "2024-01-18"),
    ("headquarters-5", "总部基地 5 期", "怀来斯达琪数据有限公司", "斯达琪", 106, "张行审立字[2024]655号", "2024-10-15"),
]


def chindata():
    rows = []
    key = "chindata-acquisition-legal"
    for ident, label, legal, alias, page, approval, issued in PROJECTS:
        guard_pdf(key, page, alias, approval.removesuffix("号"))
        # Full legal names are verified separately in the disclosure's definitions.
        if legal not in re.sub(r"\s+", "", "".join(pdf_pages(key)[2:4])):
            raise ValueError(f"Legal operator not defined: {legal}")
        props = dict(project_label=label, legal_entity=legal, source_entity_alias=alias,
                     filing_disclosure_date="2026-07-21", document_month="2026-06",
                     approval_or_exemption_as_published=approval, approval_issued_at=issued,
                     pdf_page=page, printed_page=f"2-2-{page-1}",
                     approval_is_selected_reference_not_exhaustive=True,
                     public_site_code=None, code_to_campus_join_status="not_established",
                     source_claim_scope="legal_opinion_reporting_project_approvals",
                     operation_not_inferred_from_approval=True)
        rows.append(record(key, f"chindata:project_reference:{ident}", "project_approval_reference", label,
                           "Chindata", "CN", props, unit="project_phase_group", scope="institution_declared",
                           parties=[{"name": legal, "role": "disclosed_project_entity"}]))
    # Site-specific property-title rows, kept separate from grouped project approvals.
    for ident, legal, address, cert, page in [
        ("donghuayuan-machine-room-1", "河北秦淮数据有限公司", "怀来县东花园镇大南辛堡村新建新媒体大数据产业基地一期建设项目机房1", "冀（2023）怀来县不动产权第0002381号", 173),
        ("sangyuan-phase2-machine-room-3", "怀来斯达智数据科技有限公司", "怀来县桑园镇黄营村环首都·桑园云计算产业基地建设项目（二期）项目3幢机房楼", "冀（2024）怀来县不动产权第0005458号", 178),
        ("nantong-keze-8", "江苏秦淮数据科技有限公司", "科泽路8号", "苏（2021）南通市不动产权第0068345号", 178),
        ("nantong-keze-8-building3", "江苏思达歌数据科技有限公司", "科泽路8号3幢", "苏（2024）南通市不动产权第0005308号", 178),
    ]:
        guard_pdf(key, page, address, cert)
        rows.append(record(key, f"chindata:property_reference:{ident}", "property_title_reference", address,
                           "Chindata", "CN", dict(address_as_published=address, title_number=cert,
                           pdf_page=page, printed_page=f"2-2-{page-1}", legal_entity=legal,
                           public_site_code=None, operation_not_inferred_from_property_title=True),
                           unit="property_title", scope="institution_declared",
                           parties=[{"name": legal, "role": "disclosed_title_holder"}]))
    supplement = "chindata-acquisition-supplement"
    for ident, label, page, claim in [
        ("sangyuan-3", "桑园3期", 69, "Construction not complete; approvals in progress"),
        ("qingyang-1", "庆阳1期", 69, "Construction not complete; approvals in progress"),
        ("lingqiu-9", "灵丘9期", 71, "Built but not fully commissioned; some equipment installation and energy acceptance remain"),
    ]:
        guard_pdf(supplement, page, label, "尚未建设完毕" if page == 69 else "未完全投运")
        rows.append(record(supplement, f"chindata:phase_status_reference:{ident}", "phase_status_disclosure", label,
                           "Chindata", "CN", dict(pdf_page=page, filing_disclosure_date="2026-09-23",
                           document_month="2026-09", disclosed_status=claim, current_operation_not_reassessed=True,
                           public_site_code=None), unit="phase_status", scope="institution_declared"))
    return rows


INDIA = [("Mohali", "6992326"), ("Delhi", "1273294"), ("Jaipur", "1269515"),
         ("Gandhinagar", "1271715"), ("Mumbai", "1275339"), ("Kolkata", "1275004"),
         ("Hyderabad", "1269843"), ("Bengaluru", "1277333"), ("Chennai", "1264527"), ("Kochi", "1273874")]


def tata():
    rows = []
    for city, _ in INDIA:
        guard_pdf("tata-cdn-map", 1, city, "Active CDN PoP", "Planned CDN PoP", "© 2024")
        rows.append(record("tata-cdn-map", f"tata:historical_cdn_city:{slug(city)}", "historical_cdn_city_declaration",
                           city, "Tata Communications", "IN", dict(locality=city, service="tata_cdn",
                           pdf_page=1, marker_status_as_depicted="active", legend_color="green",
                           extraction_method="manual_visual_review_of_provider_map_labels_and_legend",
                           map_copyright_year=2024, claim_as_of=None, publication_date_not_established=True,
                           current_deployment_not_established=True, coordinates_not_digitized_from_map=True),
                           unit="provider_city_declaration"))
    return rows


def other_assertions():
    data = read(REPO_ROOT / source("peeringdb-dx1")["path"])["data"]
    assert len(data) == 1 and data[0]["id"] == 1355 and data[0]["name"] == "Equinix DX1 - Dubai"
    f = data[0]
    rows = [record("peeringdb-dx1", "equinix:facility_address_reference:dx1", "facility_address_registration",
                   f["name"], "Equinix", "AE", dict(facility_code="DX1", registry_id=1355,
                   address_as_published=[f["address1"], f["address2"], f["city"]],
                   registry_updated_at=f["updated"], identity_join_basis="explicit_DX1_facility_code_and_city",
                   registry_is_self_reported=True, cloud_region_building_not_asserted=True,
                   registry_coordinates_not_admitted=True), unit="facility_registration", confidence="medium",
                   relationships=[{"relationship_type": "corroborates_endpoint_identity", "target_record_id": "gulf:interconnect_endpoint:equinix-dx1"}])]
    # The API ignored the name filter and returned a full facility list. Select
    # reviewed IDs and assert their names/countries; never treat every response as a match.
    facilities = {r["id"]: r for r in read(REPO_ROOT / source("peeringdb-mc1")["path"])["data"]}
    for fid, name, country, endpoint in [
        (9339, "Equinix MC1 - Muscat", "OM", "equinix-mc1"),
        (8243, "AWS Bahrain DC52 MMR", "BH", "aws-dc52-manama"),
        (8242, "AWS Bahrain DC53 MMR", "BH", "aws-dc53-manama"),
        (1493, "SmartHub Fujairah", "AE", "etisalat-smarthub-fujairah"),
    ]:
        f = facilities[fid]
        assert f["name"] == name and f["country"] == country
        props = dict(registry_id=fid, address_as_published=[v for v in [f["address1"], f["address2"]] if v],
                     registry_city=f["city"], registry_updated_at=f["updated"],
                     identity_join_basis="explicit_facility_code_or_SmartHub_name_and_country",
                     registry_is_self_reported=True, independent_operator_audit_not_asserted=True,
                     city_label_not_promoted_to_cloud_region=True, registry_coordinates_not_admitted=True,
                     query_filter_not_honored=True, response_selection="reviewed_facility_id_and_exact_name")
        if fid == 1493:
            from bs4 import BeautifulSoup
            text = BeautifulSoup((REPO_ROOT / source("eand-smarthub")["path"]).read_bytes(), "html.parser").get_text(" ", strip=True)
            assert "SmartHub Fujairah" in text and "Etisalat" in text
            props["operator_corroboration"] = evidence("eand-smarthub")
        rows.append(record("peeringdb-mc1", f"gulf:facility_registration_reference:{fid}", "facility_address_registration",
                           name, "Equinix" if fid == 9339 else "Amazon Web Services" if country == "BH" else "Etisalat / e&",
                           country, props, unit="facility_registration", confidence="medium",
                           relationships=[{"relationship_type": "corroborates_endpoint_identity", "target_record_id": "gulf:interconnect_endpoint:" + endpoint}]))
    text = read(REPO_ROOT / source("vnet-q2-2026-extract")["path"])["response"]
    for code in ["N-HB Campus 03", "N-OR Campus 01"]:
        assert code in text and "June 30, 2026" in text
        rows.append(record("vnet-q2-2026-extract", f"vnet:campus_activity_reference:{slug(code)}", "campus_activity_disclosure",
                           code, "VNET", "CN", dict(campus_code=code, claim_as_of="2026-06-30",
                           disclosed_activity="contributed_to_quarterly_increase_in_utilized_capacity",
                           individual_capacity_mw=None, locality=None, address=None,
                           code_abbreviation_not_decoded=True), unit="campus_reference"))
    return rows


def cst_measurements():
    key = "cst-latency-data"
    text = (REPO_ROOT / source(key)["path"]).read_text()
    assert "First Half of 2026" in text and "weighted averages" in text
    match = re.search(r'\bh=(\[\{p:.*?\}\]);function', text)
    if not match:
        raise ValueError("CST measurement-array structure changed")
    # Only JSON-compatible literal data is accepted. Never execute upstream scripts.
    data = json.loads(re.sub(r'([,{])([A-Za-z_][A-Za-z_0-9]*):', r'\1"\2":', match[1]))
    names = {a or b: c for a, b, c in re.findall(r'(?:"([\w-]+)"|(\w+)):\{ar:"[^"]+",en:"([^"]+)"\}', text)}
    assert len(data) == 31 and len({d["p"] for d in data}) == 19
    rows = []
    for d in data:
        assert set(d) == {"p", "c", "k", "isp"} and set(d["isp"]) == {"stc", "zain", "mobily", "salam"}
        assert all(type(n) is int and 0 < n < 1000 for n in [d["k"], *d["isp"].values()])
        rows.append(record(key, f"cst:cloud_latency_measurement:{d['p']}-{d['c']}-2026h1", "cloud_access_latency_measurement",
                           f"{names[d['p']]} — {d['c'].title()}", names[d["p"]], "SA",
                           dict(locality=d["c"].title(), provider_label=names[d["p"]], report_period="2026-H1",
                           country_weighted_average_ms=d["k"], telecom_provider_average_ms=d["isp"],
                           measurement_population="Saudi residential FTTH Meqyas probes",
                           aggregation="published weighted averages; weights and individual samples unavailable",
                           measurement_targets_not_published=True, exact_facility_not_identified=True,
                           october_health_not_asserted=True, dashboard_evidence=evidence("cst-latency-dashboard")),
                           unit="provider_city_latency_aggregate", scope="institution_declared"))
    return rows


def external_ids():
    baseline = read(BASELINE)
    ids = set()
    for layer in baseline["layers"]:
        ids.update(f["properties"]["record_id"] for f in read(REPO_ROOT / layer["files"]["geojson"]["path"])["features"])
    for layer in baseline["infrastructure_evidence_layers"]:
        ids.update(r["record_id"] for r in read(REPO_ROOT / layer["files"]["json"]["path"])["records"])
    return ids


def infrastructure(output):
    rows = sorted(chindata() + tata() + other_assertions() + cst_measurements(), key=lambda r: r["record_id"])
    categories = {
        "project_approval_reference": "A filing's grouped project/phase and legal-entity reference; not a site count or operation finding.",
        "property_title_reference": "A disclosed property title and address; not proof of current data-center operation.",
        "phase_status_disclosure": "A dated phase-specific construction/commissioning disclosure; not a refreshed whole-campus status.",
        "historical_cdn_city_declaration": "A historical map's provider/city membership; not a current building inventory.",
        "facility_address_registration": "A self-reported registry address linked by an explicit facility code.",
        "campus_activity_disclosure": "A named campus code with reported activity at a specified reporting date.",
        "cloud_access_latency_measurement": "A published provider/city latency aggregate from residential FTTH measurements; not an exact site.",
    }
    collection = dict(type="InfrastructureEvidenceCollection", schema_version="1.0.0", retrieved_at=DATE,
                      scope_note="Independent dated assertions; no new physical-site total, public-code alias or current operation inferred.",
                      categories=categories, records=rows)
    validate_collection(collection, external_record_ids=external_ids())
    write_json(output / INFRA, collection)
    report = dict(built_at=DATE, record_count=len(rows), category_counts=dict(sorted(Counter(r["category"] for r in rows).items())),
                  physical_site_total=None, parser="scripts/update_completion_enrichment.py",
                  derived_files={"csv": {"path": INFRA.replace(".json", ".csv"), "source": INFRA,
                                        "generator": "make " + INFRA.replace(".json", ".csv")}})
    write_json((output / INFRA).with_suffix(".report.json"), report)
    return rows


def footprints(output, rows):
    gaz = geography.source("geonames-cities15000")
    with zipfile.ZipFile(REPO_ROOT / gaz["path"]) as archive:
        places = {r[0]: r for r in csv.reader(io.StringIO(archive.read("cities15000.txt").decode()), delimiter="\t")}
    # The selected GeoNames IDs were reviewed for country, populated-place type and subdivision.
    selections = [("tata", "Tata Communications", "tata_cdn", city, "IN", gid,
                   [], [f"tata:historical_cdn_city:{slug(city)}"], "tata-cdn-map") for city, gid in INDIA]
    selections += [
        ("huawei", "Huawei Cloud", "huawei_cloud", "Wuhu", "CN", "1791236", ["huawei:cloud_region:cn-east-4"], [], "huawei-chinese-global"),
        ("tencent", "Tencent Cloud", "tencent_cloud", "Riyadh", "SA", "108410", ["tencent:cloud_region:me-saudi-arabia"], [], "tencent-cls-regions"),
        ("chindata", "Chindata", "chindata_colocation", "Nantong", "CN", "1799722", [],
         ["chindata:project_reference:nantong-1", "chindata:project_reference:nantong-2"], "chindata-acquisition-legal"),
    ]
    huawei = html.unescape((REPO_ROOT / source("huawei-chinese-global")["path"]).read_text())
    assert re.search(r'"tip"\s*:\s*"站点所在城市：芜湖"\s*,\s*"regionName"\s*:\s*"cn-east-4"', huawei)
    from bs4 import BeautifulSoup
    tencent = BeautifulSoup((REPO_ROOT / source("tencent-cls-regions")["path"]).read_bytes(), "html.parser")
    assert any([c.get_text(" ", strip=True) for c in tr.find_all("td")] == ["Riyadh", "me-saudi-arabia"] for tr in tencent.find_all("tr"))
    features = []
    ids = {r["record_id"] for r in rows}
    for vendor, provider, service, city, country, gid, records, claims, key in selections:
        r = places[gid]
        assert r[1] == city and r[6] == "P" and r[8] == country and set(claims) <= ids
        if city == "Nantong":
            assert r[10:12] == ["04", "3206"]  # Jiangsu, not the Chongqing namesake.
        features.append(dict(type="Feature", geometry=dict(type="Point", coordinates=[float(r[5]), float(r[4])]), properties=dict(
            footprint_id=f"{vendor}:locality:{service}:{gid}", vendor_id=vendor, provider=provider, service=service,
            locality=city, country_code=country, location_precision="city", coordinate_method="gazetteer_reference_point",
            coordinate_crs="EPSG:4326", record_unit="provider_service_locality", physical_site_confirmed=False,
            lifecycle_status="not_assessed", source_record_ids=records, source_claim_ids=claims,
            source_locality_labels=[city], evidence=[evidence(key)], excluded_from_canonical_totals=True,
            gazetteer=dict(geonames_id=gid, name=r[1], feature_code=r[7], admin1=r[10],
                           evidence=geography.evidence("geonames-cities15000"), license_url="https://creativecommons.org/licenses/by/4.0/"))))
    collection = dict(type="FeatureCollection", schema_version="1.0.0", built_at=DATE,
                      excluded_from_canonical_totals=True, features=sorted(features, key=lambda f: f["properties"]["footprint_id"]))
    load_validator(REPO_ROOT / "schema/geographic-footprint.schema.json").validate(collection)
    write_json(output / VIEW, collection)
    layers = read(BASELINE)["layers"]
    report = dict(built_at=DATE, record_count=len(features), excluded_from_canonical_totals=True,
                  input_layers=[{"layer": l["layer"], **l["files"]["geojson"]} for l in layers if l["layer"] in {"huawei/regions", "tencent/regions-and-zones"}],
                  assertion_input={"path": INFRA, "sha256": sha256(output / INFRA)},
                  historical_tata_point_count=10, resolved_previously_held_record_count=2,
                  interpretation="Supplement to prior views; Tata points are historical map declarations, all geometry is locality reference geometry.",
                  derived_files={"csv": {"path": VIEW.replace(".geojson", ".csv"), "source": VIEW,
                                        "generator": "make " + VIEW.replace(".geojson", ".csv")}})
    write_json((output / VIEW).with_suffix(".report.json"), report)
    return collection


def routing(output):
    prefixes = read(REPO_ROOT / f"data/network/gulf-provider-prefixes.{TAG}.json")["records"]
    raw = REPO_ROOT / source("gulf-routing-sample")["path"]
    rows, report = build_ripestat_records(paths={"ripestat": raw}, retrieved_at=DATE, prefix_records=prefixes,
                                          write_source_provenance=False)
    by_id = {r["record_id"]: r for r in prefixes}
    for row in rows:
        p = by_id[row["properties"]["provider_prefix_record_id"]]["properties"]
        row["properties"].update(region_id=p["region_id"], network_border_group=p.get("network_border_group"),
                                 physical_location_not_asserted=True, service_health_not_asserted=True)
    report.update(sample_policy="One lowest-address declared prefix per Gulf region, border group and available IP family; AWS AMAZON scope only. One address per prefix; no active probes.",
                  missing_muscat_ipv6_reason="No retained AMAZON IPv6 declaration for the Muscat border group",
                  latency_not_measured=True)
    write_network_layer(records=rows, layer_name="gulf-routing-review", retrieved_at=DATE,
                        parser_name="scripts/update_completion_enrichment.py", output_root=output, extra_report=report)
    return rows


def ledger(output, rows, view, network):
    from bs4 import BeautifulSoup
    yandex = BeautifulSoup((REPO_ROOT / source("yandex-incident-review")["path"]).read_bytes(), "html.parser").get_text(" ", strip=True)
    assert "Обновлено 11.10.2026" in yandex
    assert all(t in yandex for t in ["Сасово", "Владимире", "Калуге"])
    for key in ["jio-cdn-datasheet", "jio-cdn-brochure"]:
        assert "Managed" in "".join(pdf_pages(key)) and "CDN" in "".join(pdf_pages(key))
    run_path = REPO_ROOT / f"data/raw/repository/gulf-hosted-run.{TAG}.json"
    jobs_path = REPO_ROOT / f"data/raw/repository/gulf-hosted-jobs.{TAG}.json"
    run, jobs = read(run_path), read(jobs_path)
    assert run["conclusion"] == "success" and run["event"] == "push"
    assert jobs["jobs"] and all(j["conclusion"] == "success" for j in jobs["jobs"])
    tasks = []

    def task(identifier, status, result, release, keys=()):
        tasks.append(dict(task_id=identifier, disposition=status, outcome=result,
                          additional_evidence_required=release, source_ids=list(keys), reviewed_at=DATE))

    task("chindata-project-crosswalk", "implemented", "21 phase-group/legal-entity references, four property titles, three later phase-status disclosures and Nantong locality added.", None,
         ["chindata-acquisition-legal", "chindata-acquisition-supplement"])
    task("chindata-public-site-codes", "evidence_limited", "All nine H/W identities retained; filings do not explicitly equate them with named campus phases.",
         "An operator or filing explicitly connecting each public code to a named campus/phase; an address/coordinate source for any precise geometry.")
    task("china-held-localities", "implemented_with_evidence_limits", "All 24 holds dispositioned: Wuhu and Riyadh resolved; two multi-region containers excluded; 20 remain broader than city precision or lack an explicit identity.",
         "City-specific provider statements for unresolved region/pool IDs; administrative or metro labels alone remain at their published precision.", ["huawei-chinese-global", "tencent-cls-regions"])
    task("china-operator-and-carrier-directories", "implemented_with_evidence_limits", "VNET campus-code disclosures added. The 31-vendor cohort is reconciled with prior scoped evidence. GDS download remains unavailable; Mobile/Unicom consolidated public ECS identities remain unestablished.",
         "Accessible dated operator site tables and public ECS region identifiers; customer-only console access is not assumed.", ["vnet-q2-2026-extract", "gds-portfolio-presentation", "gds-portfolio-extract", "unicom-redis-regions"])
    task("tata-indian-cdn-cities", "implemented", "Ten Indian city declarations from the visually reviewed map and ten locality points added; current operation is unknown.",
         "A newer dated deployment directory is needed to refresh historical claims.", ["tata-cdn-map", "tata-cdn-map-landing"])
    task("jio-deployment-list", "evidence_limited", "Product page, linked datasheet and brochure reviewed; they describe CDN service but contain no itemized deployment-city list.",
         "A named, dated Jio CDN deployment directory or equivalent host/operator statement.", ["jio-cdn-product", "jio-cdn-datasheet", "jio-cdn-brochure"])
    task("apple-aec-attribution", "evidence_limited", "AEC program reference reconfirmed. ASN/TLS classifications and Apple DNS points cannot identify AEC installations.",
         "Endpoint-specific AEC classification or explicit Apple/host deployment evidence; the published ASN lists contain neither endpoint IPs nor certificate roles.", ["apple-aec-program"])
    task("gulf-endpoint-addresses", "implemented_with_evidence_limits", "Five named endpoint registrations linked; DX1 has a building reference and MC1 a district-level address. Every other endpoint has a recorded identity/address disposition.",
         "Explicit facility-code joins for ambiguous operator/city labels and street/building evidence before precise point admission.", ["peeringdb-dx1", "peeringdb-mc1", "eand-smarthub", "equinix-sustainability-2025"])
    task("gulf-routing-rpki", "implemented", "13 prefix samples yield 12 observed routes, one no-route response and 12 valid RPKI results. Muscat has an IPv4 sample; no eligible IPv6 declaration exists in the retained feed.", None, ["gulf-routing-sample"])
    task("gulf-passive-latency", "implemented", "31 Saudi provider/city aggregates retained from the regulator's first-half-2026 FTTH measurement report, including Oracle Riyadh and Jeddah.",
         "Public target IPs and individual samples would be needed for endpoint joins or independent measurement replay; these aggregates do not assess October health.", ["cst-latency-dashboard", "cst-latency-data"])
    task("aws-muscat-fujairah-status", "awaiting_provider_update", "Muscat routing does not resolve the missing Local Zone listing. SmartHub Fujairah presence does not reconfirm a CloudFront deployment.",
         "Explicit AWS service-status or current product-directory statements; do not infer retirement from absence or activity from unrelated infrastructure.")
    task("aws-saudi-core-region", "awaiting_provider_update", "The December 2026 launch plan remains a plan. Hosted monitoring and the existing launch-review gate are active.",
         "An explicit AWS launch announcement plus published region and stable AZ identifiers.")
    task("russia-yandex-status", "evidence_limited", "The re-fetched incident page still says updated October 11. No recovery claim or lifecycle refresh is admitted.",
         "A newer explicit operator update for Sasovo, Vladimir and Kaluga; cloud service health alone does not prove facility recovery.", ["yandex-incident-review"])
    task("russia-evolution-parent", "evidence_limited", "The additional third-zone announcement does not publish a parent-region identifier. Existing three zones keep unresolved parent identity.",
         "A Cloud.ru region directory or explicit region-to-zone association, rather than inference from an AZ definition or datacenter name.", ["cloudru-third-zone"])
    task("crypto-grinex-origin", "source_unavailable", "The candidate Grinex domain again returns HTTP 403. Previously sourced exchange identity and application DNS evidence remain separate; no origin-hosting claim is added.",
         "Accessible first-party domain identity followed by endpoint evidence; a domain label, CDN address or another exchange's infrastructure does not establish Grinex hosting.", ["grinex-identity-review"])
    task("hosted-source-review", "implemented", "First hosted run succeeded after the authorized monitoring push; weekly schedule remains active.", None)

    resolved = {rid for f in view["features"] for rid in f["properties"]["source_record_ids"]}
    containers = {"qiniu:cloud_resource_pool:pool-1", "qiniu:cloud_resource_pool:pool-3"}
    held = []
    for old in read(REPO_ROOT / f"data/china/provider-localities.{TAG}.report.json")["held_records"]:
        r = dict(old)
        rid = r["record_id"]
        r["disposition"] = "resolved_in_supplement" if rid in resolved else "excluded_multi_region_container" if rid in containers else "broader_than_city_precision" if r["source_locality"] else "explicit_city_identity_not_established"
        r["original_reason"] = r.pop("reason")
        held.append(r)
    old_endpoints = [r for r in read(REPO_ROOT / f"data/infrastructure/gulf-cloud-connectivity.{TAG}.json")["records"] if r["category"] == "interconnect_endpoint_reference"]
    refs = {rel["target_record_id"]: r for r in rows if r["category"] == "facility_address_registration" for rel in r["relationships"]}
    endpoints = []
    for r in old_endpoints:
        ref = refs.get(r["record_id"])
        endpoints.append(dict(record_id=r["record_id"], name=r["name"],
            disposition="registry_identity_correlated" if ref else "explicit_facility_join_not_established",
            corroboration_record_id=ref["record_id"] if ref else None,
            address_disposition="building_reference" if ref and ref["record_id"] == "equinix:facility_address_reference:dx1" else "district_reference" if ref and ref["properties"].get("registry_id") == 9339 else "no_verified_address",
            geometry_admitted=False))
    cohort = []
    additions = {"chindata": "project/phase, property and Nantong evidence", "huawei": "Wuhu locality and Saudi latency report",
                 "tencent": "Riyadh locality", "vnet": "two campus-code activity disclosures"}
    for vendor in read(REPO_ROOT / f"data/china/geography-enrichment.{TAG}.json")["vendors"]:
        cohort.append(dict(vendor_id=vendor["vendor_id"], name=vendor["name"],
                           disposition="supplement_added" if vendor["vendor_id"] in additions else "prior_scoped_evidence_preserved",
                           supplement=additions.get(vendor["vendor_id"]), prior_source_ids=vendor["existing_review_source_ids"],
                           prior_assessment=f"data/china/geography-enrichment.{TAG}.json"))
    payload = dict(built_at=DATE, baseline_manifest={"path": repo_ref(BASELINE), "sha256": sha256(BASELINE)},
                   source_catalog={"path": repo_ref(CATALOG), "sha256": sha256(CATALOG)},
                   scope="Completion review of the authorized enrichment plans; evidence limitations remain explicit and are not marked resolved.",
                   canonical_records_added=0, canonical_records_changed=0, infrastructure_assertions_added=len(rows),
                   locality_points_added=len(view["features"]), network_records_added=len(network), tasks=tasks,
                   task_disposition_counts=dict(sorted(Counter(t["disposition"] for t in tasks).items())),
                   china_held_record_dispositions=held, china_vendor_cohort=cohort, gulf_endpoint_dispositions=endpoints,
                   yandex_status_source_updated_at="2026-10-11",
                   workflow_receipt={"url": run["html_url"], "run_id": run["id"], "head_sha": run["head_sha"],
                                     "conclusion": run["conclusion"], "run": {"path": repo_ref(run_path), "sha256": sha256(run_path)},
                                     "jobs": {"path": repo_ref(jobs_path), "sha256": sha256(jobs_path)}},
                   unperformed_active_measurements="No new RIPE Atlas jobs, scans, paid measurements, customer-console queries or exchange transactions; only public evidence and read-only APIs.")
    write_json(output / f"data/enrichment/completion-review.{TAG}.json", payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    assert sha256(BASELINE) == read(BASELINE.with_suffix(".json.provenance.json"))["sha256"]
    rows = infrastructure(args.output_root)
    view = footprints(args.output_root, rows)
    network = routing(args.output_root)
    ledger(args.output_root, rows, view, network)
    print(json.dumps({"assertions": len(rows), "locality_points": len(view["features"]), "network_records": len(network)}))


if __name__ == "__main__":
    main()
