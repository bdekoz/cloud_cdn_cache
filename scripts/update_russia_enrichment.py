#!/usr/bin/env python3
"""Rebuild the approved Russia enrichment offline from retained evidence."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from location_common import REPO_ROOT, sha256, write_json
from russia_enrichment_common import (BASELINE, DATE, TAG, EXTRA, LOCATION_LAYERS,
    NETWORK_LAYERS, evidence, read, source)
from update_cdn_comparisons import csv_ref
import update_crypto_endpoints
import update_russia_comparison
import update_russia_providers
import update_yandex


def country_view(root: Path):
    source_paths = []
    for layer in read(BASELINE)["layers"]:
        item = layer["files"]["geojson"]
        if sha256(REPO_ROOT / item["path"]) != item["sha256"]:
            raise ValueError("Pre-enrichment canonical snapshot changed")
        source_paths.append((layer["layer"], REPO_ROOT / item["path"], item["path"]))
    source_paths += [(layer, root / f"data/{layer}.{TAG}.geojson", f"data/{layer}.{TAG}.geojson") for layer in LOCATION_LAYERS]
    features, sources, parents = [], [], []
    all_ids = set()
    for layer, path, ref in source_paths:
        collection = read(path)
        for feature in collection["features"]:
            identity = feature["properties"]["record_id"]
            if identity in all_ids:
                raise ValueError(f"Duplicate canonical record ID: {identity}")
            all_ids.add(identity)
        selected = [f for f in collection["features"] if f["properties"]["country_code"] == "RU"]
        if selected:
            sources.append({"path": ref, "sha256": sha256(path)})
            parents.append(layer)
            features.extend(selected)
    features.sort(key=lambda feature: feature["properties"]["record_id"])
    path = f"data/russia/locations-and-observations.{TAG}.geojson"
    write_json(root / path, {"type": "FeatureCollection", "metadata": {
        "built_at": DATE, "view_of": parents, "selection": "country_code=RU",
        "excluded_from_canonical_totals": True, "sources": sources,
        "scope_note": "Mixed geographic units and source ages; not a current operating facility count."}, "features": features})
    report = {"layer": "russia/locations-and-observations", "built_at": DATE,
        "view_of": parents, "selection": "country_code=RU", "view_excluded_from_canonical_totals": True,
        "record_count": len(features), "geometry_null": sum(f["geometry"] is None for f in features),
        "provider_counts": dict(sorted(Counter(f["properties"]["provider"] for f in features).items())),
        "entity_types": dict(sorted(Counter(f["properties"]["entity_type"] for f in features).items())),
        "sources": sources, "generated_files": [path], "derived_files": csv_ref(path)}
    write_json((root / path).with_suffix(".report.json"), report)
    return report


def run(root: Path):
    for module in (update_yandex, update_russia_providers, update_russia_comparison, update_crypto_endpoints):
        module.run(root)
    view = country_view(root)
    layers = [{"layer": layer, "record_count": len(read(root / f"data/{layer}.{TAG}.geojson")["features"])}
              for layer in LOCATION_LAYERS]
    networks = [{"layer": layer, "record_count": len(read(root / f"data/network/{layer}.{TAG}.json")["records"])}
                for layer in NETWORK_LAYERS]
    write_json(root / f"data/russia/enrichment-implementation.{TAG}.json", {
        "implementation_type": "russia_yandex_crypto_enrichment", "built_at": DATE,
        "approved_plan_ref": f"data/russia/enrichment-assessment.{TAG}.json",
        "baseline_manifest": {"path": BASELINE, "sha256": sha256(REPO_ROOT / BASELINE)},
        "prior_canonical_layers_preserved": True, "new_location_layers": layers,
        "new_location_record_count": sum(layer["record_count"] for layer in layers),
        "new_network_layers": networks, "new_network_record_count": sum(layer["record_count"] for layer in networks),
        "ru_view_record_count": view["record_count"], "ru_view_geometry_null": view["geometry_null"],
        "application_endpoint_record_count": len(read(root / update_crypto_endpoints.PATH)["records"]),
        "application_entity_count": len(read(root / update_crypto_endpoints.PATH)["entities"]),
        "ru_registered_comparison_asn_count": len(read(root / f"data/russia/cdn-asn-comparison.{TAG}.json")["records"]),
        "new_source_receipts": {key: source(key) for key in EXTRA},
        "country_normalization": {"city": "Simferopol", "source_country_label": "Russia",
                                  "country_code": "UA", "evidence": evidence("country_policy")},
        "limits": ["Location records have unlike units, unknown coordinates and source-dated lifecycle declarations.",
                   "Yandex incident status remains the October 11 statement; current outage or recovery is not established.",
                   "Evolution zone parents remain unknown; schema 1.3 requires source evidence for missing parent identity.",
                   "Registration country and public DNS endpoints do not establish physical origin hosting.",
                   "The June registration comparison adds no scans or locations. Missing provider IDs are not verified absences.",
                   "Grinex current endpoint identity remains unverified; no inherited Garantex locations."]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    run(parser.parse_args().output_root)
