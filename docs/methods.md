# Data refinement methods

Date: 2026-08-04

This document explains the assessment, recovery, schema evolution, provider refreshes, mainland-China cloud work, separate edge/CDN track, and separate colocation track. The immutable baseline is [`assessment.20260804.md`](assessment.20260804.md); the implemented result is recorded in [`reassessment.md`](reassessment.md).

The central rule is to preserve what a source actually establishes—including its unit, jurisdiction, product scope, uncertainty, and omissions—rather than force every provider into a visually complete point layer.

## Scope and units

The repository contains unlike infrastructure classes. A provider-declared metro, physical POP, owned data center, cloud region, availability zone, operator resource pool, embedded cache, and independently observed ASN are not interchangeable.

Counts use the smallest defensible source unit:

- A provider site code, region ID, or zone ID is one record when the provider publishes it.
- A metro is one record when only a metro list is published; repeated assets are represented by a source-specific count in `properties`.
- A region and each availability zone are separate records when both stable IDs are published.
- A named resource pool remains a resource pool if the source does not publish a region ID or individual zone children.
- An observed provider/ASN pair is one measurement record. It is not a provider-declared POP.
- A province-coverage claim or a fleet total is assessment evidence, not a location record.

Legacy CSV/GeoJSON pairs are counted once after checking record and coordinate parity. Derived mainland views repeat canonical IDs from their parent layers and are excluded from the manifest's canonical `record_count`. Raw, recovered, and historical CSVs remain evidence-bearing artifacts; only schema-normalized CSV publication snapshots with complete GeoJSON equivalents are disposable projections.

## Schema 1.1

[`schema/location.schema.json`](../schema/location.schema.json) is a JSON Schema 2020-12 contract used before canonical GeoJSON serialization. Version 1.1.0 adds the distinctions required by the China work:

- `parent_record_id` links a zone to its published region.
- `jurisdiction_scope` separates mainland China, Hong Kong, Macao, Taiwan, other, global, and unknown scopes.
- `access_status` separates public, sales-restricted, invite-only, and dedicated access from operational lifecycle.
- `service_scope` states which product surface established membership, such as compute, VPC, Cloud Connect, financial cloud, automotive cloud, or colocation.
- `coordinate_crs` is `EPSG:4326` for serialized WGS 84 coordinates and null when geometry is null.
- `coordinate_method=transformed` is available for a documented GCJ-02 or BD-09 conversion.
- `cloud_resource_pool` represents a published pool without inventing region or zone semantics.

Stable provider IDs are preferred for `record_id`, `source_record_id`, and `site_code`. When no provider ID exists, identity derivation must be deterministic and documented. Retrieval dates and row numbers are never identity inputs. Updaters write one sorted canonical GeoJSON stream. The jq projection restores coordinates from geometry, orders columns by the schema's `required` array, recursively sorts object keys, and uses compact JSON for arrays and nested properties.

`lifecycle_status` and `access_status` answer different questions. A Tencent zone can be operational while sales-restricted. A financial-cloud region can be operational and dedicated. Neither condition is represented as inactive.

## Evidence hierarchy

Sources are selected in this order:

1. Provider APIs and machine-readable provider endpoints
2. Provider documentation containing stable IDs or explicit lists
3. Current provider directories, maps, filings, and product coverage pages
4. Licensed public registries, filings, procurement records, or exchange/facility data
5. Reproducible DNS, BGP, TLS, HTTP, or latency measurements
6. Historical or unattributed repository data

Higher-ranked evidence determines current membership and identity. Lower-ranked evidence can provide coordinates or context, but it cannot silently override a provider declaration. Marketing totals are retained in reports or assessment JSON when the provider does not publish the underlying entities.

### Unauthorized or leaked inventory

The refinement pipeline does not acquire, authenticate to, normalize, or redistribute unauthorized or leaked infrastructure inventories. It also excludes credential-gated exports obtained without provider permission and private customer or employee material without a clear access and redistribution basis.

This is both a safety and a data-quality boundary: provenance, consent, integrity, selection bias, freshness, and permissible redistribution cannot be established reliably for such material. Public descriptions of a reported incident may be cited as historical context, but the underlying unauthorized inventory is not converted into location records.

The pre-existing `data/amazon_atlas_leak_2015.json` remains historical repository material. It is not a source for the 2026 normalized layers, is absent from the consolidated manifest, and was not used to fill any China, Google, edge, or colocation gap.

Data supplied by a provider, customer, or researcher can be considered when the contributor is authorized to share it. The provenance record must state the access basis, license or permission, permitted scope, retrieval date, and any redistribution limits; sensitive fields should be minimized before normalization.

## Raw snapshots and provenance

Each normalized refresh starts with an immutable response under `data/raw/<source>/`. A sidecar provenance JSON records:

