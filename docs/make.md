# Make usage

Date: 2026-08-04; updated 2026-10-19

The Makefile manages disposable CSV projections, validation, and the bounded network refresh workflow. Schema-normalized GeoJSON is retained for locations, `NetworkEvidenceCollection` JSON is retained for network assertions, and CSV is created only when a consumer needs it. Other provider refreshes remain explicit updater commands.

The current manifest also includes separately counted `InfrastructureEvidenceCollection` JSON and its derived Russia view. `scripts/infrastructure-json-to-csv.jq` projects their schema fields without changing category, unit, nested properties or null geometry. Generate one with `make data/infrastructure/connectivity.20261011.csv`, or include them in `make RETRIEVED_AT=2026-10-11 csv`.

## Requirements

- GNU Make
- `jq`
- Python 3 plus the packages in `requirements.txt` for `make check`
- Poppler's `pdftotext` for Russian/Yandex certifications, China's final recognition directory and corporate/carrier filings

Run `make help` for the short command list.

The current October 19 manifest includes the [India/Apple comparisons](cdn-mapping-india-apple.20261019.md). Run `make RETRIEVED_AT=2026-10-19 csv` to include their projections. Direct targets are `make data/india/cdn-asn-comparison.20261019.csv`, `make data/observations/cdn-asn-comparison.20261019.csv`, `make data/observations/apple-asn.20261019.csv` and `make data/india/cdn-cities.20261019.csv`. Matrix CSVs use `scripts/cdn-comparison-to-csv.jq`, retain source observation IDs, and label missing matches `not_observed_in_this_snapshot`. Their JSON sources and the dated APNIC snapshot are retained; generated CSVs are disposable. The comparison validator runs under `make check`.

The same manifest includes the [Russia enrichment](russia-enrichment.20261019.md): six location layers, two Yandex network layers, the refreshed RU geographic view, the RIPE registration comparison and application endpoints. Direct targets include `make data/russia/cdn-asn-comparison.20261019.csv` and `make data/applications/crypto-endpoints.20261019.csv`. The application projection preserves each DNS response and address/provenance objects in JSON cells; entity-level context stays in the canonical JSON. RIPE comparison headers name the registry explicitly while older APNIC projections retain their headers. Location schema 1.3 keeps the same field order as 1.2.

The [Gulf enrichment](gulf-enrichment.20261019.md) adds `make data/gulf/provider-localities.20261019.csv`, `make data/infrastructure/gulf-cloud-connectivity.20261019.csv` and `make data/network/gulf-provider-prefixes.20261019.csv`. Locality CSVs use their geographic-footprint projection, preserving source IDs, gazetteer evidence and the exclusion from canonical totals. The full October 19 CSV target includes these files and the four refreshed AWS/Oracle location layers.

## Generate CSV

Generate every CSV target recorded by the default dated manifest:

```sh
make csv
```

Generate just one projection:

```sh
make data/google/edge.20260804.csv
make data/coreweave/regions-and-zones.20260805.csv
make data/google/cloud-regions-and-zones.20260805.csv
make data/observations/cdn-mapping-cities.20260805.csv
make data/network/provider-prefixes.20260805.csv
```

A direct target does not generate unrelated CSV files. The default manifest is `data/manifest.20260805.json`; it references older 2026-08-04 GeoJSON where that is the true snapshot date and the new hyperscaler, city-observation, and network files at 2026-08-05.

The current Google refresh is selected by `make RETRIEVED_AT=2026-10-11 csv`. Its manifest retains older dates for other providers and includes the October Google Cloud, AI-zone, GPU, and GCPing enrichment. A direct current target is `make data/google/cloud-regions-and-zones.20261011.csv`. See [`google-enrichment.20261011.md`](google-enrichment.20261011.md) for the offline updater commands.

That manifest also selects the implemented [China enrichment](china-enrichment.20261011.md). CSV targets include the refreshed cloud directories, new Qiniu/Azure China layers, three China infrastructure layers, endpoint/network evidence and the separately counted vendor registry. Infrastructure and registry CSVs use `scripts/infrastructure-json-to-csv.jq`. Examples are `make data/qiniu/resource-pools-and-regions.20261011.csv` and `make data/vendors/registry.20261011.csv`. `make check` validates source-token completeness, ambiguous labels, recognition entries, external joins, native observation bounds and offline regeneration.

For another retrieval date, point Make at its manifest:

```sh
make RETRIEVED_TAG=20260901 csv
```

This requires `data/manifest.20260901.json` and the GeoJSON files referenced by it. Changing `RETRIEVED_TAG` does not fetch or create a new snapshot.

## What the rule does

The dated manifest supplies both its location GeoJSON and network JSON target lists. For a location target, `scripts/geojson-to-csv.jq`:

1. reads column order from `schema/location.schema.json` → `required`;
2. copies canonical properties into the row;
3. restores `longitude` and `latitude` from Point geometry, or emits empty values for null geometry;
4. serializes arrays and objects as compact JSON with recursively sorted object keys;
5. applies CSV quoting only where commas, quotes, carriage returns, or newlines require it.

