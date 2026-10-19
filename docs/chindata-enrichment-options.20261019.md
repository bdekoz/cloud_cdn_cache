# Chindata: empty map and enrichment options

Reviewed October 19, 2026. This is a source investigation and proposed implementation sequence; the canonical Chindata layer has not been changed.

The [current layer](../data/chindata/data-centers.20261011.geojson) contains four records, not zero: `ChinaNorth H01`, `H02`, `H04` and `W01`. All four have null geometry, unknown city and unknown lifecycle, so a point map has nothing to draw. The [October implementation](china-enrichment.20261011.md) explicitly retained the unresolved code-to-campus relationships.

There is also a concrete coverage gap: the connector reads the [directory landing page](https://www.chindatagroup.com/global.html), which exposes the four northern codes, while separate regional pages contain additional entries. Re-fetching only that landing page will not close the gap.

## Recommended sequence

| Priority | Method | Evidence found and expected result |
| --- | --- | --- |
| 1 | Traverse all seven regional directory links and their base pages | The [Yangtze River Delta page](https://www.chindatagroup.com/portal/article/index/cid/28/id/58.html) lists **ChinaEast H01**, and the [Greater Bay Area page](https://www.chindatagroup.com/portal/article/index/cid/28/id/59.html) lists **ChinaSouth W01**. These are two additional code candidates omitted by the current four-code layer. Retain the source's regional association without assuming a city mentioned in regional marketing is the code's location. |
| 1 | Build a Chinese/English campus and operator alias table | The provider's [2020 Sangyuan opening announcement](https://www.chindatagroup.com/media/news/192.html) places Sangyuan in Huailai, Zhangjiakou. Its [July 2026 announcement](https://www.chindatagroup.com/media/news/533.html) reports a system entering service at the same named campus. Start with Sangyuan, then investigate Donghuayuan/Guanting Lake and Cunrui; keep dates and phase identities separate. |
| 1 | Retrieve local planning, land-use, environmental and completion records | Search by the full company/project name, including `秦淮数据`, `大同秦淮数据有限公司`, `桑园`, `怀来`, `灵丘` and `环首都·太行山能源信息技术产业基地`. These are candidates for project IDs, addresses, cadastral boundaries, coordinates and phase-specific status. A permit establishes its dated approval, not completed operation. |
| 2 | Add a separate view of declared cities or campuses for mapping | Once a named campus is explicitly tied to a locality, show a sourced city/metro centroid or verified campus coordinate at its actual precision. Keep this view outside canonical facility totals until overlaps with existing codes are resolved. This can provide useful visible coverage before exact building coordinates are available. |
| 2 | Reconcile certifications and filings against that alias table | Use dated operator reports and official recognition records to corroborate operator, project name and lifecycle. Match exact names, addresses or project identifiers; keep campus totals, building capacity, electrical capacity and IT load distinct. |
| 3 | Inspect provider photo assets and public map references as supporting evidence | The four code detail pages are photo galleries whose assets are CSS background images; ordinary text extraction returns almost nothing. Preserve captions, explicit labels and any source-linked address/map information. OCR or visual resemblance alone should not finalize a code-to-campus relationship. |

The provider also has dedicated pages for [Qingyang](https://www.chindatagroup.com/portal/article/index/cid/28/id/494.html), [Zhongwei](https://www.chindatagroup.com/portal/article/index/cid/28/id/495.html), [Ulanqab](https://www.chindatagroup.com/portal/article/index/cid/28/id/517.html) and [Yichang](https://www.chindatagroup.com/portal/article/index/cid/28/id/522.html). Capture their actual base entries and distinguish named projects, broad service regions and operating buildings. A region label is not a facility count.

For Lingqiu, the [2026 county government work report](https://www.lingqiu.gov.cn/lqxrmzfz/zfgzbg/202604/4377a3fe37a042bb9cca483a93d7ac5f.shtml) reports Chindata phase nine in operation and plans to advance phase ten. This is useful dated lifecycle evidence at project/phase grain, but it does not map the northern site codes. A Datong environmental-report PDF surfaced in search but returned 404 when fetched; no coordinates or project join were admitted from that unavailable file.

## Proposed data and display rules

Maintain an evidence table with provider code, Chinese/English campus names, legal operator, phase/building identifier, municipality, address, source date, lifecycle, raw-source hash and proposed canonical match. Mark each relationship confirmed, candidate or unresolved. Reuse the four existing record IDs when a match is confirmed; preserve aliases when a code/name changes. Do not merge unrelated campuses merely because they share a city or operator.

For geometry, prefer an explicit provider or official project location. Retain original coordinate values and the source CRS; transform GCJ-02, BD-09 or projected coordinates reproducibly before publishing WGS 84. Use a clearly marked locality centroid when only locality evidence is available. Do not substitute the Beijing headquarters address, an ASN registration address, or a map icon's pixel position for a data-center location.

The map should show an accompanying **“4 records awaiting location evidence”** list, rather than an apparently empty inventory or points at `(0, 0)`. Track separately the counts of source-listed codes, resolved campuses, located records and current-status confirmations. These are proposed display changes; this repository review has not modified a map application.

Start implementation with regional traversal and the Sangyuan/Huailai and Lingqiu alias work. Validate source hashes, stable IDs, code/campus deduplication, phase lifecycle, coordinate precision and country/region consistency before publishing any new points. The present review establishes six named code candidates in total, but establishes no verified geographic assignment for the four retained northern codes.
