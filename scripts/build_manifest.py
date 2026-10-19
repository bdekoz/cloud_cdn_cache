#!/usr/bin/env python3
"""Build a consolidated manifest without relabeling older retained snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from location_common import REPO_ROOT, SCHEMA_CONTRACT_VERSION, SCHEMA_PATH, repo_ref, retrieval_tag, sha256, write_json
from network_common import NETWORK_SCHEMA_PATH, NETWORK_SCHEMA_VERSION


BASELINE_TAG = "20260804"
HYPERSCALER_TAG = "20260805"
NETWORK_TAG = "20260805"
GOOGLE_REFRESH_TAG = "20261011"
RUSSIA_REVIEW_TAG = "20261011"
INFRASTRUCTURE_TAG = "20261011"
CHINA_REVIEW_TAG = "20261011"
CHINA_IMPLEMENTATION_TAG = "20261011"
CDN_COMPARISON_TAG = "20261019"
CARTOGRAPHY_RESTORATION_TAG = "20261019"
RUSSIA_ENRICHMENT_REVIEW_TAG = "20261019"
RUSSIA_IMPLEMENTATION_TAG = "20261019"
GEOGRAPHY_ENRICHMENT_TAG = "20261019"
GULF_ENRICHMENT_TAG = "20261019"
APPLE_TV_TAG = "20261019"
RUSSIA_LOCATION_LAYERS = (
    "yandex/regions-and-zones", "yandex/cdn-cities", "selectel/russian-hierarchy",
    "cloudru/advanced-regions-and-zones", "cloudru/evolution-zones", "ixcellerate/data-centers",
)

BASELINE_LAYERS = (
    "google/edge",
    "google/data-centers",
    "cloudflare/edge",
    "microsoft/front-door",
    "microsoft/front-door-codes",
    "aws/cloudfront",
    "aws/local-zones",
    "fastly/pops",
    "cachefly/locations",
    "alibaba/regions-and-zones",
    "tencent/regions-and-zones",
    "baidu/regions-and-zones",
    "huawei/mainland-regions",
    "volcano/regions-and-zones",
    "kingsoft/mainland-regions-and-zones",
    "jd/mainland-regions-and-zones",
    "tianyi/vpc-resource-pools",
    "chindata/data-centers",
    "observations/cdn-mapping",
)

HYPERSCALER_LAYERS = (
    "coreweave/regions-and-zones",
    "aws/regions-and-zones",
    "google/cloud-regions-and-zones",
    "microsoft/cloud-regions",
    "oracle/cloud-regions",
    "ibm/regions-and-zones",
    "ibm/classic-data-centers",
    "meta/data-centers",
)

CURRENT_OBSERVATION_LAYERS = (
    "observations/cdn-mapping-cities",
)

NETWORK_EVIDENCE_LAYERS = (
    "provider-prefixes",
    "ripestat-routing",
    "peeringdb-relationships",
)

VIEW_NAMES = {
    "alibaba/mainland-regions-and-zones": "alibaba/regions-and-zones",
    "tencent/mainland-regions-and-zones": "tencent/regions-and-zones",
    "tencent/mainland-specialized-regions-and-zones": "tencent/regions-and-zones",
    "baidu/mainland-regions-and-zones": "baidu/regions-and-zones",
    "volcano/mainland-regions-and-zones": "volcano/regions-and-zones",
}

ASSESSMENT_NAMES = (
    "china/provider-assessment",
    "china-edge/provider-assessment",
    "china-colocation/operator-assessment",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", default=date.today().isoformat())
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def layer_manifest(layer: str, tag: str) -> dict[str, Any]:
    base = REPO_ROOT / "data" / f"{layer}.{tag}"
    csv_path = Path(f"{base}.csv")
    geojson_path = Path(f"{base}.geojson")
    report_path = Path(f"{base}.report.json")
    collection = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = collection["features"]
    rows = [feature["properties"] for feature in features]
    sources = {}
    for row in rows:
        key = (row["raw_source_ref"], row["source_sha256"], row["source_url"])
        sources[key] = {
            "raw_source_ref": key[0],
            "sha256": key[1],
            "source_url": key[2],
            "source_published_at": row["source_published_at"],
        }
        if row.get("properties", {}).get("source_updated_at"):
            sources[key]["source_updated_at"] = row["properties"]["source_updated_at"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for source in report.get("enrichment_sources", []):
        key = (source["raw_source_ref"], source["source_sha256"], source["source_url"])
        sources[key] = {
            "raw_source_ref": key[0], "sha256": key[1], "source_url": key[2],
            "source_published_at": source.get("source_published_at"), "source_scope": source["source_scope"],
        }
    return {
        "coordinate_methods": dict(sorted(Counter(row["coordinate_method"] for row in rows).items())),
        "derived_files": {
            "csv": {
                "generator": f"make {repo_ref(csv_path)}",
                "path": repo_ref(csv_path),
                "source": repo_ref(geojson_path),
            }
        },
        "entity_types": dict(sorted(Counter(row["entity_type"] for row in rows).items())),
        "files": {
            "geojson": {"path": repo_ref(geojson_path), "sha256": sha256(geojson_path)},
            "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)},
        },
        "geometry_null": sum(feature["geometry"] is None for feature in features),
        "layer": layer,
        "providers": sorted({row["provider"] for row in rows}),
        "record_count": len(rows),
        "snapshot_tag": tag,
        "retrieved_at": sorted({row["retrieved_at"] for row in rows}),
        "schema_versions": sorted({row["schema_version"] for row in rows}),
        "services": sorted({row["service"] for row in rows}),
        "source_scopes": sorted({row["source_scope"] for row in rows}),
        "sources": sorted(sources.values(), key=lambda source: source["raw_source_ref"]),
    }


def assessment_manifest(name: str, tag: str) -> dict[str, str]:
    path = REPO_ROOT / "data" / f"{name}.{tag}.json"
    return {"path": repo_ref(path), "sha256": sha256(path)}


def comparison_manifest(name: str, tag: str) -> dict[str, Any]:
    path = REPO_ROOT / "data" / f"{name}.{tag}.json"
    report_path = path.with_suffix(".report.json")
    collection = json.loads(path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "layer": name, "snapshot_tag": tag, "built_at": collection["built_at"],
        "view_of": collection["view_of"], "selection": collection["selection"],
        "record_count": len(collection["records"]), "record_unit": "distinct_asn",
        "excluded_from_canonical_totals": True, "sources": collection["sources"],
        "files": {"json": {"path": repo_ref(path), "sha256": sha256(path)},
                  "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)}},
        "derived_files": report["derived_files"],
    }


def network_layer_manifest(layer: str, tag: str) -> dict[str, Any]:
    base = REPO_ROOT / "data/network" / f"{layer}.{tag}"
    json_path = Path(f"{base}.json")
    csv_path = Path(f"{base}.csv")
    report_path = Path(f"{base}.report.json")
    collection = json.loads(json_path.read_text(encoding="utf-8"))
    records = collection["records"]
    sources = {}
    for record in records:
        key = (record["raw_source_ref"], record["source_sha256"], record["source_url"])
        sources[key] = {
            "raw_source_ref": key[0],
            "sha256": key[1],
            "source_published_at": record["source_published_at"],
            "source_url": key[2],
        }
    return {
        "derived_files": {
            "csv": {
                "generator": f"make {repo_ref(csv_path)}",
                "path": repo_ref(csv_path),
                "source": repo_ref(json_path),
            }
        },
        "evidence_types": dict(sorted(Counter(record["evidence_type"] for record in records).items())),
        "files": {
            "json": {"path": repo_ref(json_path), "sha256": sha256(json_path)},
            "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)},
        },
        "layer": layer,
        "providers": sorted({record["provider"] for record in records if record["provider"]}),
        "record_count": len(records),
        "retrieved_at": sorted({record["retrieved_at"] for record in records}),
        "schema_versions": sorted({collection["schema_version"]}),
        "services": sorted({record["service"] for record in records if record["service"]}),
        "snapshot_tag": tag,
        "source_scopes": sorted({record["source_scope"] for record in records}),
        "sources": sorted(sources.values(), key=lambda source: (source["raw_source_ref"], source["source_url"])),
        "statuses": dict(sorted(Counter(record["status"] for record in records).items())),
    }


def infrastructure_manifest(layer: str, tag: str, directory: str = "infrastructure") -> dict[str, Any]:
    path = REPO_ROOT / "data" / directory / f"{layer}.{tag}.json"
    collection = json.loads(path.read_text(encoding="utf-8"))
    records = collection["records"]
    sources = {}
    for row in records:
        sources[row["raw_source_ref"]] = {"raw_source_ref": row["raw_source_ref"], "sha256": row["source_sha256"],
                                         "source_url": row["source_url"], "source_published_at": row["source_published_at"],
                                         "source_updated_at": row["source_updated_at"]}
    files = {"json": {"path": repo_ref(path), "sha256": sha256(path)}}
    report = path.with_suffix(".report.json")
    if report.exists():
        files["report"] = {"path": repo_ref(report), "sha256": sha256(report)}
    return {"layer": f"{directory}/{layer}", "snapshot_tag": tag, "schema_version": collection["schema_version"],
            "record_count": len(records), "category_counts": dict(sorted(Counter(row["category"] for row in records).items())),
            "unit_counts": dict(sorted(Counter(row["unit"] for row in records).items())),
            "geometry_null": sum(row["geometry"] is None for row in records), "files": files,
            "sources": [sources[key] for key in sorted(sources)],
            "derived_files": {"csv": {"path": repo_ref(path.with_suffix(".csv")), "source": repo_ref(path),
                                       "generator": f"make {repo_ref(path.with_suffix('.csv'))}"}}}


def application_manifest(tag: str) -> dict[str, Any]:
    path = REPO_ROOT / f"data/applications/crypto-endpoints.{tag}.json"
    report_path = path.with_suffix(".report.json")
    collection = json.loads(path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    sources = {}

    def collect(value):
        if isinstance(value, dict):
            if "source_sha256" in value and "raw_source_ref" in value:
                sources[value["raw_source_ref"]] = value
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(collection)
    return {"layer": "applications/crypto-endpoints", "snapshot_tag": tag,
            "schema_version": collection["schema_version"], "built_at": collection["built_at"],
            "record_count": len(collection["records"]), "entity_count": len(collection["entities"]),
            "record_unit": report["record_unit"], "excluded_from_location_and_network_totals": True,
            "files": {"json": {"path": repo_ref(path), "sha256": sha256(path)},
                      "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)}},
            "sources": [sources[key] for key in sorted(sources)], "derived_files": report["derived_files"]}


def geographic_footprint_manifest(tag: str, layer: str = "china/provider-localities") -> dict[str, Any]:
    path = REPO_ROOT / f"data/{layer}.{tag}.geojson"
    report_path = path.with_suffix(".report.json")
    collection = json.loads(path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {"layer": layer, "snapshot_tag": tag,
        "schema_version": collection["schema_version"], "record_count": len(collection["features"]),
        "record_unit": "provider_service_locality", "excluded_from_canonical_totals": True,
        "physical_sites": False, "input_layers": report["input_layers"],
        "files": {"geojson": {"path": repo_ref(path), "sha256": sha256(path)},
                  "report": {"path": repo_ref(report_path), "sha256": sha256(report_path)}},
        "derived_files": report["derived_files"]}


def main() -> None:
    args = parse_args()
    tag = retrieval_tag(args.retrieved_at)
    output = args.output or REPO_ROOT / "data" / f"manifest.{tag}.json"
    if tag < BASELINE_TAG:
        raise ValueError(f"no consolidated snapshot is defined before {BASELINE_TAG}")
    layer_specs = [(layer, BASELINE_TAG) for layer in BASELINE_LAYERS]
    if tag >= HYPERSCALER_TAG:
        layer_specs.extend((layer, HYPERSCALER_TAG) for layer in HYPERSCALER_LAYERS)
        layer_specs.extend((layer, HYPERSCALER_TAG) for layer in CURRENT_OBSERVATION_LAYERS)
    if tag >= GOOGLE_REFRESH_TAG:
        layer_specs = [
            (layer, GOOGLE_REFRESH_TAG if layer.startswith("google/") else snapshot_tag)
            for layer, snapshot_tag in layer_specs
        ]
    if tag >= RUSSIA_REVIEW_TAG:
        layer_specs.append(("yandex/data-centers", RUSSIA_REVIEW_TAG))
    if tag >= CHINA_IMPLEMENTATION_TAG:
        refreshed = {
            "alibaba/regions-and-zones", "tencent/regions-and-zones", "baidu/regions-and-zones",
            "volcano/regions-and-zones", "kingsoft/mainland-regions-and-zones",
            "jd/mainland-regions-and-zones", "tianyi/vpc-resource-pools", "chindata/data-centers",
            "aws/regions-and-zones",
        }
        layer_specs = [("huawei/regions", CHINA_IMPLEMENTATION_TAG) if layer == "huawei/mainland-regions"
                       else (layer, CHINA_IMPLEMENTATION_TAG if layer in refreshed else snapshot_tag)
                       for layer, snapshot_tag in layer_specs]
        layer_specs.extend((layer, CHINA_IMPLEMENTATION_TAG) for layer in (
            "microsoft/china-cloud-regions", "qiniu/resource-pools-and-regions"))
    if tag >= CARTOGRAPHY_RESTORATION_TAG:
        layer_specs.extend((layer, CARTOGRAPHY_RESTORATION_TAG) for layer in (
            "akamai/legacy-locations", "apple/dns-cities"))
    if tag >= RUSSIA_IMPLEMENTATION_TAG:
        layer_specs.extend((layer, RUSSIA_IMPLEMENTATION_TAG) for layer in RUSSIA_LOCATION_LAYERS)
    if tag >= GEOGRAPHY_ENRICHMENT_TAG:
        layer_specs = [(layer, GEOGRAPHY_ENRICHMENT_TAG if layer == "chindata/data-centers" else snapshot_tag)
                       for layer, snapshot_tag in layer_specs]
    if tag >= GULF_ENRICHMENT_TAG:
        gulf_layers = {"aws/regions-and-zones", "aws/cloudfront", "aws/local-zones", "oracle/cloud-regions"}
        layer_specs = [(layer, GULF_ENRICHMENT_TAG if layer in gulf_layers else snapshot_tag)
                       for layer, snapshot_tag in layer_specs]
    layers = [layer_manifest(layer, snapshot_tag) for layer, snapshot_tag in layer_specs]
    network_layers = []
    if tag >= NETWORK_TAG:
        network_layers = [network_layer_manifest(layer, NETWORK_TAG) for layer in NETWORK_EVIDENCE_LAYERS]
    if tag >= CHINA_IMPLEMENTATION_TAG:
        network_layers.append(network_layer_manifest("china-vendor-evidence", CHINA_IMPLEMENTATION_TAG))
    if tag >= RUSSIA_IMPLEMENTATION_TAG:
        network_layers.extend(network_layer_manifest(layer, RUSSIA_IMPLEMENTATION_TAG)
                              for layer in ("yandex-prefixes", "yandex-routing"))
    if tag >= GULF_ENRICHMENT_TAG:
        network_layers.append(network_layer_manifest("gulf-provider-prefixes", GULF_ENRICHMENT_TAG))
        network_layers.append(network_layer_manifest("gulf-routing-review", GULF_ENRICHMENT_TAG))
    if tag >= APPLE_TV_TAG:
        network_layers.append(network_layer_manifest("apple-tv-routing", APPLE_TV_TAG))
        network_layers.append(network_layer_manifest("apple-aec-candidate-routing", APPLE_TV_TAG))
    views = []
    for view, parent in VIEW_NAMES.items():
        entry = layer_manifest(view, CHINA_IMPLEMENTATION_TAG if tag >= CHINA_IMPLEMENTATION_TAG else BASELINE_TAG)
        entry["view_of"] = parent
        views.append(entry)
    if tag >= CHINA_IMPLEMENTATION_TAG:
        for view, parent in [("alibaba/mainland-specialized-regions-and-zones", "alibaba/regions-and-zones"),
                             ("huawei/mainland-regions", "huawei/regions")]:
            entry = layer_manifest(view, CHINA_IMPLEMENTATION_TAG)
            entry["view_of"] = parent
            views.append(entry)
    if tag >= RUSSIA_REVIEW_TAG:
        view_tag = RUSSIA_IMPLEMENTATION_TAG if tag >= RUSSIA_IMPLEMENTATION_TAG else RUSSIA_REVIEW_TAG
        entry = layer_manifest("russia/locations-and-observations", view_tag)
        entry["view_of"] = ["google/edge", "cloudflare/edge", "cachefly/locations", "observations/cdn-mapping-cities", "yandex/data-centers"]
        if tag >= RUSSIA_IMPLEMENTATION_TAG:
            report = json.loads((REPO_ROOT / f"data/russia/locations-and-observations.{view_tag}.report.json").read_text())
            entry["view_of"] = report["view_of"]
        views.append(entry)
    comparison_sections = {}
    if tag >= CDN_COMPARISON_TAG:
        for view, parent in (("observations/apple-asn", "observations/cdn-mapping"),
                             ("india/cdn-cities", "observations/cdn-mapping-cities")):
            entry = layer_manifest(view, CDN_COMPARISON_TAG)
            entry["view_of"] = parent
            views.append(entry)
        comparison_schema = REPO_ROOT / "schema/cdn-comparison.schema.json"
        comparison_sections = {
            "observation_comparison_schema": {"path": repo_ref(comparison_schema),
                                              "sha256": sha256(comparison_schema), "version": "1.0.0"},
            "observation_comparison_views": [comparison_manifest(name, CDN_COMPARISON_TAG) for name in
                                             ("observations/cdn-asn-comparison", "india/cdn-asn-comparison")],
            "observation_comparison_view_count": 2,
        }
        if tag >= RUSSIA_IMPLEMENTATION_TAG:
            comparison_sections["observation_comparison_schema"]["version"] = "1.1.0"
            comparison_sections["observation_comparison_views"].append(
                comparison_manifest("russia/cdn-asn-comparison", RUSSIA_IMPLEMENTATION_TAG))
            comparison_sections["observation_comparison_view_count"] = len(comparison_sections["observation_comparison_views"])
    assessments = [assessment_manifest(name, BASELINE_TAG) for name in ASSESSMENT_NAMES]
    if tag >= RUSSIA_REVIEW_TAG:
        assessments.extend(assessment_manifest(name, RUSSIA_REVIEW_TAG) for name in ("russia/provider-assessment", "yandex/image-claim-review"))
    if tag >= CHINA_REVIEW_TAG:
        assessments.extend(assessment_manifest(name, CHINA_REVIEW_TAG) for name in (
            "china/vendor-coverage-assessment", "china/enrichment-plan", "china/review-evidence",
        ))
    if tag >= CHINA_IMPLEMENTATION_TAG:
        assessments.extend(assessment_manifest(name, CHINA_IMPLEMENTATION_TAG) for name in (
            "china/legacy-reconciliation", "china/enrichment-implementation"))
    if tag >= CARTOGRAPHY_RESTORATION_TAG:
        assessments.append(assessment_manifest("apple/dns-endpoint-audit", CARTOGRAPHY_RESTORATION_TAG))
    if tag >= RUSSIA_ENRICHMENT_REVIEW_TAG:
        assessments.append(assessment_manifest("russia/enrichment-assessment", RUSSIA_ENRICHMENT_REVIEW_TAG))
    if tag >= RUSSIA_IMPLEMENTATION_TAG:
        assessments.append(assessment_manifest("russia/enrichment-implementation", RUSSIA_IMPLEMENTATION_TAG))
    if tag >= GEOGRAPHY_ENRICHMENT_TAG:
        assessments.extend(assessment_manifest(name, GEOGRAPHY_ENRICHMENT_TAG) for name in (
            "china/geography-enrichment", "chindata/campus-alias-review", "gulf/aws-oracle-coverage"))
    if tag >= GULF_ENRICHMENT_TAG:
        assessments.append(assessment_manifest("gulf/enrichment-implementation", GULF_ENRICHMENT_TAG))
        assessments.append(assessment_manifest("enrichment/completion-review", GULF_ENRICHMENT_TAG))
    if tag >= APPLE_TV_TAG:
        assessments.append(assessment_manifest("apple/tv-delivery-review", APPLE_TV_TAG))
        assessments.append(assessment_manifest("apple/aec-review", APPLE_TV_TAG))
        assessments.append(assessment_manifest("apple/aec-followup", APPLE_TV_TAG))
    quarantine_audit = REPO_ROOT / "data/quarantine/audit.20260804.json"
    infrastructure_sections = {}
    if tag >= INFRASTRUCTURE_TAG:
        infrastructure_schema = REPO_ROOT / "schema/infrastructure-evidence.schema.json"
        infrastructure_layers = [infrastructure_manifest("connectivity", INFRASTRUCTURE_TAG)]
        if tag >= CHINA_IMPLEMENTATION_TAG:
            infrastructure_layers.extend(infrastructure_manifest(name, CHINA_IMPLEMENTATION_TAG) for name in (
                "china-ai-services", "china-facilities-and-portfolios", "china-carrier-links"))
        if tag >= GULF_ENRICHMENT_TAG:
            infrastructure_layers.append(infrastructure_manifest("gulf-cloud-connectivity", GULF_ENRICHMENT_TAG))
            infrastructure_layers.append(infrastructure_manifest("completion-evidence", GULF_ENRICHMENT_TAG))
        if tag >= APPLE_TV_TAG:
            infrastructure_layers.append(infrastructure_manifest("apple-tv-delivery", APPLE_TV_TAG))
            infrastructure_layers.append(infrastructure_manifest("apple-aec-hosts", APPLE_TV_TAG))
            infrastructure_layers.append(infrastructure_manifest("apple-aec-followup", APPLE_TV_TAG))
        infrastructure_view = infrastructure_manifest("russia-connectivity", INFRASTRUCTURE_TAG)
        infrastructure_view["view_of"] = "infrastructure/connectivity"
        infrastructure_sections = {
            "infrastructure_evidence_schema": {"path": repo_ref(infrastructure_schema), "sha256": sha256(infrastructure_schema), "version": "1.0.0"},
            "infrastructure_evidence_layers": infrastructure_layers,
            "infrastructure_evidence_layer_count": len(infrastructure_layers),
            "infrastructure_evidence_record_count": sum(layer["record_count"] for layer in infrastructure_layers),
            "infrastructure_evidence_views": [infrastructure_view],
            "infrastructure_evidence_view_count": 1,
        }
        if tag >= CHINA_IMPLEMENTATION_TAG:
            registry = infrastructure_manifest("registry", CHINA_IMPLEMENTATION_TAG, directory="vendors")
            registry["counted_as_infrastructure"] = False
            infrastructure_sections["vendor_registry"] = registry
            infrastructure_sections["vendor_registry_record_count"] = registry["record_count"]
    application_sections = {}
    location_schema, location_version = SCHEMA_PATH, SCHEMA_CONTRACT_VERSION
    if tag >= RUSSIA_IMPLEMENTATION_TAG:
        location_schema, location_version = REPO_ROOT / "schema/location-v1.3.schema.json", "1.3.0"
        application_schema = REPO_ROOT / "schema/application-endpoint.schema.json"
        application_layer = application_manifest(RUSSIA_IMPLEMENTATION_TAG)
        application_sections = {
            "application_endpoint_schema": {"path": repo_ref(application_schema), "sha256": sha256(application_schema), "version": "1.0.0"},
            "application_endpoint_layers": [application_layer], "application_endpoint_layer_count": 1,
            "application_endpoint_record_count": application_layer["record_count"],
            "application_entity_count": application_layer["entity_count"],
        }
    geographic_sections = {}
    scope_note = "Canonical location counts span unlike provider-declared and observed entity types and are not a physical-site total. Derived views repeat source-layer IDs and network evidence is non-spatial; both are excluded from record_count."
    if tag >= GEOGRAPHY_ENRICHMENT_TAG:
        footprint_schema = REPO_ROOT / "schema/geographic-footprint.schema.json"
        bibliography = REPO_ROOT / f"data/references/bibliography.{GEOGRAPHY_ENRICHMENT_TAG}.json"
        bibliography_doc = REPO_ROOT / f"docs/bibliography.{GEOGRAPHY_ENRICHMENT_TAG}.md"
        geographic_sections = {
            "geographic_footprint_schema": {"path": repo_ref(footprint_schema), "sha256": sha256(footprint_schema), "version": "1.0.0"},
            "geographic_footprint_views": [geographic_footprint_manifest(GEOGRAPHY_ENRICHMENT_TAG)],
            "geographic_footprint_view_count": 1,
            "bibliography": {"files": {"json": {"path": repo_ref(bibliography), "sha256": sha256(bibliography)},
                                       "markdown": {"path": repo_ref(bibliography_doc), "sha256": sha256(bibliography_doc)}},
                             "reference_count": json.loads(bibliography.read_text())["reference_count"]},
        }
        scope_note = scope_note.replace("Derived views", "Derived location views") + " Geographic footprint views group provider/service/locality memberships, use reference-point geometry and are also excluded from canonical totals."
    if tag >= GULF_ENRICHMENT_TAG:
        geographic_sections["geographic_footprint_views"].append(
            geographic_footprint_manifest(GULF_ENRICHMENT_TAG, "gulf/provider-localities"))
        geographic_sections["geographic_footprint_views"].append(
            geographic_footprint_manifest(GULF_ENRICHMENT_TAG, "enrichment/provider-localities"))
        geographic_sections["geographic_footprint_view_count"] = len(geographic_sections["geographic_footprint_views"])
    if tag >= APPLE_TV_TAG:
        geographic_sections["geographic_footprint_views"].append(
            geographic_footprint_manifest(APPLE_TV_TAG, "apple/tv-delivery-localities"))
        geographic_sections["geographic_footprint_views"].append(
            geographic_footprint_manifest(APPLE_TV_TAG, "apple/aec-localities"))
        geographic_sections["geographic_footprint_view_count"] = len(geographic_sections["geographic_footprint_views"])
    write_json(output, {
        **infrastructure_sections,
        **comparison_sections,
        **application_sections,
        **geographic_sections,
        "assessments": assessments,
        "generated_from_retained_snapshots_at": args.retrieved_at,
        "layer_count": len(layers),
        "layers": layers,
        "network_evidence_layer_count": len(network_layers),
        "network_evidence_layers": network_layers,
        "network_evidence_record_count": sum(layer["record_count"] for layer in network_layers),
        "network_evidence_schema": {
            "path": repo_ref(NETWORK_SCHEMA_PATH),
            "sha256": sha256(NETWORK_SCHEMA_PATH),
            "version": NETWORK_SCHEMA_VERSION,
        },
        "record_count": sum(layer["record_count"] for layer in layers),
        "schema": {"path": repo_ref(location_schema), "sha256": sha256(location_schema), "version": location_version},
        "scope_note": scope_note,
        "quarantine": {"audit_path": repo_ref(quarantine_audit), "audit_sha256": sha256(quarantine_audit)},
        "view_count": len(views),
        "views": views,
    })
    print(json.dumps({"layer_count": len(layers), "network_evidence_layer_count": len(network_layers), "network_evidence_record_count": sum(layer["record_count"] for layer in network_layers), "record_count": sum(layer["record_count"] for layer in layers), "view_count": len(views), "output": repo_ref(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
