# Post-refinement dataset reassessment

Date: 2026-08-04; updated 2026-10-11

This report records the implemented result. The original [`assessment.20260804.md`](assessment.20260804.md) is the read-only baseline and has not been revised. Detailed methods, source policy, parsing decisions, and commands are in [`methods.md`](methods.md).

## Executive outcome

The repository now has a schema-validated, reproducible update path for global edge, cloud, observation, mainland-China public-cloud, China edge/CDN assessment, and China colocation assessment work.

The current [`manifest.20261011.json`](../data/manifest.20261011.json) contains 27,390 location-schema records across 28 layers and 3,125 separately counted network-evidence records across three layers. The October [Google refresh](google-enrichment.20261011.md) adds nine net owned-directory entries and three explicitly listed AI zones to the August inventory, and joins GCPing endpoints and GPU availability. Five mainland views contain 160 repeated source-layer IDs and are deliberately excluded from the location count. Three assessment JSON files record providers whose public evidence is aggregate, product-scoped, or insufficient for canonical locations.

The main improvement is semantic, not merely numeric: provider declarations, current lifecycle, access restriction, jurisdiction, product scope, inferred or inherited coordinates, independent observations, partial directories, aggregate marketing coverage, and quarantined claims are now distinct.

## Schema and publication model

Location schema 1.1.0 added parent relationships, mainland/Hong Kong/Macao/Taiwan jurisdiction, access state, service scope, coordinate CRS, transformed-coordinate support, and cloud resource pools. Schema 1.2.0 adds CoreWeave's provider-defined `super_region` and general `restricted` access. The contract accepts both record versions so older snapshots remain historically accurate. A separate network-evidence schema 1.0.0 represents prefixes, routing origins, RPKI state, facility registrations, IX memberships, and future measurements without geometry. Together these contracts prevent several common errors:

- treating Hong Kong as mainland China;
- treating a dedicated financial cloud as a public region;
- treating a sales-restricted but operating zone as inactive;
- turning a named resource pool into an invented region/AZ hierarchy;
- serializing Chinese GCJ-02 or BD-09 coordinates as WGS 84 without transformation;
- double-counting derived mainland views as new infrastructure.
- treating a prefix, origin ASN, registry relationship, or latency result as a physical POP.

Every generated record has stable identity, source URL, immutable raw reference and SHA-256, source/retrieval dates, lifecycle, source scope, jurisdiction, access state, service scope, precision, coordinate method/CRS, and confidence.

Canonical normalized location layers are retained as GeoJSON; network layers are retained as `NetworkEvidenceCollection` JSON. CSV is a lossless on-demand projection: jq follows the applicable schema-required field order, restores location coordinates from point geometry, and compactly encodes arrays and objects. The Makefile can generate all projections or one named target. The manifest hashes only retained canonical JSON/GeoJSON and reports and records the CSV source and generation command separately. Evidence-bearing raw, recovered, and historical CSVs are unaffected.

## Canonical coverage

| Layer | Records | Record meaning | Geometry |
|---|---:|---|---:|
| Google Edge | 65 | Provider-declared peering/edge metro | 65 points |
| Google owned data centers | 68 | Directory entry; 31 in development | 12 points, 56 null |
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
| June 2026 ASN observation layer | 13,631 | Valid positive provider/ASN TLS observation; seven raw AS0 rows rejected | 13,631 null |
| June 2026 partial city observations | 11,659 | Provider/ASN/MaxMind city geolocation from public map | 11,659 points; none is a facility coordinate |
| CoreWeave core cloud | 63 | 7 super regions + 56 availability zones | 63 null |
| AWS core cloud | 147 | 39 regions + 108 itemized stable AZ IDs | 147 null |
| Google Cloud core | 176 | 43 regions + 130 standard zones + 3 AI zones | 176 null |
| Azure public cloud | 57 | Programmatic public-cloud region | 57 null |
| OCI commercial cloud | 45 | Region with realm, key, and AD count | 45 null |
| IBM Cloud core | 53 | 13 regions + 40 universal zones | 53 null |
| IBM classic data centers | 42 | Stable classic-infrastructure data-center code | 42 null |
| Meta data centers | 33 | Current provider-directory card | 33 null |

These counts describe unlike entities and must not be presented as a physical-site total. Null geometry is intentional missing evidence. A regional centroid does not imply facility precision.

## Hyperscaler coverage implementation

The plan in [`hyperscalers.20260804.md`](hyperscalers.20260804.md) has been implemented for CoreWeave, AWS, Google Cloud, Azure, OCI, IBM, IBM classic infrastructure, and Meta. The dated implementation record is [`hyperscalers.implementation.20260805.md`](hyperscalers.implementation.20260805.md).

The exact increment is 613 records, replacing the earlier rough estimate. Important corrections are preserved rather than hidden:

