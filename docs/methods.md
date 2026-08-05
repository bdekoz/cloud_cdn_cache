# Data refinement methods

This document explains how the 2026-08-04 assessment, recoveries, and provider refreshes were produced. The central rule is to preserve what a source actually says—including uncertainty and omissions—rather than making every layer look equally complete.

## Scope and unit of analysis

The repository contains unlike infrastructure classes. A provider-declared metro, a physical POP, a cloud region, an availability zone, an embedded cache, and an independently observed ASN are not interchangeable. The canonical schema therefore keeps them separate with `service`, `entity_type`, `source_scope`, `location_precision`, and `properties`.

Counts in the assessment use the smallest defensible source unit:

- A provider site code or zone ID is one record when the provider publishes that identifier.
- A metro is one record when only a metro list is published; repeated assets are represented by `properties.asset_count`.
- A region and each of its availability zones are separate records when both stable IDs are published.
- An observed provider/ASN pair is one record in the measurement layer. It is not counted as a provider-declared POP.

Legacy CSV/GeoJSON pairs were counted once after confirming record and coordinate parity. Exact duplicate rows were measured separately because they may encode multiplicity rather than data-entry errors.

## Evidence hierarchy

Sources are selected in this order:

1. Provider APIs and machine-readable provider endpoints
2. Provider documentation with stable IDs or explicit lists
3. Provider marketing maps and location lists
4. Reproducible independent measurements
5. Historical or unattributed repository data

Higher-ranked sources determine current membership and identity. Lower-ranked sources may supply coordinates or historical context, but never silently override current provider declarations. Marketing aggregate counts are retained in reports when the provider does not publish the underlying entities.

## Raw snapshots and provenance

Every normalized refresh starts from an immutable snapshot under `data/raw/<source>/`. Each used source has a sidecar provenance JSON containing its URL, retrieval date, media type, source publication date when available, repository-relative path, SHA-256 digest, and a note about source semantics.

[`data/manifest.20260804.json`](../data/manifest.20260804.json) consolidates all 12 normalized layers, output and report hashes, source references, entity distributions, geometry coverage, services, providers, and the quarantine audit. It is generated after all layer outputs so stale artifacts are detectable.

The pipeline does not parse a live page and publish results without retaining the exact response. This makes later parser debugging and semantic diffs possible even if a provider changes its page. Generated records repeat the raw path and hash, so every row can be tied to exact evidence.

Provider HTML, documentation, APIs, independent research, and geocoder results may have terms different from this repository's ODC-By license. No blanket relicensing assumption is made. The 2026 measurement downloads state no explicit data license on the source page; their report and provenance sidecars flag that fact for downstream review.

## Canonical schema and identity

[`schema/location.schema.json`](../schema/location.schema.json) is the JSON Schema 2020-12 contract used before CSV and GeoJSON serialization. Its core includes:

- Stable identity: `record_id`, `aliases`, `source_record_id`, `site_code`
- Classification: `provider`, `service`, `entity_type`, `source_scope`
- Place: city, metro, subdivision, country, ISO alpha-2 code, latitude, longitude, precision, and coordinate method
- Time and provenance: source URL, raw reference, hash, publication/retrieval dates, first/last seen
- Interpretation: lifecycle status, confidence, and source-specific `properties`

`record_id` is independent of retrieval date. Provider site, region, or zone IDs are preferred. If none exists, the ID is derived from provider, entity type, normalized city, subdivision, and country—not from a row number. CSV and GeoJSON are written from the same sorted canonical record stream; arrays and nested properties use compact JSON in CSV.

Schema version 1.0.0 deliberately validates the snake_case service naming convention instead of a closed provider enum. Registered services remain documented in [`schema/README.md`](../schema/README.md).

## Provider-specific refinement

