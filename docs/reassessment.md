# Post-refinement dataset reassessment

Date: 2026-08-04

This report records the implemented result. The original [`assessment.20260804.md`](assessment.20260804.md) is the read-only baseline and has not been revised. Detailed methods, source policy, parsing decisions, and commands are in [`methods.md`](methods.md).

## Executive outcome

The repository now has a schema-validated, reproducible update path for global edge, cloud, observation, mainland-China public-cloud, China edge/CDN assessment, and China colocation assessment work.

The consolidated manifest contains 15,113 canonical records across 19 layers. Five mainland views contain 160 repeated source-layer IDs and are deliberately excluded from that count. Three assessment JSON files record providers whose public evidence is aggregate, product-scoped, or insufficient for canonical locations.

The main improvement is semantic, not merely numeric: provider declarations, current lifecycle, access restriction, jurisdiction, product scope, inferred or inherited coordinates, independent observations, partial directories, aggregate marketing coverage, and quarantined claims are now distinct.

## Schema and publication model

Schema 1.1.0 adds parent relationships, mainland/Hong Kong/Macao/Taiwan jurisdiction, access state, service scope, coordinate CRS, transformed-coordinate support, and cloud resource pools. It prevents several common errors:

- treating Hong Kong as mainland China;
- treating a dedicated financial cloud as a public region;
- treating a sales-restricted but operating zone as inactive;
- turning a named resource pool into an invented region/AZ hierarchy;
- serializing Chinese GCJ-02 or BD-09 coordinates as WGS 84 without transformation;
- double-counting derived mainland views as new infrastructure.

Every generated record has stable identity, source URL, immutable raw reference and SHA-256, source/retrieval dates, lifecycle, source scope, jurisdiction, access state, service scope, precision, coordinate method/CRS, and confidence.

Canonical normalized layers are retained as GeoJSON only. CSV is a lossless on-demand projection: a jq program follows the schema-required field order, restores coordinates from point geometry, and compactly encodes arrays and objects. The Makefile can generate all projections or one named target. The manifest hashes only retained GeoJSON and reports and records the CSV source and generation command separately. Evidence-bearing raw, recovered, and historical CSVs are unaffected.

## Canonical coverage

| Layer | Records | Record meaning | Geometry |
|---|---:|---|---:|
| Google Edge | 65 | Provider-declared peering/edge metro | 65 points |
| Google owned data centers | 59 | Directory entry; 27 in development | 12 points, 47 null |
| Cloudflare | 338 | Geographic status-API component/site code | 243 points, 95 null |
| Azure Front Door metros | 110 | Listed metro with explicit asset count | 104 points, 6 null |
| Azure Front Door codes | 128 | Provider abbreviation-directory row | 97 points, 31 null |
| AWS CloudFront | 102 | Standard-POP metro with explicit asset count | 56 points, 46 null |
| AWS Local Zones | 45 | Current Local Zone ID | 41 points, 4 null |
| Fastly | 164 | Provider POP ID | 164 points |
| CacheFly | 87 | Explicit provider location; one planned | 63 points, 24 null |
| Alibaba Cloud | 137 | 32 regions + 105 availability zones | 83 regional centroids, 54 null |
| Tencent Cloud | 84 | 22 regions + 62 availability zones | 75 regional centroids, 9 null |
| Baidu AI Cloud | 27 | 8 BCC regions + 19 zones | 27 null |
| Huawei Cloud | 9 | Product-scoped mainland region ID | 9 null |
| Volcano Engine | 17 | 4 regions + 13 explicit zone IDs | 17 null |
| Kingsoft Cloud | 22 | 8 mainland regions + 14 zones | 22 null |
| JD Cloud | 14 | 4 mainland regions + 10 zones | 14 null |
| Tianyi Cloud | 63 | 40 regional + 23 AZ-capable VPC resource pools | 63 null |
| Chindata | 4 | Partial current data-center directory code | 4 null |
| June 2026 observation layer | 13,638 | Positive provider/ASN TLS observation | 13,638 null |