- CoreWeave has seven published super regions and 56 AZs, not 52 ordinary parent regions.
- AWS has 39 region records but only 108 itemized stable AZ IDs in the retained directory; the 15-AZ gap from the 123 aggregate is not synthesized.
- Azure has 57 region records, including eight restricted and 39 with zone support; it has no manufactured child zones.
- The August Google implementation has 43 regions and 130 standard zones with Compute properties; the October refresh adds three explicit AI zones, 43 GCPing endpoints, and 89 GPU-availability joins.
- OCI's retained itemized commercial table has 45 regions; AD counts remain properties.
- IBM has 13 regions and 40 universal zones; its 39 account-logical labels are not identities. Its 42 classic data centers are separate.
- Meta's current directory has 33 cards. All retain `lifecycle_status=unknown` unless current status is explicit.

All new geometry is null. AWS Local Zones now link to canonical parent region IDs. The manifest preserves original dates instead of relabeling 2026-08-04 sources as 2026-08-05.

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

The June 2026 provider CSVs contain 13,638 raw rows, but each of the seven files contains one invalid AS0 row with a blank name. The corrected layer preserves the raw total and rejects those rows, contributing 13,631 valid provider/ASN TLS observations: Google 4,246; Netflix 2,902; Meta 2,547; Microsoft 1,654; Akamai 1,093; Apple 973; and CloudFront 216. These records remain null-geometry ASN evidence.

The separately retained public KML contributes 11,659 valid MaxMind city-coordinate observations after rejecting four Netflix AS0 placemarks: Google GGC 4,802; Meta FNA 2,736; and Netflix OCA 4,121. It is explicitly partial. Google and Meta cover 198 and 183 countries in the KML versus article aggregates of 215 and 204; Netflix matches 181. Five folders contain exactly 2,000 rows, 599 accepted Netflix records lack a usable city, and Akamai, Microsoft, Apple, and CloudFront are absent. Coordinates are city geolocation evidence, not POP/facility coordinates, and source redistribution rights remain unresolved.

## Network-context implementation

The non-spatial provider-prefix layer contributes 1,581 records: 150 GLOBAL CloudFront, 114 broad Google-owned, 1,091 Google Cloud customer-resource, and 226 Azure Front Door frontend ranges. It contains 1,337 IPv4 and 244 IPv6 declarations. Feed scope is preserved, and no prefix is converted into geometry.

The deterministic RIPEstat pilot selects one IPv4 and one IPv6 prefix from each of four feed scopes. Eight sampled route observations and seven RPKI validations are retained. Seven samples returned announced, RPKI-valid origin/prefix pairs. One CloudFront IPv6 sample was not announced; the negative is limited to that sampled address and time. RIPEstat geolocation was deliberately excluded because it would reuse MaxMind rather than independently corroborate the study.

The bounded PeeringDB pilot covers four returned provider origins—AS8075, AS15169, AS16509, and AS396982—and retains 498 facility registrations plus 1,031 IX memberships. These records assert only what the registry says about each network ASN. They do not prove CDN appliance presence, facility ownership, or a physical provider site. PeeringDB's AUP remains applicable and requires review before broader reuse or redistribution.

RIPE Atlas has not been executed. No provider-approved targets or Atlas credentials/credits are available. A future run must first fix its target list, probe sampling, IPv4/IPv6 and DNS context, rate/repetition, controls, credit budget, and publication terms. The detailed implementation and gate are recorded in [`network-evidence.20260805.md`](network-evidence.20260805.md).

Unsupported Baidu global claims and an uncited Alibaba estimate layer remain quarantined with hashes. They are preserved as historical evidence but are not presented as current coverage.

## Prioritized enrichment roadmap

### Priority 0: protect semantics on every update

- Keep the schema 1.1 core fields mandatory and use 1.2 only where its added semantics apply.
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

- Keep the implemented PeeringDB pilot bounded and linked as registry evidence; obtain a clear bulk reuse/redistribution basis before expanding it.
- Refresh provider-prefix and RIPEstat/RPKI layers as time-versioned evidence without converting them into sites.
- Execute RIPE Atlas only after approved targets, credentials/credits, and the reviewed measurement specification are available.
- Complete a source-rights matrix before republishing retained provider or independent raw snapshots outside this repository.

## Verification status

The suite validates schema conformance, coordinate CRS, stable IDs, parent integrity, view subsets, jurisdiction/access semantics, raw hashes, on-demand CSV/GeoJSON parity, provider-specific source counts, assessment gates, quarantine evidence, and byte-for-byte canonical GeoJSON regeneration.

At this assessment date:

- Google validation covers the August snapshots and the October refresh: 65 edge metros, 68 data-center entries, 43 regions, 130 standard zones, three AI zones, and the endpoint/GPU joins.
- The authoritative/ASN-observation suite passes for 14,982 records across 17 non-Google baseline layers.
- The hyperscaler suite passes for 613 records across eight new layers and checks mixed-date manifest generation.
- The partial city-observation suite passes for 11,659 records.
- The network suite passes for 3,125 records across provider-prefix, RIPEstat, and PeeringDB layers.
- With the refreshed Google layers, the location-schema inventory comprises 27,390 records across 28 layers; network evidence remains separately counted.
- Recovery validation remains separate and passes unchanged.

Recommended update flow:

`fetch → checksum/raw snapshot → parse → normalize → validate → semantic diff → review → publish`

Suggested starting cadence is weekly for APIs, monthly for provider documentation, quarterly for filings and independent measurements, and event-driven for announced launches, closures, acquisitions, or product changes.