| Layer | Membership and identity | Multiplicity/status treatment | Coordinates |
|---|---|---|---|
| Google Edge | Provider coordinate array; one provider-declared metro record per point | Edge is separate from owned data centers and GGC | Provider coordinates; labels inherited or curated only where the coordinate source lacks labels |
| Google data centers | Provider location directory; one row per directory entry | `in_development` retained; operational otherwise | Provider coordinates for 12 entries; 47 null geometries |
| Cloudflare | Geographic child components of seven region groups in the public status API; component/site codes are stable IDs | Live component health stays in `properties.component_status`, not lifecycle | Exact legacy city/country match where available; otherwise null |
| Azure Front Door metros | Provider metro list, enriched from the separate abbreviation table | Parenthetical POP count becomes `asset_count`; commercial and US Government scope retained | Exact legacy city/country match; otherwise null |
| Azure Front Door codes | One record for each of 128 provider abbreviation-directory rows (130 atomic abbreviations, 114 location labels) | Kept separate because a code-directory row and a counted metro asset are different source units | Exact legacy city/country match; otherwise null |
| AWS CloudFront | Provider standard-POP city list | Parenthetical count becomes `asset_count`; REC and embedded-POP aggregates stay in the report because their individual locations are not published | Exact legacy city/country match; otherwise null |
| AWS Local Zones | Every currently available Local Zone ID | Network border group, parent region, parent zone ID, and geography retained | Legacy city centroid when matched; otherwise null |
| Fastly | Every row in the provider POP directory; POP code is the stable ID | Multi-site groupings retained as `sites_spanned` | Provider-published approximate coordinates for all 164 POP IDs |
| CacheFly | Every location in the provider list | Private/premium markers retained; Marseille is `planned` because it is labeled coming soon | Exact legacy city/country match; otherwise null |
| Alibaba Cloud | Public-cloud tables only; separate records for 32 region IDs and 105 zone IDs | Nanjing and Fuzhou closing-down regions and their zones are `inactive`; specialized finance/government tables excluded and reported | Legacy regional centroid where an exact region/city match exists; otherwise null |
| Tencent Cloud | Separate records for 22 region IDs and 62 zone IDs | Asterisked zones retain `sales_restricted=true` | Legacy region/city centroid where matched; otherwise null |

Provider pages sometimes disagree with themselves. The parser preserves both the explicit list and the prose/header claim rather than manufacturing missing rows:

- Azure's tables contain 107 commercial metros representing 191 assets and three US Government metros. The same page claims 109/192 and four respectively.
- AWS's CloudFront list parses to 102 standard-POP metros and an aggregate asset count of 749, while the prose says 750+ standard POPs in 100+ cities.
- CacheFly's country lists contain 87 locations including Marseille, while regional headings sum to 88.

These discrepancies are asserted in tests so a future source or parser change produces a deliberate review instead of an unnoticed count shift.

### Minimal source repairs

Corrections are limited and explicit. The AWS source concatenates Portugal and Romania in one HTML paragraph and formats Nashville's count without an opening parenthesis; the parser repairs those two structures. CacheFly source spellings `Buenos Aries`, `Kula Lumpur`, and `Kiev` are retained as aliases while canonical labels use Buenos Aires, Kuala Lumpur, and Kyiv. Azure's `Japan(2)` count is accepted despite the missing space. No unlisted facility is invented to reconcile a marketing total.

## Coordinate policy

Coordinates describe the precision stated in `location_precision`; they are not evidence of an exact building unless the source provides facility-level information.

1. Provider coordinates are used when published.
2. Otherwise an existing repository coordinate may be inherited only through an exact stable ID or unambiguous normalized city/country match. Such records use `coordinate_method=legacy`.
3. No bulk third-party geocoding was used in this refresh.
4. If a safe match does not exist, latitude and longitude are both null and GeoJSON geometry is `null`.
5. Jitter is not applied to canonical data. Any visual separation of coincident assets belongs in a map renderer.

Availability zones inherit only a regional/city centroid and are marked with region precision; the point must not be interpreted as a facility location. Fastly explicitly labels its coordinates approximate, and that qualifier is retained in properties.