These counts describe unlike entities and must not be presented as a physical-site total. Null geometry is intentional missing evidence. A regional centroid does not imply facility precision.

## Mainland-China public-cloud assessment

The ten-provider cohort combines established market leaders with coverage-priority providers. It is not an assertion of exact rank from one through ten. The structured result is [`data/china/provider-assessment.20260804.json`](../data/china/provider-assessment.20260804.json).

| Provider | Coverage result | Current confidence boundary | Next action |
|---|---|---|---|
| Alibaba Cloud | Full layer retained; mainland view has 13 regions + 60 zones | Strong provider IDs; no new coordinate evidence | Monitor IDs/status monthly and seek provider WGS 84 region coordinates |
| Huawei Cloud | 9 mainland region IDs | Membership is Cloud Connect-scoped; no universal AZ inventory | Add service matrices independently; do not merge scopes until IDs agree |
| Tencent Cloud | Full layer retained; mainland general view 7 + 24; specialized view 4 + 13 | Strong IDs; access and lifecycle now separated | Track public, financial, and automotive scopes independently |
| Tianyi Cloud | 63 VPC resource pools: 40 regional, 23 AZ-capable | Published Chinese labels but no stable provider IDs or zone children | Request official IDs; retain label hashes until then |
| China Mobile Cloud | No canonical rows | No stable itemized public inventory retrieved | Request/provider-approved export; monitor official documentation endpoints |
| Baidu AI Cloud | 8 regions + 19 zones; mainland view 7 + 18 | Strong BCC zone IDs; product-scoped | Extend one product at a time and compare region identity across services |
| Volcano Engine | 4 regions + 13 explicit zones; mainland view 3 + 11 | Live doc API; one declared/listed count discrepancy | Monitor the current API and preserve declared/listed values separately |
| China Unicom Cloud | No canonical rows | Public ECS surface lacks a consolidated stable inventory | Seek official API, documentation export, or written directory |
| Kingsoft Cloud | 8 mainland regions + 14 zones | Two financial region/zone pairs are dedicated | Monitor dedicated and public inventories separately |
| JD Cloud | 4 mainland regions + 10 zones | Stable IDs parsed from documentation state | Monitor console/document differences and lifecycle announcements |

### Important corrections and source findings

- Alibaba's captured current public table yields 13 mainland regions and 60 zones. Hong Kong is represented separately rather than inflating the mainland view.
- Tencent's 4 specialized mainland regions and 13 zones are dedicated financial/automotive products, not ordinary public-cloud capacity.
- Tencent asterisks produce sales-restriction metadata while lifecycle remains operational.
- Volcano's Shanghai entry declares three zones but explicitly lists four zone IDs. All explicit IDs are retained, and the disagreement is reported.
- Huawei's 9-region output is explicitly a Cloud Connect membership list joined to official region-ID tables. It is not labeled as universal Huawei availability.
- Tianyi's 63 pools are not transformed into availability zones. The provider describes 23 as AZ-capable but does not publish the child IDs on the captured page.
- No speculative records were emitted for China Mobile or China Unicom.

## Derived mainland views

| View | Records | Parent layer |
|---|---:|---|
| Alibaba mainland regions and zones | 73 | Alibaba full layer |
| Tencent mainland general regions and zones | 31 | Tencent full layer |
| Tencent mainland specialized regions and zones | 17 | Tencent full layer |
| Baidu mainland regions and zones | 25 | Baidu full layer |
| Volcano mainland regions and zones | 14 | Volcano full layer |

View IDs must be subsets of their parents. Tencent general and specialized mainland views are disjoint. The manifest hashes the retained GeoJSON views, records their derived CSV recipes, and excludes all 160 rows from its canonical count.

## Separate China edge/CDN track

