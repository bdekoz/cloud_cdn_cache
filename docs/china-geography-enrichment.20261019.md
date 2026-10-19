# China locality enrichment

Implemented October 19, 2026. Chindata now has **nine directory codes**, up from four. A separate [locality view](../data/china/provider-localities.20261019.geojson) provides **147 map points** for nine cloud providers and Chindata. These are city/county reference points, not verified facility coordinates. They are excluded from the canonical location total.

## Chindata

The previous connector read only the landing page. The new builder traverses all seven linked regional pages and retains all eleven linked detail galleries. The [northern directory](https://www.chindatagroup.com/portal/article/index/cid/28/id/34.html) lists H01–H06 and W01. The [Yangtze directory](https://www.chindatagroup.com/portal/article/index/cid/28/id/58.html) adds ChinaEast H01, and the [Greater Bay directory](https://www.chindatagroup.com/portal/article/index/cid/28/id/59.html) adds ChinaSouth W01. This is five additions to the previous four-code layer, exceeding the two additions identified in the initial proposal.

All nine code records retain null geometry, unknown city and unknown lifecycle. The four existing IDs and their first-seen dates are preserved. Gallery photographs supply no admitted coordinates or code-to-campus matches. Consumers should display a table of **nine codes awaiting location evidence** alongside the map.

The separate [campus/alias review](../data/chindata/campus-alias-review.20261019.json) retains eight dated name or phase assertions. The provider places [Sangyuan in Huailai](https://www.chindatagroup.com/media/news/192.html), and a [July 2026 announcement](https://www.chindatagroup.com/media/news/533.html) describes an operating power system at that campus. The [2020 Huailai article](https://www.chindatagroup.com/media/news/194.html) names Donghuayuan and Cunrui; Donghuayuan/Guanting Lake remains a candidate alias. No named campus is equated with a directory code.

The [Lingqiu work report](https://www.lingqiu.gov.cn/lqxrmzfz/zfgzbg/202604/4377a3fe37a042bb9cca483a93d7ac5f.shtml) distinguishes phase 9 production from a program to advance phase 10 construction. Its publication date is April 1, 2026, but the report was presented December 28, 2025. Both dates are retained; neither is relabeled as an October operating confirmation.

Named base links in the [Qingyang](https://www.chindatagroup.com/portal/article/index/cid/28/id/494.html) and [Zhongwei](https://www.chindatagroup.com/portal/article/index/cid/28/id/495.html) directories support two more locality references. Ulanqab and Yichang pages contain regional marketing but no named base entries, so they remain held. The resulting four Chindata points represent **Huailai County, Lingqiu County, Qingyang and Zhongwei**. Campus and phase assertions sharing a locality are grouped; point and assertion counts are not facility counts.

## Alibaba and the wider cohort

The newly captured [Alibaba directory](https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones) has the same five tables and section headings as the October 11 source. Tracking-script values differ, so the raw hashes differ. The 38 regions and 133 zones remain unchanged, with their original canonical evidence dates. The new view adds 29 Alibaba locality points. The previously documented Johor zone-count conflict remains unresolved.

| Provider | Derived locality points |
| --- | ---: |
| Alibaba Cloud | 29 |
| Tencent Cloud | 19 |
| Huawei Cloud | 23 |
| Baidu Cloud | 8 |
| Volcano Engine | 5 |
| Kingsoft Cloud | 4 |
| JD Cloud | 4 |
| Tianyi Cloud | 35 |
| Qiniu | 16 |
| Chindata | 4 |

The nine cloud directories contain 472 canonical input records: **183 region/pool records** map to locality groups, **24 remain held**, and **265 AZ records** are excluded from this view. Broad labels such as Johor, Virginia, Silicon Valley and Saudi Arabia are not silently converted to cities. Haidong's administrative-area/settlement identity also remains held. Source-record IDs and original retrieval dates stay attached to each point.

The [31-vendor assessment](../data/china/geography-enrichment.20261019.json) records existing canonical coverage, new locality coverage and next steps for every member of the earlier China-review cohort. GDS, VNET, Dataport, Runze, Heying and Meiliyun need itemized project/operator/address joins; CDN vendors need itemized POP or geofeed evidence; AI platforms need explicit hosting declarations. Existing portfolios, recognitions, API endpoints and carrier evidence remain available in their original collections. Cohort membership is not a nationality or ownership assertion, and this release does not claim new physical sites for all 31 vendors.

## Geometry, sources and reproduction

Coordinates come from reviewed [GeoNames](https://download.geonames.org/export/dump/) identities under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). They are WGS 84 locality reference points. Huailai and Lingqiu use county records, not a substituted town center. Country, administrative codes, feature type and selected ID are checked explicitly; there is no runtime fuzzy matching. The retained China extract contains two verbatim rows plus the downloaded archive hash; the full cities15000 archive is retained.

The [source catalog](../data/raw/geography-enrichment/catalog.20261019.json) and [bibliography](bibliography.20261019.md) preserve URLs, dates, hashes, roles and limitations, including review-only and unavailable references. The [view report](../data/china/provider-localities.20261019.report.json) supplies every input, grouped membership and held record. Consumers must read `geographic_footprint_views` in the manifest separately from canonical layers. No map application was modified.

```sh
python3 -B scripts/update_geography_enrichment.py
python3 -B scripts/assess_gulf_coverage.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make RETRIEVED_AT=2026-10-19 csv
python3 -B tests/validate_geography_enrichment.py
```

Rebuilding is offline. Captures are separate, immutable inputs. The new suite checks ID conservation, source hashes, county/city precision, grouped membership, held records, CSV parity, Gulf scope and byte-identical regeneration. Earlier snapshots remain reproducible.