## Independent June 2026 observations

The independent study starts with routed prefixes, divides them into `/24` blocks, tests port 443, classifies recognizable TLS certificate names, and maps responding IPs to ASNs and locations. The normalized inputs published by the study contain only ASN and AS name. Consequently this repository publishes one null-geometry `observed_presence` record per provider/ASN pair rather than reconstructing unprovided IP or city evidence.

The layer contains 13,638 positive observations:

| Provider | ASN records |
|---|---:|
| Google GGC | 4,247 |
| Netflix OCA | 2,903 |
| Meta FNA | 2,548 |
| Microsoft CDN | 1,655 |
| Akamai | 1,094 |
| Apple | 974 |
| AWS CloudFront | 217 |

Positive TLS observations are useful evidence of CDN presence in an ASN, not a denominator for physical sites. Closed/filtered port 443, an unknown certificate name, routing-table coverage, shared infrastructure, and scan timing can all cause omissions or classification limits. The observation layer therefore complements and never overwrites provider-declared locations.

## Recovery of simplified data

The Meta recovery joins the original 2024 source export back to the simplified map layer and restores hostname, IP, ASN, AS name, address family, and airport/city identity. It preserves all source observations and records exact versus source-only matches.

The Netflix recovery deterministically reconstructs hostnames only where the simplified fields retain enough information. Complete and partial reconstructions are labeled, and no missing sequence, ISP identity, or network fact is guessed. Full details and counts are in [`docs/recovery.20260804.md`](recovery.20260804.md).

## Quarantine policy

Quarantine preserves bytes and hashes but excludes a layer from current views:

- The 35-location Baidu file conflicts with an official service matrix exposing eight mainland-China/Hong Kong region columns and lacks provenance for its global claims.
- The 14-feature Alibaba estimate layer contains uncited node, network-overlay, power-capacity, and facility-detail estimates absent from the official directory.

The files, rationale, and reproducible audit are under [`data/quarantine/`](../data/quarantine/). Quarantine is reversible and does not rewrite historical evidence.

## Validation and reproducibility

Validation covers:

- JSON Schema conformance and paired nullable coordinates
- Stable-ID uniqueness within and across layers
- ISO country-code format and coordinate bounds through the schema
- Deterministic record ordering
- CSV/GeoJSON record, ID, and coordinate parity
- Raw snapshot hashes against provenance sidecars
- Expected source counts, entity types, status distributions, and known source inconsistencies
- Null geometry for all ASN-only observations
- Byte-for-byte regeneration of normalized CSV and GeoJSON in a temporary directory
- Preservation of legacy Google GGC and recovery outputs

Run the full checked-in validation suite with:

```sh
python3 -B tests/validate_recovery.py
python3 -B tests/validate_google.py
python3 -B tests/validate_authoritative.py
git diff --check
```

Regenerate from retained snapshots with:

```sh
python3 -B scripts/update_google.py --dataset all --retrieved-at 2026-08-04
python3 -B scripts/update_authoritative.py --dataset all --retrieved-at 2026-08-04
python3 -B scripts/update_observations.py --retrieved-at 2026-08-04
python3 -B scripts/audit_quarantine.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-04
```

Use `--fetch` on an updater only when intentionally taking a new raw snapshot. A production update should follow `fetch → checksum/snapshot → parse → normalize → validate → semantic diff → review → publish`. API sources are reasonable weekly candidates; documentation sources monthly; independent measurements quarterly or when a new study is released.

## Remaining limits

- Null coordinates are intentional evidence gaps, not parser failures.
- A city point cannot prove a particular facility, ownership model, or active traffic.
- CloudFront REC and embedded-POP totals lack public itemized location lists on the captured page.
- Azure, AWS, and CacheFly publish internally inconsistent aggregate and explicit-list counts.
- Observation data measures visible TLS behavior at one time and is not exhaustive.
- Source-specific redistribution rights still require review before republishing raw third-party/provider content outside this repository.
