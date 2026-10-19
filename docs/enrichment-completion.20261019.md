# Enrichment completion review

The follow-up implementation adds 76 infrastructure assertions, 25 routing/RPKI records and 13 locality reference points. The 28,024 canonical location records remain unchanged. The [completion ledger](../data/enrichment/completion-review.20261019.json) accounts for all 24 held China records, all ten Gulf endpoints, the existing 31-vendor China cohort, and the India/Apple/Russia follow-ups. Unresolved source identities remain explicit; a completed research pass does not establish an unpublished location or future launch.

The current manifest contains 39 canonical layers, eight network layers with 3,975 records, six infrastructure layers with 400 assertions, and three locality views with 169 points. Locality views and infrastructure assertions are excluded from canonical location totals. The [bibliography](bibliography.20261019.md) now contains 209 entries, including failed retrievals and sources reviewed without admitting locations. Earlier location, network and infrastructure outputs remain byte-identical to the [frozen pre-completion manifest](../data/raw/repository/manifest-before-completion.20261019.json).

| Addition | Count | Admission boundary |
| --- | ---: | --- |
| Chindata project/phase and legal-entity references | 21 | Grouped phases and selected approval references, not individual buildings |
| Chindata property-title references | 4 | Published addresses and title holders; no current-operation inference |
| Chindata later phase-status disclosures | 3 | Phase-specific construction/commissioning evidence |
| Tata Indian CDN city declarations | 10 | Historical map declarations; current deployment unknown |
| Gulf facility registrations | 5 | Explicit code/name joins; two contain partial address references |
| VNET campus activity disclosures | 2 | Named codes with activity as of June 30, 2026 |
| Saudi access-latency aggregates | 31 | Provider/city measurements for the first half of 2026 |
| Gulf routing and RPKI observations | 25 | 13 sampled prefixes; no active probes or inferred geography |
| Supplementary locality points | 13 | Ten Tata cities, Wuhu, Riyadh and Nantong; GeoNames reference coordinates |

## Chindata and other China vendors

Chindata's acquisition disclosures supply a useful intermediate crosswalk: named project groups → legal entities → selected approvals and property references. The [June legal opinion disclosed July 21](https://static.cninfo.com.cn/finalpage/2026-07-21/1225433429.PDF) identifies Donghuayuan, Cunrui, Sangyuan, Lingqiu, headquarters and Nantong phases. The implementation retains grouped ranges, such as Lingqiu 8–13, without expanding them into assumed facilities. Four title references identify Donghuayuan machine room 1, a Sangyuan phase-2 machine room, and two Nantong properties. Physical PDF page numbers and title/approval identifiers accompany each assertion.