The edge/CDN cohort is recorded in [`data/china-edge/provider-assessment.20260804.json`](../data/china-edge/provider-assessment.20260804.json). Nine official pages were archived; China Mobile is retained as an explicit source gap.

| Provider | Current public claim captured | Location-generation result |
|---|---|---|
| Wangsu | 2,800+ global nodes; 70+ countries/regions; 100+ carriers | Gated: aggregate only |
| Alibaba CDN | 3,200+ global; 2,300+ mainland; 900+ outside; 180 Tbps | Gated: province coverage is not POP identity |
| Tencent CDN | 3,200+ global; 2,300 mainland; 900 outside; 400+ Tbps | Gated: aggregate only |
| Huawei CDN | 2,000+ mainland; 800+ outside; 180 Tbps | Gated: province/country coverage only |
| Baidu CDN | 2,500+ mainland; 800+ outside; 150+50 Tbps by scope | Gated: province/country coverage only |
| Volcano CDN | 3,500+ global; 150+ Tbps | Gated: aggregate only |
| Tianyi CDN | 2,000+ mainland; 800+ outside; 160 Tbps | Gated: province/country coverage only |
| China Mobile CDN | No stable inventory retrieved | Gated source gap |
| China Unicom CDN | Nationwide node claim with no itemized list | Gated: qualitative aggregate |
| BaishanCloud | 1,700+ global edge nodes; 300+ cities; 80 Tbps redundancy | Gated: aggregate only |

The assessment deliberately generates zero canonical edge locations. Marketing fleet totals have inconsistent definitions, and a province or covered-city claim does not identify a physical POP, code, operator, address, or coordinate.

The recommended enrichment path is provider-approved site/IP exports first, followed by stable public site codes, then reproducible low-rate DNS/BGP/TLS/HTTP observations. Licensed IX/facility data and public filings can be linked as independent evidence, but exchange presence must not be presented as provider ownership.

## Separate China colocation track

Colocation and hyperscale data-center operators are not merged into the public-cloud cohort. Their market units—facility, building, campus, cabinet, megawatt, and network POP—must remain distinct. The structured assessment is [`data/china-colocation/operator-assessment.20260804.json`](../data/china-colocation/operator-assessment.20260804.json).

### GDS

The current official page publishes 51 operational and 16 under-construction data centers across four macro-markets and names 12 market locations: Beijing, Langfang, Zhangbei, Huailai, Chengdu, Shanghai, Kunshan, Changshu, Shenzhen, Guangzhou, Huizhou, and Hong Kong. It does not expose a complete stable facility directory in parseable text, so no canonical data-center rows are generated.

### VNET

The 2025 Form 20-F reports, as of 2025-12-31, 889 MW of wholesale capacity in service, 49,863 retail cabinets in service, and a 224-POP network. It also publishes macro-market distributions. These are not interchangeable counts, and VNET distinguishes self-built from partnered data centers. No facility rows are generated until a provider-approved facility identity list is available.

### Chindata

The current directory lists seven China clusters and four current codes: `ChinaNorth H01`, `ChinaNorth H02`, `ChinaNorth H04`, and `ChinaNorth W01`. Those codes produce four schema-valid `data_center` records with null geometry and an explicit partial-completeness warning.

A July 2026 official release names Sangyuan Cloud Computing Campus near Beijing. It is assessment evidence but not a fifth canonical row because the official source does not map Sangyuan to or distinguish it from the four directory codes.

The colocation enrichment priority is a provider-approved facility directory, explicit code-to-campus aliases, ownership/operation model, lifecycle, and provider coordinates. Buildings, phases, cabinets, and MW should be child metrics or separate tables rather than extra facilities.

## Source and licensing boundary

The pipeline uses provider-approved, licensed, public filing/tender, and reproducible active-measurement evidence. It does not acquire, normalize, or redistribute unauthorized or leaked infrastructure inventories, credential-gated exports obtained without permission, or private customer/employee material lacking a redistribution basis.

