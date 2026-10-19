# CDNs and Cloud Infrastructure

With the aim of creating a more comprehensive picture of global cloud and CDN infrastructure, I have collected data scraped from various service provider websites into CSV and GeoJSON format. So far, I have collected information from:

- [Cloudflare's Global Network](https://www.cloudflare.com/en-gb/network/)
- [Amazon Global Edge Network](https://aws.amazon.com/cloudfront/features/)
- [Microsoft Edge Locations](https://learn.microsoft.com/en-us/azure/frontdoor/edge-locations-by-region)
- [Google Edge Network and GGC Locations](https://peering.google.com/static/js/site/modules/pages/infrastructure.html)
- [Google Owned Data Center Locations](https://datacenters.google/locations/)
- [Fastly PoPs](https://www.fastly.com/network-map/)
- [Facebook (now Meta) Network Appliances](https://anuragbhatia.com/post/2024/05/facebook-fna-update-2024-and-backbone-analysis/)
- [Akamai](https://www.akamai.com/why-akamai)
- [Netflix Open Connect Appliances (OCAs)](https://openconnect.netflix.com/en/)
- [CacheFly](https://www.cachefly.com/network-map/)

For the above, I took the cache locations from the websites and geolocated them. Thus the map is only accurate to city level. The dates in the filenames indicate the last time the relevant website was checked.

Independent measurements also include Anurag Bhatia's [June 2026 global CDN mapping study](https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/). Its ASN and partial city observations are already incorporated separately from provider declarations. The [India and Apple evaluation](docs/cdn-mapping-india-apple.20261019.md) documents Indian network examples, Apple's coverage, and further enrichment opportunities.

For the Facebook Network Appliances, I have drawn on [Anurag Bhatia](https://anuragbhatia.com)'s very creative work in  work in locating them by the airport code in their names.

For the Netflix Open Connect Appliances, I used [SecurityTrails](https://securitytrails.com/) to look for subdomains under oca.nflxvideo.net. A typical OpenConnect appliance subdomain looks like http://ipv4-c008-muc001-ix.1.oca.nflxvideo.net/.  Similar to the Facebook Network Appliances, there is a three-letter airport code embedded in the url. I used the airport codes to geolocate the OCAs.  There is no guarantees that all of those domains are actual live appliances but it is a place to start. I should also say that the maximum number of subdomains that SecurityTrails would list was 10,000. Thus this list is not exhaustive as there were clearly more.  Other handy information in the url includes whether the appliance is located at an IXP or and ISP and whether it is IPv4 or IPv6.

This is very much an exploration so comments and suggestions are extremely welcome.  Feel free to reach out to me [here](https://github.com/stevesong/cloud_cdn_cache/issues) or on social media [@stevesong@mastodon.cloud](https://mastodon.cloud/@stevesong) or [@stevesong](https://twitter.com/stevesong)

The repository's original dataset is published under the [Open Data Commons Attribution License (ODC-By) v1.0](https://opendatacommons.org/licenses/by/1-0/). Provider snapshots and independent research downloads may remain subject to their source-specific terms; provenance files record known licensing status, and no blanket relicensing is assumed.

## Repository layout

- `data/` contains the current provider snapshots.
- `data/manifest.20261019.json` is the current consolidated hash/count/source manifest for 39 location-schema layers, ten derived location views, two separate geographic-footprint views, three ASN comparison views, seven network-evidence layers, five infrastructure-evidence layers, a separate application-endpoint collection, a separately counted vendor registry, and assessments. It preserves the actual dates of retained evidence, including the October Google, China and Yandex updates and the separate Akamai/Apple cartography sources.
- Schema-normalized location layers are committed as canonical GeoJSON and network assertions as canonical JSON; their CSV projections are generated on demand with `jq` and `make`.
- `data/google/` contains schema-normalized Google Edge, owned data-center, and Cloud region/zone layers, including AI zones, GPU availability, and GCPing endpoints.
- `data/yandex/` contains five certification-documented localities, a separate eight-record region/zone hierarchy and 35 CDN cities. `data/russia/` contains assessments, a 178-record geographic view and a separate comparison of 280 RU-registered ASNs. The [approved enrichment](docs/russia-enrichment.20261019.md) also adds Selectel, Cloud.ru and IXcellerate layers, plus Yandex service-prefix and routing evidence.
- `data/applications/` contains 15 DNS observations for five exchange-related hostnames and five entity assessments. Registry country, business presence, declared cloud hosting and unknown physical origins remain separate; application counts are excluded from location and network totals.
- `data/infrastructure/` contains 324 separately counted assertions: 84 connectivity assertions plus 135 China AI-service, 66 facility/portfolio, 12 carrier and 27 Gulf interconnect/dedicated-product assertions. Categories are extensible and units remain explicit. Its Russia connectivity view repeats three assertions and is excluded from canonical totals.
- `data/vendors/` contains 47 vendor, operator, model-brand and unresolved candidate references, excluded from location, network and infrastructure totals.
- Provider subdirectories under `data/` contain schema-normalized authoritative snapshots; each manifest entry records its actual retrieval tag, including the 2026-10-11 Google refresh.
- `data/china/` records the ten-provider mainland public-cloud assessment; provider directories contain generated cloud layers and explicit mainland views.
- `data/china/vendor-coverage-assessment.20261011.json` preserves the pre-enrichment 31-vendor audit. Its approved plan is implemented in `enrichment-implementation.20261011.json`, with refreshed directories, new Qiniu/Azure China layers, AI services, facility/carrier evidence, and legacy/quarantine candidate reconciliation. See [China enrichment](docs/china-enrichment.20261011.md).
- `data/china-edge/` records the separate ten-provider CDN/edge assessment without manufacturing POPs from fleet totals or province coverage.
- `data/china-colocation/` records the separate GDS, VNET, and Chindata assessment; `data/chindata/` contains the partial code-based current directory.
- [China locality enrichment](docs/china-geography-enrichment.20261019.md) expands Chindata from four to nine source-listed codes and adds 147 separate city/county reference points across ten providers. The [initial Chindata proposal](docs/chindata-enrichment-options.20261019.md) is retained for context.
- [AWS and Oracle Gulf enrichment](docs/gulf-enrichment.20261019.md) reviews 19 existing records, adds nine locality points, 27 scoped infrastructure assertions and 563 prefix declarations, and includes weekly source-change monitoring. The [original coverage plan](docs/gulf-coverage-plan.20261019.md) preserves the baseline.
- The [enrichment bibliography](docs/bibliography.20261019.md) and [machine-readable reference index](data/references/bibliography.20261019.json) retain source URLs, dates, raw paths, hashes and admission limits.
- `data/observations/` contains independent evidence kept separate from provider declarations, including Apple-associated TLS observations.
- `data/observations/cdn-asn-comparison.20261019.json` compares all seven providers across 6,564 ASNs. `data/india/` contains a separate 279-ASN APNIC country view and 515 India-geolocated observations; the Apple ASN view retains 973 null-geometry observations. All comparison views are excluded from canonical totals.
- `data/network/` contains non-spatial provider-prefix, RIPEstat routing/RPKI, and bounded PeeringDB relationship evidence. These records are not locations.
- `data/quarantine/` preserves unsupported or provenance-conflicted layers without presenting them as current.
- `data/raw/` contains immutable upstream snapshots used for reproducible recovery.
- `data/recovered/` contains derived records that restore discarded identity and network fields. The original provider snapshots remain unchanged.
- `archive/` contains superseded historical snapshots.
- `schema/` contains separate canonical location and network-evidence contracts and field semantics.
- `scripts/` contains deterministic recovery and provider-update tools; `tests/` validates their checked-in outputs.
- `docs/` contains coverage assessments, methods, recovery notes, and operator guidance.
- [`docs/methods.md`](docs/methods.md) documents source selection, refinement rules, coordinate policy, parsing exceptions, observation limits, quarantine, and reproducibility.
- [`docs/hyperscalers.20260804.md`](docs/hyperscalers.20260804.md) assesses core-cloud coverage for a ten-provider hyperscaler cohort and proposes a staged enrichment plan.
- [`docs/hyperscalers.implementation.20260805.md`](docs/hyperscalers.implementation.20260805.md) records the implemented CoreWeave, AWS, Google Cloud, Azure, OCI, IBM, IBM classic, and Meta layers.
- [`docs/google-enrichment.20261011.md`](docs/google-enrichment.20261011.md) records the current Google refresh, AI-zone identities, GPU availability, GCPing joins, and reproduction commands.
- [`docs/russia-reassessment.20261011.md`](docs/russia-reassessment.20261011.md) records Russian Federation coverage, Yandex source dates, image-claim exclusions, provider gaps, and offline reproduction.
- [`docs/russia-yandex-crypto.20261019.md`](docs/russia-yandex-crypto.20261019.md) preserves the pre-implementation review of 100 RU-coded records, Yandex cloud/CDN sources and five crypto exchanges.
- [`docs/russia-enrichment.20261019.md`](docs/russia-enrichment.20261019.md) records the completed plan, source decisions, new schemas, current counts and offline reproduction.
- [`docs/china-vendor-review.20261011.md`](docs/china-vendor-review.20261011.md) compares Chinese clouds, consumer platforms, AI providers, overseas offerings, and independent platforms, and prioritizes enrichment.
- [`docs/infrastructure-expansion.20261011.md`](docs/infrastructure-expansion.20261011.md) records the expanded current-source search, emergent categories, source boundaries, and serialized infrastructure evidence.
- [`docs/network-evidence.20260805.md`](docs/network-evidence.20260805.md) records the ASN correction, partial city map, provider prefixes, RIPEstat/RPKI pilot, bounded PeeringDB pilot, and RIPE Atlas measurement gate.
- [`docs/cdn-mapping-india-apple.20261019.md`](docs/cdn-mapping-india-apple.20261019.md) evaluates the June study and documents the implemented India/Apple views, dated APNIC join, country-selection limits, and sources for Indian vendors' own CDN services.
- [`docs/make.md`](docs/make.md) documents CSV generation, cleanup, validation, refresh usage, and troubleshooting.

The 2024 Meta FNA source fields and the reconstructable 2023 Netflix OCA hostnames have been recovered. See [the recovery record](docs/recovery.20260804.md) for provenance, confidence levels, limitations, and regeneration commands.

The 2026-10-11 [Google enrichment](docs/google-enrichment.20261011.md) retains 65 edge metros, refreshes the owned data-center directory to 68 entries, and publishes 43 Cloud regions, 130 standard zones, and three explicitly listed AI zones. All 43 regions have supplementary GCPing endpoints; 89 zones have published GPU listings. Cloud geometry remains null, and no latency samples were collected. The [original Google layer record](docs/google-layers.20260804.md) documents the August snapshots.

The current manifest contains 28,024 location-schema records, including the 416 historical Akamai records and 14 independently derived Apple DNS cities described in [cartography restoration](docs/cartography-restoration.20261019.md). October China enrichment refreshes eight cloud vendors, extends global Huawei/Volcano coverage, adds Qiniu and Azure China, and now retains nine partial Chindata codes with unknown lifecycle. The separate China (147-point) and Gulf (nine-point) locality views are excluded from these totals and do not identify facility coordinates. China Mobile and China Unicom remain consolidated ECS source gaps; Unicom AI pools are separately scoped evidence. AI access endpoints, CDN totals, recognized facilities and GDS/VNET portfolios retain explicit units and provenance. Google Edge, owned data centers and Cloud/AI zones remain distinct. The June 2026 ASN and city layers retain 13,631 and 11,659 independent observations. Provider prefixes, sampled routing, registrations and endpoint checks total 3,950 non-spatial network records, including 220 Yandex declarations/routing observations and 563 AWS/OCI Gulf prefix declarations. See the [China implementation](docs/china-enrichment.20261011.md), immutable [baseline assessment](docs/assessment.20260804.md), [reassessment](docs/reassessment.md), and [methods](docs/methods.md).

The [hyperscaler assessment](docs/hyperscalers.20260804.md) identified the missing core hierarchy, and the [implementation report](docs/hyperscalers.implementation.20260805.md) records 613 new provider-declared records across eight layers. These include seven CoreWeave super regions and 56 AZs; 39 AWS regions and 108 itemized stable AZ IDs; 43 Google regions and 130 zones; 57 Azure regions; 45 OCI regions; 13 IBM regions and 40 universal zones; 42 separate IBM classic data centers; and 33 Meta directory locations. All new geometry is intentionally null.

The refinement pipeline uses provider-approved, licensed, public filing/tender, and reproducible measurement evidence. Unauthorized or leaked inventories are not used to fill gaps; source and authorization rules are documented in [methods](docs/methods.md).

To generate every normalized CSV projection from the current manifest, run `make RETRIEVED_AT=2026-10-19 csv`; plain `make csv` selects the August manifest. To generate one file, name it directly, for example `make data/india/cdn-asn-comparison.20261019.csv`. Location/network column order comes from the applicable schema; ASN comparisons use their provider-column metadata. Arrays or objects are emitted as compact JSON. These generated files are ignored by Git. Raw source CSVs, recovered outputs, and historical CSVs remain retained because they contain evidence or fields that cannot necessarily be reconstructed from canonical JSON. See [Make usage](docs/make.md) for cleanup, validation, refresh, and troubleshooting details.

I am grateful to [Mozilla](https://mozilla.com) for affording me the time to produce this map. Any errors are of course my own responsibility.
