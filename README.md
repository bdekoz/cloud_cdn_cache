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

For the Facebook Network Appliances, I have drawn on [Anurag Bhatia](https://anuragbhatia.com)'s very creative work in  work in locating them by the airport code in their names.

For the Netflix Open Connect Appliances, I used [SecurityTrails](https://securitytrails.com/) to look for subdomains under oca.nflxvideo.net. A typical OpenConnect appliance subdomain looks like http://ipv4-c008-muc001-ix.1.oca.nflxvideo.net/.  Similar to the Facebook Network Appliances, there is a three-letter airport code embedded in the url. I used the airport codes to geolocate the OCAs.  There is no guarantees that all of those domains are actual live appliances but it is a place to start. I should also say that the maximum number of subdomains that SecurityTrails would list was 10,000. Thus this list is not exhaustive as there were clearly more.  Other handy information in the url includes whether the appliance is located at an IXP or and ISP and whether it is IPv4 or IPv6.

This is very much an exploration so comments and suggestions are extremely welcome.  Feel free to reach out to me [here](https://github.com/stevesong/cloud_cdn_cache/issues) or on social media [@stevesong@mastodon.cloud](https://mastodon.cloud/@stevesong) or [@stevesong](https://twitter.com/stevesong)

The repository's original dataset is published under the [Open Data Commons Attribution License (ODC-By) v1.0](https://opendatacommons.org/licenses/by/1-0/). Provider snapshots and independent research downloads may remain subject to their source-specific terms; provenance files record known licensing status, and no blanket relicensing is assumed.

## Repository layout

- `data/` contains the current provider snapshots.
- `data/manifest.20260805.json` is the current consolidated hash/count/source manifest for 27 canonical layers, five derived views, and the China assessment artifacts. It preserves the actual 2026-08-04 tags of older layers.
- Schema-normalized publication layers are committed as canonical GeoJSON; their CSV projections are generated on demand with `jq` and `make`.
- `data/google/` contains schema-normalized Google Edge and Google Data Center layers.
- Provider subdirectories under `data/` contain schema-normalized authoritative refreshes dated 2026-08-04 or 2026-08-05; each manifest entry records its actual snapshot tag.
- `data/china/` records the ten-provider mainland public-cloud assessment; provider directories contain generated cloud layers and explicit mainland views.
- `data/china-edge/` records the separate ten-provider CDN/edge assessment without manufacturing POPs from fleet totals or province coverage.
- `data/china-colocation/` records the separate GDS, VNET, and Chindata assessment; `data/chindata/` contains the partial code-based current directory.
- `data/observations/` contains independent evidence kept separate from provider declarations, including Apple CDN presence.
- `data/quarantine/` preserves unsupported or provenance-conflicted layers without presenting them as current.
- `data/raw/` contains immutable upstream snapshots used for reproducible recovery.
- `data/recovered/` contains derived records that restore discarded identity and network fields. The original provider snapshots remain unchanged.
- `archive/` contains superseded historical snapshots.
- `schema/` contains the canonical location contract and field semantics.
- `scripts/` contains deterministic recovery and provider-update tools; `tests/` validates their checked-in outputs.
- `docs/` contains coverage assessments, methods, recovery notes, and operator guidance.
- [`docs/methods.md`](docs/methods.md) documents source selection, refinement rules, coordinate policy, parsing exceptions, observation limits, quarantine, and reproducibility.
- [`docs/hyperscalers.20260804.md`](docs/hyperscalers.20260804.md) assesses core-cloud coverage for a ten-provider hyperscaler cohort and proposes a staged enrichment plan.
- [`docs/hyperscalers.implementation.20260805.md`](docs/hyperscalers.implementation.20260805.md) records the implemented CoreWeave, AWS, Google Cloud, Azure, OCI, IBM, IBM classic, and Meta layers.
- [`docs/make.md`](docs/make.md) documents CSV generation, cleanup, validation, refresh usage, and troubleshooting.

The 2024 Meta FNA source fields and the reconstructable 2023 Netflix OCA hostnames have been recovered. See [the recovery record](docs/recovery.20260804.md) for provenance, confidence levels, limitations, and regeneration commands.

Google Edge and owned data centers are now separate normalized layers. See [the Google layer record](docs/google-layers.20260804.md) for source semantics, updater options, null-geometry handling, and validation commands.

Cloudflare, Azure Front Door, AWS CloudFront and Local Zones, Fastly, CacheFly, Alibaba, Tencent, Baidu, Huawei, Volcano, Kingsoft, JD, Tianyi, and the partial Chindata directory have normalized refreshes dated 2026-08-04. Google Edge and owned data centers remain distinct options. China Mobile and China Unicom are explicit public-cloud source gaps; China edge/CDN marketing aggregates and the GDS/VNET portfolio totals remain assessments rather than speculative points. The June 2026 ASN observation layer adds Google, Netflix, Meta, Akamai, Microsoft, Apple, and CloudFront evidence without conflating observations with physical locations. See the immutable [baseline assessment](docs/assessment.20260804.md), the implemented [reassessment](docs/reassessment.md), and [methods](docs/methods.md).

The [hyperscaler assessment](docs/hyperscalers.20260804.md) identified the missing core hierarchy, and the [implementation report](docs/hyperscalers.implementation.20260805.md) records 613 new provider-declared records across eight layers. These include seven CoreWeave super regions and 56 AZs; 39 AWS regions and 108 itemized stable AZ IDs; 43 Google regions and 130 zones; 57 Azure regions; 45 OCI regions; 13 IBM regions and 40 universal zones; 42 separate IBM classic data centers; and 33 Meta directory locations. All new geometry is intentionally null.

The refinement pipeline uses provider-approved, licensed, public filing/tender, and reproducible measurement evidence. Unauthorized or leaked inventories are not used to fill gaps; source and authorization rules are documented in [methods](docs/methods.md).

To generate every normalized CSV projection, run `make csv`. To generate one file, name it directly, for example `make data/google/cloud-regions-and-zones.20260805.csv`. Column order comes from the schema, and arrays or objects are emitted as compact JSON. These generated files are ignored by Git. Raw source CSVs, recovered outputs, and historical CSVs remain retained because they contain evidence or fields that cannot necessarily be reconstructed from canonical GeoJSON. See [Make usage](docs/make.md) for cleanup, validation, refresh, and troubleshooting details.

I am grateful to [Mozilla](https://mozilla.com) for affording me the time to produce this map. Any errors are of course my own responsibility.
