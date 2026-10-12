# Google layer refresh and enrichment

Date: 2026-10-11

This refresh checks current public sources, including [GCPing](https://gcping.com/), and preserves the August snapshots. Google Edge, owned data-center directory entries, Cloud regions/zones, and historical GGC remain separate units.

## Published snapshots

| Layer | Previous records | Current records | Current canonical file |
|---|---:|---:|---|
| Google Edge metros | 65 | 65 | [`edge.20261011.geojson`](../data/google/edge.20261011.geojson) |
| Google-owned data-center directory | 59 | 68 | [`data-centers.20261011.geojson`](../data/google/data-centers.20261011.geojson) |
| Google Cloud regions and zones | 173 | 176 | [`cloud-regions-and-zones.20261011.geojson`](../data/google/cloud-regions-and-zones.20261011.geojson) |

Neighboring `.report.json` files record counts, source references and digests, canonical checksums, and CSV generation recipes. The new [`manifest.20261011.json`](../data/manifest.20261011.json) selects these three Google snapshots and retains actual older dates for other providers. It contains 27,390 location-schema records across 28 layers and 3,125 separately counted network-evidence records. The increment of 12 is nine net directory entries and three AI-zone identities, not a physical-facility expansion count.

## Edge and owned data centers

The [Google peering map](https://peering.google.com/static/js/site/modules/pages/infrastructure.html) still publishes the same 65 edge-metro coordinates. Each point represents a metro with one or more POPs. Its other arrays remain distinct: 24 peering-map data-center points and 1,179 GGC coordinates. This refresh does not replace the historical combined GGC files.

The [owned data-center directory](https://datacenters.google/locations/) has 68 entries: 37 not marked in development, normalized as operational under the existing convention, and 31 marked in development. Twelve have provider coordinates; the other 56 retain null geometry. A directory entry can describe a city, county, or broader area and is not necessarily a building.

Compared with August, 14 labels are added and five disappear. Broad entries including Central Ohio, Indiana, Mayes County, and Northern Virginia give way to finer locality labels. These remain directory-membership differences without invented one-to-one identity continuity. Ellis County, Texas is also absent; absence alone does not establish decommissioning. Reports enumerate all added and removed IDs.

Lincoln, Nebraska and Mesa, Arizona change from `in_development` to not marked in development. Their stable IDs and original `first_seen` dates are retained, and reports list these lifecycle transitions.

## Cloud hierarchy and AI zones

The [Compute region/zone table](https://docs.cloud.google.com/compute/docs/regions-zones) still supplies 43 regions and 130 standard zones. Published machine-type lists change for 69 retained zones, CPU-platform lists for ten, options for four, and low-CO2 markings for nine. These describe documented support or labels rather than live capacity.

The separate [AI-zone directory](https://docs.cloud.google.com/compute/docs/regions-zones/ai-zones) identifies three additional zones:

| AI zone | Published locality | Region | Standard parent zone |
|---|---|---|---|
| `europe-west4-ai1a` | De Kooy, Netherlands | `europe-west4` | `europe-west4-a` |
| `us-central1-ai1a` | Lincoln, Nebraska | `us-central1` | `us-central1-a` |
| `us-south1-ai1b` | Austin, Texas | `us-south1` | `us-south1-b` |

The Cloud layer contains 43 regions and 133 zones: 130 standard plus three AI. Reports separate `standard_availability_zone_count` and `ai_zone_count` so specialized zones are not confused with the provider's standard-zone aggregate.

AI records use `entity_type=availability_zone` and stable `google:availability_zone:<zone-id>` IDs. `properties.zone_kind=ai` distinguishes them from standard zones. `parent_record_id` links to the region, while `properties.parent_zone_id` and `parent_zone_record_id` identify the standard parent zone. Region properties list both kinds of children and their separate counts.

Google says AI zones share software-update schedules and sometimes infrastructure with their standard parents. Records preserve this relationship without implying another independent failure domain. AI zones retain their own locality labels and null geometry; no region coordinate is copied onto them. Enabling AI-zone visibility for the project is recorded as `access_status=restricted` and an explicit access requirement, separate from operational lifecycle. Illustrative names mentioned only in explanatory prose, such as `us-west4-ai2b`, are not generated as directory entries.

## GPU availability

The [GPU locations table](https://docs.cloud.google.com/compute/docs/regions-zones/gpu-regions-zones) joins to 89 explicit zones: 88 standard and `europe-west4-ai1a`, which lists G4. Matching zones gain `properties.gpu_availability`, including published machine-type labels, locality, URL, raw reference, digest, and retrieval date. Regions list their matching `gpu_zone_ids`.

Listed GPU support does not establish available stock, quota, entitlement, or measured performance. The other 44 zone IDs are reported as absent from this table, without inferring no GPU support. Lincoln and Austin remain valid AI-zone identities even though the GPU table does not list them.

## GCPing

The [endpoint catalog](https://global.gcping.com/api/endpoints) has 44 entries: one for each of the 43 provider-declared regions plus `global`. All regional keys join exactly to existing region codes. Each region gains `properties.gcping` with the catalog label, HTTPS URL, raw reference, digest, retrieval date, and methodology link. Supplementary metadata uses `source_scope=observed`; canonical membership remains `provider_declared`, and GCPing labels do not replace Compute locality labels.

[GCPing's methodology](https://gcping.com/) describes browser HTTPS requests to regional Cloud Run services and median request/response elapsed time. It is not an official Google product. Timing depends on the caller and is not ICMP RTT, inter-region latency, a universal ranking, or facility-location evidence. The global load-balancer endpoint is retained only in report metadata, without generating a region or location.

This refresh captures the catalog and methodology, collects no latency samples, and makes no endpoint-health assertion. Later observations would require timestamps, caller/probe context, protocol, sample counts, errors, and method in the separate network-evidence track.

## Provenance, reproduction, and validation

Seven raw snapshots and sidecars are retained under [`data/raw/google/`](../data/raw/google/): peering, owned locations, standard Compute zones, AI zones, GPU zones, GCPing endpoints, and GCPing methodology. The Cloud report and consolidated manifest include enrichment-source digests alongside primary-source digests. Source-specific copyright and redistribution terms remain applicable.

With the dependencies in `requirements.txt` installed, regenerate offline:

```sh
python3 -B scripts/update_google.py --dataset all --retrieved-at 2026-10-11
python3 -B scripts/update_hyperscalers.py --dataset google --google-enrichment --retrieved-at 2026-10-11
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-11
make check
```

Keep `--google-enrichment` when rebuilding this enriched Cloud snapshot. The explicit flag preserves historical single-source regeneration. Add `--fetch` only when deliberately taking new upstream snapshots with a new retrieval date.

Generate current projections with `make RETRIEVED_AT=2026-10-11 csv`, or one with `make data/google/cloud-regions-and-zones.20261011.csv`. Plain `make csv` retains the August default.

Validation covers historical and current snapshots, schema, stable identities and history, raw/canonical hashes, CSV parity, endpoint joins, both AI parent relationships, access restrictions, GPU coverage, directory churn, lifecycle changes, manifest selection, and byte-for-byte offline regeneration. History lookup ignores future snapshots when reproducing an earlier date.
