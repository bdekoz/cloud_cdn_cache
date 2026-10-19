# Russia enrichment implementation

Implemented October 19, 2026, from the [approved Yandex/crypto assessment](russia-yandex-crypto.20261019.md) and the [earlier domestic-provider review](russia-reassessment.20261011.md). The [implementation receipt](../data/russia/enrichment-implementation.20261019.json) records counts, source receipts and limits.

The enrichment adds **89 location-schema records in six layers, 220 network records, and 15 application DNS observations**. All 89 new location geometries remain null. The [current manifest](../data/manifest.20261019.json) contains 28,019 location records in 39 layers, 3,387 network records in six layers, and a separately counted application collection with five entities. Existing infrastructure evidence and the vendor registry are unchanged. These totals combine different units; they are not counts of operating facilities.

## Location layers

| Layer | Records | Unit and source |
| --- | ---: | --- |
| [Yandex hierarchy](../data/yandex/regions-and-zones.20261019.geojson) | 8 | Two regional labels and six zones: five RU zones and Kazakhstan's `kz1-a`. [Region documentation](https://yandex.cloud/en/docs/overview/concepts/region) and [zone documentation](https://yandex.cloud/en/docs/overview/concepts/geo-scope) |
| [Yandex CDN cities](../data/yandex/cdn-cities.20261019.geojson) | 35 | One declaration per city with one or more PoPs, from the [city directory](https://yandex.cloud/en/docs/cdn/concepts/points-of-presence) |
| [Selectel hierarchy](../data/selectel/russian-hierarchy.20261019.geojson) | 28 | Three Russian regional labels, seven availability zones and 18 distinct pool codes from the [location table](https://docs.selectel.ru/infrastructure/locations/) |
| [Cloud.ru Advanced](../data/cloudru/advanced-regions-and-zones.20261019.geojson) | 5 | Region `ru-moscow-1` and zones `1a`, `1b`, `1c`, `1e`, from the [public zone FAQ](https://cloud.ru/docs/dc-cloud/ug/topics/faq__advanced__datacenter-az) |
| [Cloud.ru Evolution](../data/cloudru/evolution-zones.20261019.geojson) | 3 | `ru.AZ-1`, `ru.AZ-2`, `ru.AZ-3`, retaining their distinct UUIDs from the [VM documentation](https://cloud.ru/docs/virtual-machines/ug/topics/concepts__virtual-machines); Russian placement comes from the [platform overview](https://cloud.ru/docs/evolution/overview/index) |
| [IXcellerate directory](../data/ixcellerate/data-centers.20261019.geojson) | 10 | MOS1–5 operational, MOS6/MOS8/MOS12 planned, MOS7/MOS11 in development, according to the [retrieved campus directory](https://ixcellerate.ru/why-ixcellerate/scalability/) |

Yandex's `ru-central1-m` is scoped to BareMetal; the four other Russian zones are public-cloud zones. Region identities use published regional labels rather than invented provider IDs. The certification localities retained on October 11 remain separate: no zone-to-building join is asserted. Yandex's incident report still carries its October 11 update; neither current recovery nor continued outage is established by these older zone lists. New Yandex lifecycle fields therefore remain unknown.

The CDN source labels 27 cities as Russia. **Simferopol is normalized to Ukraine**, using internationally recognized borders supported by [UN General Assembly resolution 68/262](https://documents.un.org/doc/undoc/gen/n13/455/17/pdf/n1345517.pdf). Its original `source_country_label=Russia` and the normalization evidence remain inspectable. The resulting layer has 26 RU-coded cities. The provider's separate global claim of 78 PoPs is retained in the report and does not become 78 city or facility rows.

Selectel's `ru-6` spans three availability zones. It is one pool with three zone references and per-zone segments, rather than three copies. Pool parents reference their regional grouping. SPB/MSK/NSK pool codes do not establish facility ownership. The parser handles optional HTML closing tags and checks region tabs and zone headers before accepting tables.

Advanced and Evolution are separate product hierarchies. The current Advanced directory requires authorization to expose IDs, but its public FAQ supplies the admitted IDs and explicitly withholds building mappings. Evolution publishes no parent-region identity in the reviewed zone source. [Location schema 1.3](../schema/location-v1.3.schema.json) permits a null zone parent only with an explicit missing-parent flag and source evidence; this avoids inventing a parent. The earlier [1.2 contract](../schema/location.schema.json) remains unchanged, and the new contract accepts its retained records. IXcellerate statuses are provider declarations at retrieval, not measured health; campus capacity is not assigned to individual buildings.

## Yandex network evidence

[Service prefixes](../data/network/yandex-prefixes.20261019.json) contain 49 declarations from the [public-IP documentation](https://yandex.cloud/en/docs/overview/concepts/public-ips) and 115 from the [CDN feed](https://tech.cdn.yandex.net/prefixes/yc.json). VPC, BareMetal, CDN and four supporting-service roles remain separate. Single IPs become `/32` or `/128` entries. The overlapping CDN `/24` and `/27` are retained as declarations; summing their address counts would double-count coverage. No physical country, customer relationship or prefix-to-city mapping is inferred.

[Routing evidence](../data/network/yandex-routing.20261019.json) contains 56 prefixes reported for AS200350 by [RIPEstat at 2026-10-19 00:00 UTC](https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS200350&starttime=2026-10-19T00:00:00&endtime=2026-10-19T00:00:00). It preserves the response timelines and ASN identity evidence. Routing origin does not assign a prefix to one Yandex service or physical location.

## Exchange endpoint evidence

The new [application contract](../schema/application-endpoint.schema.json) and [crypto collection](../data/applications/crypto-endpoints.20261019.json) preserve five entity assessments and 15 DNS queries across five hostnames. Query identity includes entity, hostname, role, timestamp and RR type. Full resolver responses preserve questions, answers, TTLs, authority sections, response flags and comments. Confidence applies to the observed response, not to an origin-location inference.

Eight queries return the requested RR type; seven return NOERROR without that type, including CNAME-only responses to some address queries. None is classified as NXDOMAIN. Address enrichment attaches only to returned addresses contained by the retained routing prefix and registry interval. Registry country, ASN holder and resolver vantage remain separate from origin geography. The source and service-status findings for ABCEX, Bybit, EXMO.me, Garantex and Grinex are linked in the [assessment](russia-yandex-crypto.20261019.md#crypto-exchanges).

Bybit's declared AWS Singapore placement is entity-level provider evidence; it is not a DNS-to-zone join. ABCEX and EXMO.me have RU-registered network evidence with unknown origins. EXMO.me's July termination announcement is retained separately from website DNS availability. Garantex and Grinex have entity context but no admitted current endpoint queries. All 15 query records have null origin country and facility identity. The sampled addresses match no retained Yandex service prefix, which does not exclude other Yandex dependencies. Application evidence is excluded from both location and network totals.

## June registration comparison and geographic view

The [RU ASN comparison](../data/russia/cdn-asn-comparison.20261019.json) joins the existing June CDN study observations to the [RIPE delegated file through June 6](https://ftp.ripe.net/pub/stats/ripencc/2026/delegated-ripencc-extended-20260606.bz2). Parsing checks the header, all resource totals, allocated/assigned intervals, interval bounds and overlaps. Reserved/available ranges are excluded. The report retains unmatched-ASN counts and the file's timezone; exact per-observation study timestamps were not published.

There are **280 RU-registered ASNs**. Provider-associated observation counts are Google 119, Netflix 0, Meta 2, Akamai 37, Microsoft 169, Apple 70 and CloudFront 6. A missing provider reference means not observed in this snapshot. The 70 Apple associations are not 70 Apple facilities or verified Russian cache locations. Comparison schema 1.1 adds `rir_registration` while retaining the original APNIC schema-1.0 records and CSV columns unchanged.

The refreshed [RU geographic view](../data/russia/locations-and-observations.20261019.geojson) contains **178 records, 86 with null geometry**: the 100-record pre-implementation selection plus 78 new RU-coded records. It repeats canonical source features and is excluded from totals. It does not include registry-only ASN matches or exchange endpoints. The earlier 91-record October 11 view remains retained.

## Reproduction and validation

```sh
python3 -B scripts/update_russia_enrichment.py
python3 -B scripts/review_russia_enrichment.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make RETRIEVED_AT=2026-10-19 csv
make check
```

These commands use retained inputs without new DNS queries or web requests. The updater accepts `--output-root /tmp/russia-enrichment` for byte-for-byte comparison. The pre-implementation assessment uses the [frozen manifest](../data/raw/repository/manifest-before-russia.20261019.json), so later additions do not change its baseline. New raw evidence has SHA-256 sidecars; retrieval, provider publication, registry snapshot and DNS observation dates remain distinct. Upstream redistribution terms remain applicable.

Validation covers schema rejection cases, parent references, pool deduplication, source hashes, country normalization, DNS response conservation and error distinctions, registry interval boundaries, CSV parity, canonical/view separation, unchanged prior layers and offline regeneration. The October 11 manifest and earlier India/Apple outputs remain byte-identical.
