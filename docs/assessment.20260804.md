# Dataset Coverage Assessment and Enrichment Paths

Date: 2026-08-04

## Assessment

This is a useful historical and exploratory atlas, but it is not currently defensible as a comprehensive, up-to-date infrastructure inventory.

The repository contains 13 logical current layers across 12 providers and about 20,810 records, counting CSV/GeoJSON pairs only once. Its main strength is breadth—especially Google, Meta, and Netflix infrastructure in less commonly mapped markets. Its main weakness is that the records represent fundamentally different things: metros, POPs, zones, appliances, hostnames, and inferred ASN locations are all presented as comparable points.

Nine dated layers are from 2023, Meta is from 2024, and the three Chinese-cloud layers added in 2025 have no observation date or source metadata. The [original upstream repository](https://github.com/stevesong/cloud_cdn_cache) also appears to have stopped receiving source-data updates in 2024.

### Coverage compared with current sources

| Layer | Repository | Current benchmark | Assessment |
|---|---:|---:|---|
| AWS CloudFront | 501 records, 97 metros | 750+ standard POPs, 100+ cities; 1,140+ embedded POPs; 15 regional caches | Materially incomplete and missing infrastructure classes. [AWS](https://aws.amazon.com/cloudfront/features/) |
| Cloudflare | 288 metros | 337 cities; public status API exposes about 339 location components | Approximately 85% nominal city coverage. Easy refresh candidate. [Network](https://www.cloudflare.com/network/) · [API](https://www.cloudflarestatus.com/api/v2) |
| Azure Front Door | 182 POPs, 106 metros | 192 commercial locations across 109 metros, plus four US Gov locations | Roughly 95% of commercial locations and 97% of metros. [Microsoft](https://learn.microsoft.com/en-us/azure/frontdoor/edge-locations-by-region) |
| Google edge map | 1,267 | Current legacy endpoint: 1,268 | Almost exactly current for that source—one new POP—but Google’s separate [data-center directory](https://datacenters.google/locations/) has a broader scope. [Edge infrastructure](https://peering.google.com/static/js/site/modules/pages/infrastructure.html) |
| Fastly | 80 metros | 84 active metro labels on its map; 164 POP identifiers at 135 location labels in its detailed table | Metro coverage is fairly close, but the dataset loses POP IDs and multi-site structure. [Map](https://www.fastly.com/network-map) · [POP documentation](https://www.fastly.com/documentation/guides/getting-started/concepts/using-fastlys-global-pop-network/) |
| CacheFly | 69 | 88 listed locations, including one coming soon | About 78%; status and service tiers are missing. [CacheFly map](https://www.cachefly.com/network-map/) |
| Akamai | 416 markers | Akamai now describes almost 4,400 embedded POPs in 130+ countries | Counts are not comparable: the local file is a map abstraction, not a POP inventory. [Akamai](https://www.akamai.com/blog/cloud/2026/may/internet-front-door-edge-now-intelligent) |
| AWS Local Zones | 34 GA IDs plus 19 announced rows | 45 currently available zone IDs | About 76% of available IDs. Several old “announced” rows never launched under those IDs and should not remain current. [AWS locations](https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html) |
| Netflix | 9,507 DNS-derived records | No public asset denominator; Netflix reports 1,000+ ISP partners and 60+ data centers | Useful discovery snapshot, but capped by the original SecurityTrails 10,000-result limit and not reproducible from official data alone. [Netflix Open Connect](https://openconnect.netflix.com/en/) |
| Meta | 8,353 FNA records | Original 2024 research reported 8,014 unique strings and 989 airport/city codes | Broad coverage, but the local conversion discarded hostname, IP, and ASN identity, making revalidation difficult. [Source research](https://anuragbhatia.com/post/2024/05/facebook-fna-update-2024-and-backbone-analysis/) |
| Tencent | 41 zones, 18 regions | Current official table contains about 62 zones across roughly 22 region classes | Stale and missing new zones; some locally listed regions are no longer in the current table. [Tencent](https://intl.cloud.tencent.com/document/product/416/64284?lang=en) |
| Alibaba | 19 region points | Current official material describes roughly 29 public regions, with stable region and zone IDs | Needs rebuilding from official IDs rather than extending the existing point list. [Alibaba](https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones) |
| Baidu | 35 claimed global regions | A current official service-region document lists eight Chinese/Hong Kong regions | This is a provenance conflict, not merely staleness. The layer should be quarantined until every claimed region can be substantiated. [Baidu](https://cloud.baidu.com/doc/Reference/s/2jwvz23xx/) |

The widest local layers contain 177 distinct country strings for Google, 162 for Meta, 152 for Akamai, 139 for Netflix, and 112 for Cloudflare. These are only rough measures: country names are not normalized, several are localized, and CloudFront incorrectly places US state abbreviations such as `CA` and `TX` in its country field.

### Important data-quality findings

- Every coordinate is in a valid WGS84 range, and paired CSV/GeoJSON files currently agree on record counts and coordinates.
- There is no stable record ID, canonical schema, source manifest, raw-source archive, observation timestamp, confidence, or location precision.
- Exact duplicates are common: 1,725 Meta rows, 126 CloudFront rows, and 76 Azure Front Door rows. Some probably encode multiple appliances or POPs, but that multiplicity is implicit.
- Meta and Netflix coordinates are often artificially jittered around an airport or city. This creates false precision and makes one site appear to be many physical locations.
- The 2022 Meta archive retained ASN, AS name, IP-family, hostname, and airport information; the current file discarded much of it. That is a significant schema regression.
- The GeoJSON property `IPS Name` is a systematic typo for CSV `ISP Name`.
- The historical 2015 AWS leak should be clearly separated from current provider-declared infrastructure.
- The current ODC-By repository license should not be assumed to relicense every scraped provider page, third-party database, or geocoder result. Source-specific licensing and redistribution terms need a manifest.

## Recommended enrichment and update path

1. Establish a canonical model first.

   Introduce fields such as `provider`, `service`, `entity_type`, `provider_id`, `metro`, `iso_country`, `subdivision`, `status`, `asset_count`, `location_precision`, `source_method`, `source_url`, `observed_at`, `first_seen`, `last_seen`, `asn`, `hostname`, and `confidence`.

   Keep at least four entity types separate:

   - Provider-declared region or zone
   - POP/site/facility
   - Embedded appliance or cache
   - Independently observed ASN/IP/city evidence

2. Preserve evidence rather than only rendered points.

   Store immutable raw snapshots, then generate normalized CSV, GeoJSON, and optionally Parquet. Keep canonical city or airport coordinates in the data; apply visual jitter only in a map renderer. Replace duplicate points with an explicit `asset_count` where identity is unavailable.

3. Automate the easiest authoritative refreshes.

   High-value initial connectors are Cloudflare’s status API, Google’s infrastructure endpoint, Azure’s location/code pages, AWS Local Zones documentation and `ip-ranges.json`, Fastly’s POP table/API, and CacheFly’s network page. Tencent and Alibaba should be rebuilt from official region/zone IDs. Baidu should remain excluded from the current view pending verification.

4. Add an independent observation layer.

   The June 2026 global CDN mapping study supplies fresh ASN/city evidence for Google, Meta, Netflix, Akamai, Microsoft, Apple, and CloudFront. It reports coverage as high as 215 countries or territories for GGC, 204 for Meta, and 181 for Netflix. Its TLS scanning and MaxMind geolocation have known false-negative and precision limits, so these records should complement—not overwrite—provider declarations. [Research and downloads](https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/)

5. Enrich network context.

   - Use [PeeringDB’s API](https://docs.peeringdb.com/api_specs/) for ASN, facility, and IX relationships.
   - Use [RIPEstat](https://stat.ripe.net/docs/data-api/ripestat-data-api) for prefix origin, routing, RPKI, and geolocation evidence.
   - Use [RIPE Atlas](https://beta-ui.atlas.ripe.net/docs/apis/rest-api-manual/introduction) for sampled reachability and latency validation.
   - Retain provider IP-prefix feeds separately because a routed prefix does not prove a physical POP location.

6. Add history and validation.

   A scheduled pipeline should perform:

   `fetch → checksum/raw snapshot → parse → normalize → validate → semantic diff → review → publish`

   Useful checks include coordinate bounds, ISO country validity, stable-ID uniqueness, source/date presence, unexpected row-count changes, stale announced locations, and automatic CSV/GeoJSON parity. Weekly API refreshes, monthly documentation refreshes, and quarterly independent measurements would be reasonable starting cadences.

The best first increment would be to define the schema and provenance manifest, refresh Cloudflare/Azure/Fastly/AWS Local Zones/Google, quarantine Baidu and stale announcements, and ingest the 2026 measurement data as a distinct observation layer—including Apple, which the repository currently lacks.