The pre-existing `data/amazon_atlas_leak_2015.json` was not used in any 2026 layer and is absent from the consolidated manifest. If a contributor is authorized to share otherwise non-public data, it can be evaluated only after the provenance record documents permission, permitted use, redistribution terms, retrieval date, and sensitive-field minimization.

This boundary avoids both security harm and false precision: an unauthorized list can be stale, selectively disclosed, tampered with, or impossible to license even when it appears detailed.

## Existing recovery, observations, and quarantine

The Meta recovery restores hostname, IP, ASN, AS name, address family, and airport/city identity from the original 2024 source export. Netflix recovery reconstructs only hostnames justified by retained simplified fields and labels partial reconstructions.

The June 2026 observation layer contributes 13,638 provider/ASN TLS observations: Google 4,247; Netflix 2,903; Meta 2,548; Microsoft 1,655; Akamai 1,094; Apple 974; and CloudFront 217. The source does not publish city/IP detail in the normalized inputs, so geometry remains null.

Unsupported Baidu global claims and an uncited Alibaba estimate layer remain quarantined with hashes. They are preserved as historical evidence but are not presented as current coverage.

## Prioritized enrichment roadmap

### Priority 0: protect semantics on every update

- Keep schema 1.1 fields mandatory.
- Run ID, parent, jurisdiction, lifecycle, access, service-scope, and source-structure diffs before publication.
- Preserve source disagreements instead of forcing aggregate agreement.
- Keep full layers, views, assessments, observations, and quarantine separate in the manifest.

### Priority 1: close authoritative China cloud gaps

- Seek provider-approved inventories for China Mobile and China Unicom.
- Add Huawei service-specific inventories independently and reconcile only stable shared region IDs.
- Monitor all generated provider IDs and lifecycle announcements monthly.
- Add coordinates only from provider WGS 84 data or a documented reviewed transformation.

### Priority 2: build an evidence-based edge inventory

- Request official site/IP allowlists where available.
- Establish a versioned active-measurement design with rate limits, timestamps, multiple mainland and external vantage points, resolver and BGP state, classifier version, and repeatability.
- Keep inferred edge candidates in an observation layer until independently corroborated.
- Track churn separately from first/last seen rather than overwriting rows.

### Priority 3: deepen colocation coverage

- Resolve GDS and VNET facilities from approved directories or current filings with stable facility identities.
- Resolve Chindata codes to campuses only through explicit provider aliases.
- Distinguish self-built, partnered, managed, owned, operational, under-construction, and planned assets.
- Expand the assessed operator cohort only after defining a consistent market unit.

### Priority 4: coordinates, registries, and licensing

- Use licensed PeeringDB/IX/facility evidence as linked observations, not ownership proof.
- Add RIPEstat/RPKI and reproducible latency measurements at ASN/site-ID level where useful.
- Complete a source-rights matrix before republishing retained provider or independent raw snapshots outside this repository.

## Verification status

The suite validates schema conformance, coordinate CRS, stable IDs, parent integrity, view subsets, jurisdiction/access semantics, raw hashes, on-demand CSV/GeoJSON parity, provider-specific source counts, assessment gates, quarantine evidence, and byte-for-byte canonical GeoJSON regeneration.

At this assessment date:

- Google validation passes for 65 edge metros and 59 data-center locations.
- The authoritative/observation suite passes for 14,989 records across 17 non-Google canonical layers.
- Together they comprise the 15,113 records in the 19-layer manifest.
- Recovery validation remains separate and passes unchanged.

Recommended update flow:

`fetch → checksum/raw snapshot → parse → normalize → validate → semantic diff → review → publish`

Suggested starting cadence is weekly for APIs, monthly for provider documentation, quarterly for filings and independent measurements, and event-driven for announced launches, closures, acquisitions, or product changes.