- source URL and media type;
- source publication date when available;
- retrieval date and repository-relative raw path;
- SHA-256 digest;
- a source-semantics and redistribution note.

Records repeat the raw path and digest, allowing every row to be tied to exact evidence. The pipeline does not publish a parse of a live page without retaining the response that was parsed.

[`data/manifest.20260804.json`](../data/manifest.20260804.json) now covers 19 canonical layers, five derived views, and three assessment artifacts. Canonical counts exclude views. The manifest hashes retained GeoJSON and reports, records each un-hashed CSV target with its source and generator command, and includes the quarantine audit.

Provider documentation, APIs, independent research, and registry data can have terms different from this repository's ODC-By license. Retention in `data/raw` is not a blanket relicensing assertion; provenance files flag source-specific review requirements.

## Refinement workflow

The common update sequence is:

`fetch → checksum and provenance → parse → normalize → schema validation → semantic assertions → source diff → review → publish GeoJSON → optionally project CSV`

An update fails closed when a required table, stable ID, parent relationship, or expected source structure disappears. Known source disagreements are preserved as report fields and asserted in tests. A change in an aggregate claim never causes synthetic rows to be added.

## Existing global provider work

| Layer | Membership and identity | Status/multiplicity | Coordinates |
|---|---|---|---|
| Google Edge | Provider peering coordinate array; one metro record per entry | Kept separate from data centers and GGC | Provider coordinates |
| Google data centers | Provider location directory | `in_development` retained | Provider coordinates for 12 entries; otherwise null |
| Cloudflare | Geographic status-API components with stable site codes | Live health stays in properties | Exact legacy match where available |
| Azure Front Door metros | Provider metro list | Parenthetical POP count becomes `asset_count` | Exact legacy city/country match |
| Azure Front Door codes | Provider abbreviation-directory rows | Kept separate from counted metro assets | Exact legacy match where available |
| AWS CloudFront | Provider standard-POP city list | Per-city count retained; non-itemized REC/embedded totals stay in report | Exact legacy match where available |
| AWS Local Zones | Every current available Local Zone ID | Parent region and network border group retained | Legacy city centroid when unambiguous |
| Fastly | Every provider POP code | Multi-site grouping retained | Provider approximate coordinates |
| CacheFly | Provider location list | Private/premium and planned state retained | Exact legacy match where available |
| Alibaba Cloud | Public region and zone tables | Closing regions retained as inactive; specialized tables excluded from the full public-cloud parse | Legacy regional centroid when matched |
| Tencent Cloud | Region and zone tables | Sales restriction and dedicated specialized products are separate from lifecycle | Legacy regional centroid when matched |

Minimal source repairs remain explicit: a concatenated Portugal/Romania CloudFront paragraph, a Nashville count missing an opening parenthesis, and several source spellings retained as aliases. No missing asset is invented to reconcile a page heading.

## Mainland-China public-cloud track

The provider cohort combines market leaders with coverage-priority providers. Positions six through ten are not presented as an exact revenue ranking. The machine-readable assessment is [`data/china/provider-assessment.20260804.json`](../data/china/provider-assessment.20260804.json).

| Provider | Generated canonical source layer | Result and method |
|---|---|---|
| Alibaba Cloud | `data/alibaba/regions-and-zones.*` | 32 regions + 105 zones globally; mainland view is 13 regions + 60 zones. Hong Kong is separate. |
| Huawei Cloud | `data/huawei/mainland-regions.*` | 9 mainland region IDs. Membership comes from Cloud Connect and IDs are joined from three official auxiliary tables; no universal AZ layer is claimed. |
| Tencent Cloud | `data/tencent/regions-and-zones.*` | 22 regions + 62 zones globally; mainland general view is 7 + 24 and mainland specialized view is 4 + 13. |
| China Telecom Tianyi Cloud | `data/tianyi/vpc-resource-pools.*` | 63 provider-named VPC pools: 40 regional and 23 AZ-capable. No zone children are invented. |
| China Mobile Cloud | none | Gated: no stable itemized authoritative region/zone/pool inventory was retrieved. |
| Baidu AI Cloud | `data/baidu/regions-and-zones.*` | 8 BCC regions + 19 zones; mainland view is 7 + 18 and Hong Kong remains separate. |
| Volcano Engine | `data/volcano/regions-and-zones.*` | 4 regions + 13 explicit zone IDs; mainland view is 3 + 11. Current live documentation API replaces an offline predecessor. |
| China Unicom Cloud | none | Gated: the public ECS surface did not expose a consolidated stable inventory. |
| Kingsoft Cloud | `data/kingsoft/mainland-regions-and-zones.*` | 8 mainland regions + 14 zones, including two dedicated financial region/zone pairs. Singapore is excluded from the mainland layer. |
| JD Cloud | `data/jd/mainland-regions-and-zones.*` | 4 regions + 10 zones parsed from server-rendered documentation state. |

