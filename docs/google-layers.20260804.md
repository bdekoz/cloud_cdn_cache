# Google Edge and Data Center Layers

Date: 2026-08-04

Google Edge and Google-owned data centers are represented as separate provider-declared layers under schema version `1.1.0`. They are not interchangeable asset counts, and neither replaces the existing Google Global Cache snapshot. The 1.1 regeneration adds explicit jurisdiction, access, service-scope, parent, and coordinate-CRS fields without changing membership.

## Outputs

| Layer | CSV | GeoJSON | Records |
|---|---|---|---:|
| Google Edge | [`data/google/edge.20260804.csv`](../data/google/edge.20260804.csv) | [`data/google/edge.20260804.geojson`](../data/google/edge.20260804.geojson) | 65 |
| Google Data Centers | [`data/google/data-centers.20260804.csv`](../data/google/data-centers.20260804.csv) | [`data/google/data-centers.20260804.geojson`](../data/google/data-centers.20260804.geojson) | 59 |

Each layer has a neighboring `.report.json` containing output checksums, counts, lifecycle summaries, and comparison notes. Canonical records conform to [`schema/location.schema.json`](../schema/location.schema.json). CSV and GeoJSON are generated from the same ordered in-memory records.

## Google Edge

Source: [Google peering infrastructure](https://peering.google.com/static/js/site/modules/pages/infrastructure.html)

The source publishes 65 coordinates and explicitly describes them as metros where at least one edge POP is present. Therefore:

- Each row represents a metro with edge presence, not one physical facility.
- `entity_type=edge_pop` and `location_precision=metro` describe the layer, while `properties.representation` preserves the one-or-more-POPs qualification.
- All coordinates are provider supplied.
- The source does not publish location labels in the payload. Sixty-four labels are matched to the legacy Google layer by coordinates; administrative reverse-geocoder labels are normalized to their metro meaning where necessary.
- One new source coordinate, `26.474211, 49.797085`, is labeled Dammam, Saudi Arabia through a curated coordinate match.
- Label derivation is explicit in `properties.label_method`, and overall record confidence is `medium` rather than implying that Google supplied the label.

The legacy layer contains 64 edge metros, so this snapshot adds one provider coordinate while retaining all earlier coordinates.

## Google Data Centers

Source: [Google Data Center locations](https://datacenters.google/locations/)

The directory contains 59 owned-location entries:

- 32 are not marked as in development and are normalized as `operational`.
- 27 are explicitly marked `in_development`.
- 12 include provider coordinates.
- 47 do not include coordinates and are emitted as valid GeoJSON features with `geometry: null`.

No third-party geocoder is used to manufacture missing precision. Entries without provider coordinates use `coordinate_method=unknown` and `location_precision=unknown`. Country and subdivision fields are parsed from the provider's location label; all records include an ISO 3166-1 alpha-2 country code.

The legacy combined Google file contains 24 data-center points from the peering infrastructure map. The 59-row owned-location directory has broader and newer semantics, so it is published as a distinct layer rather than treated as a row-for-row update.

## Raw provenance

The exact HTML inputs and their manifests are stored under `data/raw/google/`:

- `peering-infrastructure.20260804.html`
- `data-centers-directory.20260804.html`

Each manifest records the official URL, retrieval date, byte count, SHA-256 checksum, source counts, semantic warning, and source-license uncertainty. Google does not state a standalone redistribution license in either captured page; verify applicable terms before republishing the raw snapshots.

## Updater options

Generate either layer independently or both:

```sh
python3 -B scripts/update_google.py --retrieved-at 2026-08-04 --dataset edge
python3 -B scripts/update_google.py --retrieved-at 2026-08-04 --dataset data-center
python3 -B scripts/update_google.py --retrieved-at 2026-08-04 --dataset all
```

To capture new official snapshots before normalization, select the desired dataset and add `--fetch`. The retrieval date controls raw and normalized filenames. Existing normalized snapshots are inspected so matching stable IDs can inherit `first_seen`; additions and removals are written to the layer report.

The updater requires Python 3 and the dependency declared in `requirements.txt`.

## Validation

Run:

```sh
python3 -B tests/validate_google.py
```

Validation covers:

- JSON Schema 2020-12 conformance
- Unique stable IDs
- ISO country codes and coordinate bounds
- CSV/GeoJSON record parity
- Null-geometry behavior
- Raw and generated SHA-256 checksums
- Edge and lifecycle counts
- Legacy GGC preservation
- Independent `edge`, `data-center`, and `all` updater options
- Deterministic regeneration in a temporary directory