For a network target, `scripts/network-json-to-csv.jq` reads record order from `schema/network-evidence.schema.json` and serializes the collection's `records` without inventing geometry. Each CSV depends on its canonical JSON/GeoJSON source, applicable schema, and jq program. Make rebuilds the target when any dependency is newer. Output is first written to a neighboring `.tmp` file and renamed after jq succeeds, so an existing CSV is not partially overwritten.

Normalized CSV projections are ignored by Git and are not hashed as retained files in the manifest. Reports and the manifest instead record the target path, canonical GeoJSON source, and Make command.

## Remove generated CSV

Remove only the normalized CSV targets named by the manifest:

```sh
make clean-csv
```

This rule does not remove legacy root-level CSVs, immutable files under `data/raw/`, or recovery outputs under `data/recovered/`. Those files may contain source fields that canonical GeoJSON cannot reconstruct.

If jq fails, a `*.csv.tmp` file can remain beside the target. It is safe to inspect and delete that temporary file after resolving the error.

## Validate

Run all checked-in validation suites and the whitespace/error check:

```sh
make check
```

This validates recovery outputs, Google layers, all authoritative and observation layers, the eight hyperscaler layers, the partial city map, all network-evidence layers, manifests, reports, deterministic updater regeneration, cross-layer parents, canonical CIDRs, and in-memory jq CSV parity. It does not need materialized normalized CSVs.

To force a projection to be rebuilt even when Make considers it current:

```sh
make -B data/google/edge.20260804.csv
```

## Refresh workflow

To normalize retained source snapshots without fetching new ones, run the appropriate updater commands documented in `methods.md`, rebuild the dated manifest, validate, and optionally materialize CSV:

```sh
python3 -B scripts/update_hyperscalers.py --retrieved-at 2026-08-05
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-05
make check
make csv
```

To refresh only one hyperscaler parser from a retained snapshot, select it explicitly:

```sh
python3 -B scripts/update_hyperscalers.py --dataset coreweave --retrieved-at 2026-08-05
python3 -B scripts/update_hyperscalers.py --dataset aws --retrieved-at 2026-08-05
```

Valid dataset names are `coreweave`, `aws`, `google`, `azure`, `oci`, `ibm`, and `meta`. IBM always emits its region/universal-zone and classic-data-center layers together because both come from the same location directory and closure join.

Use updater `--fetch` options only when deliberately taking a new upstream snapshot. A reviewed refresh should preserve the raw response and provenance, pass schema and semantic checks, and inspect additions, removals, lifecycle changes, access changes, and parent changes before publication.

### Network refresh

Regenerate provider prefixes, RIPEstat routing/RPKI evidence, and PeeringDB relationships from the retained 2026-08-05 raw snapshots:

```sh
make refresh-network-offline
```

Deliberately fetch current provider feeds, run the eight-prefix RIPEstat pilot, fetch the bounded four-ASN PeeringDB pilot, and rebuild the manifest:

```sh
make refresh-network RETRIEVED_AT=2026-08-05
```

For a genuinely new snapshot, set a new ISO date, review the upstream source versions and rights, then inspect every semantic diff before publication. The fetch target does not create RIPE Atlas measurements. Atlas remains gated on an approved target list, API credentials/credits, and the measurement policy in `network-evidence.20260805.md`.

## Troubleshooting

- `jq: command not found`: install jq and rerun the command.
- `test -f data/manifest.<date>.json` fails: build or select an existing dated manifest.
- `No rule to make target ...geojson` or `...json`: the manifest names a missing canonical source, or the requested CSV has no matching location/network document.
- CSV did not rebuild: use `make -B <target>` and check timestamps on the GeoJSON, schema, and jq program.
- A CSV appears in `git status`: only manifest-declared normalized targets are expected to be ignored; raw, recovered, historical, or unregistered files remain visible intentionally.

## Locality CSV view

`make RETRIEVED_AT=2026-10-19 csv` includes the separate geographic-footprint view. Generate it alone with `make data/china/provider-localities.20261019.csv`. It uses `scripts/geographic-footprint-to-csv.jq`, preserving grouped source IDs, evidence and gazetteer metadata as JSON-valued columns. It is not a canonical location-schema CSV and does not enter canonical record totals.

The Apple views use the same footprint projection: `make data/apple/aec-localities.20261019.csv` or `make data/apple/tv-delivery-localities.20261019.csv`. Regenerate their retained evidence with `python3 -B scripts/update_apple_tv.py`, then `python3 -B scripts/update_apple_aec.py`, rebuild the bibliography and October 19 manifest, and run `make check`. The [AEC review](apple-edge-cache.20261019.md#artifacts-and-reproduction) gives the full offline command sequence and scope limits.

Run `python3 -B scripts/update_apple_aec_followup.py` before rebuilding the bibliography and manifest to include the [cache candidate follow-up](apple-aec-followup.20261019.md). Its direct CSV targets are `make data/network/apple-aec-candidate-routing.20261019.csv` and `make data/infrastructure/apple-aec-followup.20261019.csv`. The 40 unlocated classification candidates remain in the assessment JSON; they do not enter location or network record totals.