All 152 newly generated public-cloud records have null geometry because the captured official sources do not provide defensible WGS 84 facility coordinates. Nulls are preferred to city centroids unless an explicit mapping use case requests a clearly labeled centroid layer.

### Provider-specific parsing decisions

- Baidu region identity is the common prefix of provider-published BCC zone IDs. The endpoint is retained separately.
- Huawei region membership is product-scoped. A Cloud Connect list is not presented as universal availability across all Huawei services.
- Volcano's Shanghai row declares three zones but explicitly lists four IDs (`a`, `b`, `c`, and `e`). All four IDs are retained and the discrepancy is machine-reported.
- Kingsoft financial regions and zones are operational but `access_status=dedicated` with `service_scope=financial_cloud`.
- Tencent financial and automotive regions use dedicated access; asterisks denoting sales restriction remain properties/access state rather than lifecycle changes.
- Tianyi publishes named pools without stable Latin IDs. IDs are deterministic truncated SHA-256 values of the exact Chinese labels, and the labels remain `source_record_id` and aliases.
- China Mobile and China Unicom produce assessment rows but no speculative canonical records.

## China edge/CDN track

The separate edge assessment is [`data/china-edge/provider-assessment.20260804.json`](../data/china-edge/provider-assessment.20260804.json). It archives nine official public pages and records China Mobile as a documented retrieval gap.

| Provider | Provider-declared coverage retained | Published granularity |
|---|---|---|
| Wangsu | 2,800+ global nodes; 70+ countries/regions; 100+ carriers | Global aggregate |
| Alibaba CDN | 3,200+ global; 2,300+ mainland; 900+ outside; 180 Tbps | Aggregate plus mainland province coverage |
| Tencent CDN | 3,200+ global; 2,300 mainland; 900 outside; 400+ Tbps | Aggregate |
| Huawei CDN | 2,000+ mainland; 800+ outside; 180 Tbps; 130+ countries/regions | Aggregate plus province coverage |
| Baidu CDN | 2,500+ mainland; 800+ outside; 150+50 Tbps stated by scope | Aggregate plus province coverage |
| Volcano CDN | 3,500+ global; 150+ Tbps | Global aggregate |
| Tianyi CDN | 2,000+ mainland; 800+ outside; 160 Tbps | Aggregate plus province coverage |
| China Mobile CDN | no stable public inventory retrieved | Gated |
| China Unicom CDN | nationwide high-performance node claim, no itemized count | Qualitative aggregate |
| BaishanCloud | 1,700+ global edge nodes; 300+ covered cities; 80 Tbps redundancy bandwidth | Global aggregate |

These values are lower-bound marketing claims, not additive or necessarily definition-compatible. None identifies a stable POP, so the edge track generates zero canonical location records. Province coverage means a service is offered in that area; it does not prove one node per province, locate a building, or identify an operator relationship.

Lawful enrichment paths are:

1. Obtain provider-approved site, egress-IP, or origin-allowlist exports where the product exposes them.
2. Capture stable provider site codes from public APIs or documentation before adding a location.
3. Run low-rate, reproducible DNS/BGP/TLS/HTTP measurements against provider-owned test domains, with vantage point, timestamp, resolver, routing state, and classifier version retained.
4. Join licensed PeeringDB, IX, facility, filing, or public procurement evidence as linked observations; do not treat presence at an exchange as proof of owned POP infrastructure.
5. Keep inferred candidates in an observation layer until provider identity and locality can be independently corroborated.

## China colocation track

Colocation is assessed separately because an operator's facility, cabinet, megawatt, campus, and network POP are different units from a cloud region, availability zone, or CDN cache. The assessment is [`data/china-colocation/operator-assessment.20260804.json`](../data/china-colocation/operator-assessment.20260804.json).

| Operator | Current official evidence | Generation decision |
|---|---|---|
| GDS | 51 operational and 16 under-construction data centers across four macro-markets; 12 named market locations including Hong Kong | No facility rows: the current page publishes aggregate counts and market footprints, not stable facility identities. |
| VNET | At 2025-12-31: 889 MW wholesale capacity in service, 49,863 retail cabinets, and 224 network POPs; capacity/cabinets split by macro-market | No facility rows: capacity, cabinets, POPs, self-built sites, and partnered sites must not be conflated. |
| Chindata | Seven current China location clusters and four directory codes; a separate current release names Sangyuan Cloud Computing Campus near Beijing | Four code-based `data_center` records with null geometry. The source does not expose a parseable code-to-city mapping, so no mapping is inferred. |

Chindata's four records are explicitly a partial current directory, not a complete campus count. The named Sangyuan campus is retained as corroborating assessment evidence but is not added as a fifth record because an official alias mapping to one of the four codes was not established.

