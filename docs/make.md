# Make usage

Date: 2026-08-04

The Makefile manages disposable CSV projections and repository validation. It does not fetch provider sources or regenerate canonical data. Schema-normalized GeoJSON is the retained publication format; CSV is created only when a consumer needs it.

## Requirements

- GNU Make
- `jq`
- Python 3 plus the packages in `requirements.txt` for `make check`

Run `make help` for the short command list.

## Generate CSV

Generate every CSV target recorded by the default dated manifest:

```sh
make csv
```

Generate just one projection:

```sh
make data/google/edge.20260804.csv
make data/coreweave/regions-and-zones.20260804.csv
```

The second example becomes valid when that proposed canonical CoreWeave layer exists. A direct target does not generate unrelated CSV files.

For another retrieval date, point Make at its manifest:

```sh
make RETRIEVED_TAG=20260901 csv
```

This requires `data/manifest.20260901.json` and the GeoJSON files referenced by it. Changing `RETRIEVED_TAG` does not fetch or create a new snapshot.

## What the rule does

The dated manifest supplies the GeoJSON target list. For each target, `scripts/geojson-to-csv.jq`:

1. reads column order from `schema/location.schema.json` → `required`;
2. copies canonical properties into the row;
3. restores `longitude` and `latitude` from Point geometry, or emits empty values for null geometry;
4. serializes arrays and objects as compact JSON with recursively sorted object keys;
5. applies CSV quoting only where commas, quotes, carriage returns, or newlines require it.

Each CSV depends on its GeoJSON source, the schema, and the jq program. Make rebuilds the target when any dependency is newer. Output is first written to a neighboring `.tmp` file and renamed after jq succeeds, so an existing CSV is not partially overwritten.

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

This validates recovery outputs, Google layers, all authoritative and observation layers, manifests, reports, deterministic updater regeneration, and in-memory jq/GeoJSON-to-CSV parity. It does not need materialized normalized CSVs.

To force a projection to be rebuilt even when Make considers it current:

```sh
make -B data/google/edge.20260804.csv
```

## Refresh workflow

To normalize retained source snapshots without fetching new ones, run the appropriate updater commands documented in `methods.md`, rebuild the dated manifest, validate, and optionally materialize CSV:

```sh
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-04
make check
make csv
```

Use updater `--fetch` options only when deliberately taking a new upstream snapshot. A reviewed refresh should preserve the raw response and provenance, pass schema and semantic checks, and inspect additions, removals, lifecycle changes, access changes, and parent changes before publication.

## Troubleshooting

- `jq: command not found`: install jq and rerun the command.
- `test -f data/manifest.<date>.json` fails: build or select an existing dated manifest.
- `No rule to make target ...geojson`: the manifest names a missing canonical source, or the requested CSV has no matching GeoJSON.
- CSV did not rebuild: use `make -B <target>` and check timestamps on the GeoJSON, schema, and jq program.
- A CSV appears in `git status`: only manifest-declared normalized targets are expected to be ignored; raw, recovered, historical, or unregistered files remain visible intentionally.
