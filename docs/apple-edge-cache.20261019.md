# Apple Edge Cache locality review

Built 2026-10-19. The [cache-hosting map](../data/apple/aec-localities.20261019.geojson) contains two city reference points: one explicitly named Apple Edge Cache (AEC) deployment and one operator-declared Apple caching locality whose AEC program identity is unconfirmed. This is a partial evidence map, not a global inventory or a count of currently operating sites.

| Locality | Admitted evidence | Interpretation and remaining gap |
| --- | --- | --- |
| Santa Clara, California, US | [SFMIX's cache directory](https://ip.sfmix.org/) explicitly lists Apple Edge Cache, Apple TV+, AS31128 and SCL02. Its [location directory](https://sfmix.org/locations/) places SCL02 at CoreSite, 2972 Stender Way, Santa Clara. | Explicit AEC host/site declaration. The separate [AS31128 participant entry](https://portal.sfmix.org/participants/) is inactive; current cache-site lifecycle remains unresolved. The observed Apple TV HTTP peer belongs to SFMIX AS40271, but its placement at SCL02 is not established. |
| Lyon, France | [France-IX's Q2 2025 technical report](https://www.franceix.net/fr/infrastructure/techhub/rapport-technique-t2-2025/) reports two installed Apple caches and increased traffic in Lyon/AURA. Page 5 of its [Lyon presentation](https://www.franceix.net/documents/57/2025.05.19_-_Presentation_France_IX_Tour_Lyon_-_VF.pdf) corroborates locally hosted Apple caching. | One locality point, not two sites. The sources do not identify separate cache addresses or explicitly call the product AEC. Operation in October 2026 and Apple TV delivery are unverified. |

Coordinates come from GeoNames city records, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Both features have `physical_site_confirmed: false`, `lifecycle_status: not_assessed` and `excluded_from_canonical_totals: true`. The Lyon service label explicitly preserves the uncertain program identity. Santa Clara also appears in the [Apple TV delivery view](../data/apple/tv-delivery-localities.20261019.geojson); these overlapping views must not be added together as deployments.

The Lyon presentation's cover gives June 19, 2025, despite the May date in its filename. The cover date is retained as the presentation claim date; the filename does not establish publication or installation time.

## Additional hosts and exchanges

Seven leads are retained without coordinates. Their absence from the map means the cache placement is unsupported, not that no cache exists.

| Host or exchange | Retained finding | Evidence needed to map it |
| --- | --- | --- |
| [CEnet](https://cenet.catholic.edu.au/blog/avqvtwfgg0c882enccdnxsvv29rkiq-k39mr-escre-jz69a-cz9ph) | December 2023 deployment article describes an installed AEC and November 17 traffic. | Explicit cache city or site. An office address or member school's location is insufficient. |
| [TENET](https://www.tenet.ua/novini/apple-edge-cache) | September 16, 2026 announcement describes an AEC launch in its infrastructure. | Explicit cache city/site and current status. The Odesa contact address does not locate the cache. |
| [LU-CIX](https://www.lu-cix.lu/connected-networks/) | Apple Edge Cache AS31128 is listed with 2 × 100GE connectivity. | Cache placement, rather than exchange membership or port capacity. |
| [1-IX](https://1-ix.net/en/) | Apple Edge Cache AS31128 appears in a membership table attributed to PeeringDB. | Independent cache-location evidence. Distributed exchange sites and remote peering cannot locate the appliance. |
| [PIT-IX](https://portal.pit-ix.net/customer/details) | Apple AEC AS31128 member entry has a July 27, 2026 join date. | Cache city/site. The join date does not establish installation or operating status. |
| [IX Australia](https://ix.asn.au/technical-guide/) | QLD-IX routing policy describes Apple AEC access through AS10084 with explicit opt-in/opt-out communities. | A specific cache placement; regional access policy alone does not justify a Brisbane point. |
| [BIX / Giganet](https://www.bix.hu/en/news/202501_apple_edge_cache_pilot_project) | January 6, 2025 notice describes a pilot connection opportunity. | A located deployment and operating evidence; the pilot does not justify a Budapest point. |

The direct TENET and BIX HTTP captures did not expose their article text. Separately retained web-reader responses support those two assertions, and the capture method is explicit. The AS31128 PeeringDB network query returned an error, the exchange query returned an empty result, and the facility request exceeded the capture limit. These receipts establish capture limitations, not an absence of infrastructure; no PeeringDB facility rows were admitted.

## Admission method

Apple's [AEC program page](https://cache.edge.apple.com/) establishes what the program is, but does not supply a public deployment directory. A point needs a host declaration that names Apple caching and a locality or site that can be joined without ambiguity. An explicit AEC name is recorded separately from generic Apple caching.

Public Apple TV previews provide a useful discovery route. The [delivery investigation](apple-tv-delivery.20261019.md) retained manifests advertising Apple, Akamai and Fastly paths and sampled one video playlist from each. The Apple response identifies an SFMIX cache host, while the actual HTTP connection routes through AS40271. This supports looking for host-operated AEC deployments outside Apple's own ASNs. It does not resolve the sampled IP to a particular building.

The June CDN study, Apple's provider geofeed, AS714/AS6185 facilities, IX participants, Apple office addresses and entire CDN PoP lists are not treated as AEC inventories. Hostname fragments are retained as labels unless a provider or host documents their geographic meaning. No India, Gulf, Russia or China AEC locality was admitted in this bounded review.

To expand coverage, collect the same public-preview headers from access networks with known observer ASN and region, retain the actual HTTP peer and time, and investigate newly seen cache-host labels in operator documentation. Admit additional points only after an explicit host-to-locality join; keep routing, program identity, Apple TV support and current operating status as separate claims. No distributed probes, subscriber sessions or paid measurements were launched here.

## Artifacts and reproduction

- [Eight additional host/IX assertions](../data/infrastructure/apple-aec-hosts.20261019.json), plus the SFMIX declaration in the [TV evidence layer](../data/infrastructure/apple-tv-delivery.20261019.json).
- [Nine-host disposition ledger](../data/apple/aec-review.20261019.json) and [map report](../data/apple/aec-localities.20261019.report.json).
- [Shared source catalog](../data/raw/apple-tv/catalog.20261019.json), with original bytes, source URLs, timestamps, hashes and capture metadata.
- [Bibliography](bibliography.20261019.md) and [machine-readable references](../data/references/bibliography.20261019.json), including failed retrievals and held leads.

Regenerate from retained inputs without network access. PDF corroboration uses `pdftotext` from Poppler, also required by the earlier completion review:

```sh
python3 -B scripts/update_apple_tv.py
python3 -B scripts/update_apple_aec.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make check
make RETRIEVED_AT=2026-10-19 csv
```

`make data/apple/aec-localities.20261019.csv` exports just the map, preserving claim IDs, evidence and gazetteer metadata. The validation suite checks conservative geographic joins, source hashes, CSV parity, deterministic offline reproduction, preservation of the previous bibliography and unchanged canonical location records.