Next steps are to obtain provider-approved facility directories, track current annual-report portfolio tables, distinguish owned/self-built/partnered/managed assets, preserve construction state, and resolve campus aliases only from explicit provider evidence. Facility counts, buildings, phases, cabinets, megawatts, and network POPs must remain separate metrics.

## Coordinate and jurisdiction policy

Coordinates describe the precision in `location_precision`; they do not prove a building unless a source provides facility evidence.

1. Use provider WGS 84 coordinates when published.
2. If a source publishes GCJ-02 or BD-09, retain the source CRS/value and use a reviewed deterministic transformation before WGS 84 serialization.
3. Otherwise inherit an existing coordinate only through a stable ID or unambiguous normalized city/country match and label it `legacy`.
4. Keep both coordinates null when a safe match is unavailable.
5. Never apply jitter to canonical data; visual separation belongs in a renderer.

Hong Kong, Macao, and Taiwan are never silently folded into `mainland_china`. Provider marketing groupings and billing regions remain in `properties` when they differ from the canonical jurisdiction field.

## Independent observations, recovery, and quarantine

The June 2026 measurement layer contains 13,638 positive provider/ASN TLS observations. Its source inputs provide ASN and AS name, so every record has null geometry. These records are evidence of visible behavior in an ASN at one time, not appliance counts or physical sites.

Meta recovery joins the original 2024 source export back to the simplified map layer and restores hostname, IP, ASN, AS name, address family, and airport/city identity. Netflix recovery reconstructs hostnames only where simplified fields retain enough information. Confidence and unmatched records are preserved; details are in [`recovery.20260804.md`](recovery.20260804.md).

Quarantine preserves bytes and hashes but excludes claims from current coverage. The unsupported 35-location Baidu file and the uncited 14-feature Alibaba estimate remain under [`data/quarantine/`](../data/quarantine/). Quarantine is reversible and does not rewrite historical evidence.

## Validation and reproducibility

Validation covers:

- JSON Schema conformance and paired nullable coordinates;
- WGS 84 CRS consistency;
- stable-ID uniqueness within canonical layers;
- zone-to-region parent integrity;
- view IDs as subsets of parent layers and no double counting;
- jurisdiction, access, lifecycle, and service-scope semantics;
- deterministic ordering and on-demand CSV/GeoJSON parity;
- raw snapshot digests against provenance sidecars;
- provider-specific counts and known source inconsistencies;
- assessment gates for China Mobile, China Unicom, edge aggregates, GDS, and VNET;
- byte-for-byte regeneration from retained snapshots.

Run the checked-in suite with:

```sh
python3 -B tests/validate_recovery.py
python3 -B tests/validate_google.py
python3 -B tests/validate_authoritative.py
git diff --check
```

Regenerate without taking new snapshots with:

```sh
python3 -B scripts/update_google.py --dataset all --retrieved-at 2026-08-04
python3 -B scripts/update_authoritative.py --dataset all --retrieved-at 2026-08-04
python3 -B scripts/update_china.py --dataset all --retrieved-at 2026-08-04
python3 -B scripts/update_china_edge.py --retrieved-at 2026-08-04
python3 -B scripts/update_china_colocation.py --retrieved-at 2026-08-04
python3 -B scripts/update_observations.py --retrieved-at 2026-08-04
python3 -B scripts/audit_quarantine.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-04
make csv
```

`make csv` uses `scripts/geojson-to-csv.jq` to generate every CSV target recorded in the dated manifest. A single target can be generated without materializing the rest, for example `make data/google/edge.20260804.csv`. The outputs are ignored by Git and can be deleted at any time; rerunning the rule reproduces the former checked-in CSVs byte-for-byte. This policy does not apply to raw source, recovery, or historical CSVs.

Use `--fetch` only when intentionally taking new snapshots. Suggested starting cadence is weekly for APIs, monthly for documentation and product directories, quarterly for filings and independent measurements, and event-driven for announced launches or retirements. Every refresh should produce a semantic diff of IDs, parents, jurisdictions, access state, lifecycle, source structure, and aggregate discrepancies before publication.

## Remaining limits

- Null coordinates are intentional evidence gaps, not parser failures.
- A city or region centroid cannot prove a facility, ownership model, or active traffic.
- Public cloud product inventories can differ by service; a service-scoped region list is not universal.
- Edge fleet totals, bandwidth figures, province coverage, and city counts do not identify POPs.
- GDS and VNET do not currently clear the public facility-identity gate used here.
- Chindata's code layer is partial and has no code-to-city mapping in the captured directory.
- Observation data is time-bound and cannot establish exhaustiveness.
- Source-specific redistribution terms require review before raw provider or third-party content is republished elsewhere.