The [September valuation inquiry reply](https://static.cninfo.com.cn/finalpage/2026-09-23/1225577150.PDF), authored by Chongqing Kunyuan Asset Appraisal, separately describes incomplete construction at Sangyuan phase 3 and Qingyang phase 1, and incomplete commissioning at Lingqiu phase 9. These later phase disclosures qualify interpretation of older campus announcements. They do not refresh every phase's status or change the existing campus/code layer. Filing disclosure dates, document months and approval dates remain distinct.

Nantong now has a city reference point linked to the two disclosed project groups. Jiangsu's populated-place identity is checked explicitly to avoid the Chongqing namesake. The nine public Chindata H/W codes still have no explicit match to these named projects. Their coordinates remain null. A precise address for one titled building does not justify assigning it to an unmatched public code.

Huawei's [Chinese global-infrastructure page](https://www.huaweicloud.com/intl/zh-cn/global/) explicitly associates `cn-east-4` with Wuhu. Tencent's [CLS region table](https://www.tencentcloud.com/document/product/614/18940) associates `me-saudi-arabia` with Riyadh. Both now have supplementary locality points linked to existing canonical IDs. Their original records and retrieval dates are preserved. Of the original 24 holds, two are resolved in this supplement, two Qiniu multi-region containers are excluded from single-city placement, and 20 retain broader or unresolved geography. Alibaba's previously reconciled 38-region/133-zone directory remains unchanged; Johor, Virginia and Silicon Valley labels are not narrowed to invented cities.

[VNET's second-quarter release](https://ir.vnet.com/news-releases/news-release-details/vnet-reports-unaudited-second-quarter-2026-financial-results) explicitly names N-HB Campus 03 and N-OR Campus 01 in its activity discussion. Those codes are admitted as dated campus references with no decoded address or individual capacity. The retained source is a public-reader extraction because direct download returned HTTP 403. The GDS presentation could not be retained successfully; its search excerpts are not admitted. China Mobile and China Unicom still lack an established consolidated public ECS region directory in the reviewed evidence; existing product-specific evidence remains separate. The ledger reconciles every member of the prior 31-vendor cohort and identifies which received a supplement.

## Indian vendors and Apple

The [Tata CDN map](https://www.tatacommunications.com/hubfs/TaCO-2024/cdn/doc/cdn-poplist-map.pdf) visually marks Mohali, Delhi, Jaipur, Gandhinagar, Mumbai, Kolkata, Hyderabad, Bengaluru, Chennai and Kochi as active. The green/orange legend was inspected directly. These ten memberships are retained with unknown current lifecycle and locality reference geometry. The map carries a 2024 copyright notice, which is not treated as a precise publication or deployment date; the landing page's 2022 date is not transferred to the linked PDF.

Jio's [CDN page](https://www.jio.com/enterprisecloud/services/ai-cloud/network/content-delivery-network/) and its linked datasheet and brochure were retained and reviewed. They establish service scope but provide no itemized deployment-city list. The page's original gzip response bytes remain intact and are decoded only for inspection. [Apple's AEC page](https://cache.edge.apple.com/) describes its partner program without listing installations. Neither source resolves the June study's missing endpoint identities. Tata declarations, Jio service statements, Apple ASN/TLS observations and Apple DNS city evidence remain distinct.

## Gulf identity, routing and latency

The [facility-registration assertions](../data/infrastructure/completion-evidence.20261019.json) link DX1, MC1, AWS DC52, AWS DC53 and SmartHub Fujairah by explicit facility codes or names. [DX1's registration](https://www.peeringdb.com/fac/1355) gives IMPZ/Building F90. MC1 supplies an Al Oqda Barka/Al Batinah district reference. Eight endpoint references still lack a verified address; neither of the two admitted references establishes surveyed coordinates. The registry labels DC52 as Hamala and DC53 as Askar; those labels remain separate from AWS's Manama directory label and do not locate Bahrain's core region.

The MC1 API query unexpectedly returned an unfiltered 5,885-facility response. The entire response is retained, and the parser selects reviewed IDs while checking exact names and countries. It does not assume that all returned rows match the query. Multiple center3 facilities in Jeddah and Riyadh make an operator/city-only match insufficient. Equinix's current sustainability guide identifies AD1 but does not establish an explicit join to Oracle's Abu Dhabi endpoint. [e&'s SmartHub page](https://www.eand.ae/smarthub.html) corroborates the Fujairah site name; it does not confirm CloudFront presence there.

The [routing supplement](../data/network/gulf-routing-review.20261019.json) uses one lowest-address prefix per AWS/OCI Gulf region, border group and available IP family. AWS selection uses the AMAZON service scope. Thirteen sampled addresses produce twelve observed routes and twelve valid origin/prefix RPKI results; one Bahrain IPv4 lookup has no returned route. A negative sample is not evidence of regional outage, and a positive Muscat route does not establish Local Zone operation. The retained feed supplies no eligible Muscat IPv6 declaration. Returned routes can cover only part of a declared prefix or be broader than it; each observation preserves its exact scope and timestamp.

The [Saudi regulator's latency dashboard](https://www.cst.gov.sa/en/knowledge-center/reports/cloud-latency-report-26-dashboard) supplies 31 provider/city aggregates across 19 providers, based on residential FTTH Meqyas measurements for the first half of 2026. The linked public data script is retained and parsed as literal data without execution. Oracle's published country-wide averages are 19 ms for Riyadh and 20 ms for Jeddah. ISP-specific values are retained alongside the published weighted average; the updater does not substitute an unweighted mean. Target IPs, individual samples and weights are not available, so these observations cannot be replayed independently, joined to exact endpoints, or used as October health measurements.

Saudi AWS core-region admission still requires an explicit launch statement and published identifiers. Muscat Local Zone and Fujairah CloudFront status still require service-specific updates. These are provider-evidence dependencies, with existing weekly monitoring and launch-review gates in place.

## Russia, exchanges and monitoring

The freshly retrieved [Yandex incident page](https://yandex.ru/company/news/09-10-2026-01) still identifies October 11 as its latest update. Retrieval on October 19 does not establish recovery at Sasovo, Vladimir or Kaluga. Cloud.ru's additional third-zone announcement does not provide an Evolution parent-region identifier. The candidate Grinex domain again returned HTTP 403. No new application-origin or crypto-hosting inference is admitted, and the existing five-entity endpoint dataset remains unchanged.

The first hosted Gulf source review [completed successfully](https://github.com/bdekoz/cloud_cdn_cache/actions/runs/39288284158) at commit `9e10100d1b30b06060c40f316696ae89dda761f8`. Its public run and job receipts are retained in `data/raw/repository/`. The workflow now runs when its monitoring inputs change on `main`, as well as weekly and by manual dispatch. The local `gh` installation could read public run status, but manual dispatch returned HTTP 401; the already authorized SSH push triggered the successful run. No additional credentials were needed.

## Reproduce and validate

Install the Python requirements, `jq`, and Poppler's `pdftotext` (`poppler-utils` on Debian/Ubuntu). The updater runs offline and checks source hashes and reviewed PDF page anchors before producing records.

```sh
python3 -B scripts/update_completion_enrichment.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make RETRIEVED_AT=2026-10-19 csv
make check
```

Validation covers unchanged historical layers, source hashes, exact registry selection, unresolved-code preservation, historical-date handling, reference-coordinate identities, all held-record dispositions, CSV parity, bibliography-ID uniqueness, successful workflow receipts and byte-identical offline regeneration. Capture scripts are separate from reproduction. They retain exact HTTP bytes or explicitly labeled reader/API bundles, including unsuccessful leads; they do not silently refresh an existing capture.

All 16 validation suites and the complete October 19 CSV export passed for this implementation. The hosted source-review result is recorded separately above.
