# China cloud, AI and connectivity enrichment

Reviewed and retrieved: 2026-10-11, America/Los_Angeles. Native observations retain their actual 2026-10-12 UTC timestamps.

The approved [vendor review and plan](china-vendor-review.20261011.md) is implemented for the available public evidence. The original audit remains pinned to the August manifest. The durable [implementation record](../data/china/enrichment-implementation.20261011.json) hashes the outputs and records unresolved gaps. The [64-entry source catalog](../data/raw/china-enrichment/catalog.20261011.json) retains public responses, explicit fact extracts, observation captures and their SHA-256 provenance.

The current manifest has **27,500 location-schema records across 31 layers**, an increase of 105. Its eight derived views repeat 303 IDs and are excluded from that total. Network evidence totals **3,167 records across four layers**, including 42 new China-related observations/registrations. Infrastructure evidence totals **297 assertions across four layers**, including 213 new China-related assertions. A separate **47-reference vendor/operator/model-brand registry** is excluded from all three totals. These units cannot be combined into a count of physical data centers.

## Cloud directories and overlapping datasets

| Layer | October records | Change and boundary |
|---|---:|---|
| Alibaba Cloud | 171: 38 regions, 133 AZs | Public 33/108, financial 4/20, government 1/5; 34 additional IDs |
| Tencent Cloud | 97: 26 regions, 71 AZs | Current directories list 96 IDs; one August financial AZ is retained with unknown lifecycle/access; 13 additional IDs |
| Huawei Cloud | 31 regions | Global union of IAM identity/API and Resource Formation product membership, plus separately sourced Cloud Connect/trust metadata; 22 additional IDs |
| Volcano Engine | 24: 6 regions, 18 AZs | Auto Scaling directory now includes Johor and Jakarta; seven overseas records were excluded by the older parser |
| Baidu BCC | 27: 8 regions, 19 AZs | Refreshed source; BCC scope |
| Kingsoft KEC | 22: 8 regions, 14 AZs | Refreshed public/financial compute source |
| JD CVM | 14: 4 regions, 10 AZs | Refreshed documentation state parsed as literal data |
| Tianyi Cloud | 63 VPC pools | Refreshed pool labels; 23 AZ-capable pools do not establish child IDs |
| Azure China | 6 regions | Separate AzureChinaCloud partition and 21Vianet operator evidence; no invented AZ children |
| Qiniu QVM | 23: 2 pools, 21 regions | Provider IDs remain scoped to pool 1 or 3; similar Alibaba IDs do not establish upstream hosting |
| AWS core cloud | 147 retained records | Only Beijing/Sinnet and Ningxia/NWCD operator metadata enriched; August inventory dates retained |
| Chindata | 4 partial directory codes | October source retained; lifecycle unknown and code-to-campus mapping unresolved |

The [October 19 Chindata follow-up](chindata-enrichment-options.20261019.md) explains why this layer draws no points, identifies two additional code candidates on regional pages, and proposes campus alias resolution and official location evidence. It is an enrichment recommendation; the retained four-code snapshot remains unchanged.

The eight refreshed Chinese cloud layers now contain 449 records, compared with 373 in the August audit. Qiniu and Azure China add separate product/partition layers. All refreshed location geometry is null because these directory sources do not establish facility coordinates.

The full [Alibaba directory](https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones) supports separate public, financial and government scopes. Closing-down Nanjing/Fuzhou labels do not prove completed closure. Johor marketing declares three AZs while the captured explicit directory names two; the third is not synthesized. The current [Tencent English directory](https://www.tencentcloud.com/document/product/238/7520) and [Chinese CVM directory](https://cloud.tencent.com/document/product/213/6091) agree on all 96 currently itemized IDs. Previously retained Shanghai financial AZ 1 is absent from both; its August retrieval/last-seen dates remain intact.

Huawei membership is product-scoped, with [IAM endpoints](https://support.huaweicloud.com/intl/en-us/api-iam/iam_01_0001.html) and identity policy tables supplying stable IDs. This is neither a universal availability claim nor a complete AZ directory. Volcano retains both explicit IDs and declared counts; Shanghai declares three/listed four, Jakarta declares two/listed three. [Qiniu's source](https://developer.qiniu.com/qvm/4190/region-zone) has an Ulanqab label/ID in a merged cell, which is retained; Tokyo and `ap-northeast-1` appear on separate ambiguous rows, so the latter's geography stays unknown.

[Azure China](https://learn.microsoft.com/en-us/azure/china/overview-operations) operates through Shanghai Blue Cloud Technology Co., Ltd. (21Vianet), a separately identified operator. That relationship does not assign all VNET facilities to Azure. [AWS China](https://www.amazonaws.cn/en/about-aws/china/) identifies Sinnet and NWCD for its two mainland regions. Neither source supplies a complete provider-independent facility inventory.

Seven mainland views repeat 212 IDs: Alibaba general 77 and specialized 30; Tencent general 32 and specialized 20; Baidu 25; Volcano 14; Huawei 14. Hong Kong stays separate. The Russia view remains 91. General and specialized scopes are disjoint within each vendor.

[Legacy reconciliation](../data/china/legacy-reconciliation.20261011.json) inspects all 109 rows across competing Alibaba/Tencent legacy and quarantined Alibaba/Baidu datasets. It emits candidate identity matches, rather than automatically promoting aliases. Legacy geometry and speculative capacity are not inherited; quarantined records remain excluded. Current provider IDs, source labels and product scopes control the canonical outputs.

## AI vendors and service infrastructure

The [AI layer](../data/infrastructure/china-ai-services.20261011.json) contains 135 assertions: 48 documented endpoints/templates, 13 service regions/pools, 61 model-service listings, eight UCloud product-region declarations, four platform declarations and one Alibaba GPU-family catalog. Relationships link service records to the [vendor registry](../data/vendors/registry.20261011.json) and to canonical cloud regions when explicit evidence permits.

- [Alibaba Model Studio](https://www.alibabacloud.com/help/en/model-studio/regions) provides six access/storage regions: Beijing, Singapore, Virginia, Hong Kong, Frankfurt and Tokyo. Global/EU/Japan/Hong Kong/US inference scopes and product support remain separate from the access region. Workspace domain templates are not live customer endpoints.
- [BytePlus ModelArk](https://docs.byteplus.com/en/docs/modelark/region-availability?redirect=1) supplies Johor and Dublin service regions, including documented cross-region routing behavior. ByteDance Seedance is a model brand; it is not a separate physical cloud operator.
- China Unicom's public AI portal provides five pool labels and an itemized model-support matrix. Four general API domains are explicit; Shanghai requires account-manager contact. The Hohhot matrix/endpoint label alias remains unresolved. This product evidence does not replace the missing consolidated ECS inventory.
- Tencent's Hy/Hunyuan documentation supplies model/API ingress metadata, including regional gateway names. Its [August 2026 corporate announcement](https://www.tencent.com/tencent-hy3-now-available-globally-extending-practical-ai-across-products-workflows-and-cloud-services/) identifies Hy as the renamed Hunyuan family. Gateway names do not locate model execution, and an expired August trial is not current free availability.
- DeepSeek, Moonshot/Kimi, MiniMax, Z.ai and SiliconFlow have documented service/API references. SiliconFlow also distinguishes managed service from bring-your-own-cloud offerings. No source-backed physical training/inference facility coordinates were found for these vendors.
- [fal's own profile](https://fal.ai/about) identifies San Francisco headquarters. It is recorded as a global inference platform, with documented queue and model-family listings; headquarters does not establish hosting geography.
- Seedance2.ai's retained terms explicitly disclaim ByteDance affiliation. Its legal entity, corporate jurisdiction and upstream hosting remain unresolved, and direct current terms capture was unavailable. It is an independent unresolved platform reference, not an official ByteDance infrastructure vendor.
- Bilibili's [2025 annual filing](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0416/2026041601346.pdf), published April 2026, reports 116 telecommunications suppliers, four accounting for at least 10% each and 57% combined expenditure. Supplier counts are not data-center counts; obsolete 2022 server totals are not carried forward.

The registry also adds UCloud, Qiniu, SiliconFlow, MiniMax, Z.ai, Kuaishou/Kling and named facility-operator candidates Dataport, Runze, Heying and Meiliyun. Model developer, model brand, API platform, regional operator, colocation provider and named candidate remain different roles. A source-name mention in a recognition list does not resolve facility ownership.

## Facility, carrier and network evidence

The [facility/portfolio layer](../data/infrastructure/china-facilities-and-portfolios.20261011.json) contains 66 assertions. Sixty are named entries in the [final 2025 government green-facility directory](https://www.miit.gov.cn/cms_files/filemanager/1226211233/attach/202512/7ac215f191d84b5c833c9a3d76a6346b.pdf), announced December 29, 2025. These recognition entries preserve Chinese source labels and stable label hashes. They do not assert current operation, operator/ownership resolution, coordinates, or a deduplicated campus inventory. The other six preserve GDS/VNET/Bilibili portfolio claims, Wangsu/Baishan edge totals and a VNET/CATL collaboration. VNET's Q2 2026 capacity facts are retained as indexed first-party evidence because direct capture returned HTTP 403. Undated GDS/edge pages remain undated.

The [carrier layer](../data/infrastructure/china-carrier-links.20261011.json) contains 12 assertions: three submarine systems, three station declarations, two interconnection sites, one backhaul link, two portfolios and a quantum-secured WAN service declaration. [ALC's May 2026 landing milestone](https://www.chinatelecomglobal.com/whats-new/37553) is distinct from completed commercial service. [ADC's 2025 commissioning release](https://www.chinatelecomglobal.com/sc/whats-new/37385) retains design capacity rather than measured lit capacity. [Unicom's 2025 CSR](https://www.chinaunicom.com.hk/en/esg/reports/csr2025.pdf) provides SEA-H2X and Tseung Kwan O L2 references. China Telecom's self-built Chung Hom Kok station and SUNeVision's HKIS-1 share a locality but are not merged. Historical MEGA/backhaul references and the [June 2026 quantum WAN claim](https://www.chinatelecomglobal.com/whats-new/37555) do not manufacture route geometry or independently verified quantum hardware.

The [network layer](../data/network/china-vendor-evidence.20261011.json) retains one measurement run, 23 public endpoint observations, 12 sampled routing origins, two facility registrations and four IX memberships. All 23 sampled literal endpoints completed verified TLS from one unspecified vantage. Only DNS, verified TCP/TLS and unauthenticated `HEAD /` were used; templates were excluded. HTTP errors do not establish service closure or model availability. Timing includes DNS/context setup and is not RTT or inference latency. Bounded RIPEstat, APNIC and PeeringDB context identifies frontend routing/registration relationships; none establishes model execution location or provider-owned facilities.

## Remaining coverage gaps

China Mobile and China Unicom still lack consolidated public ECS directories. Huawei universal AZ availability, Qianfan geography, itemized CDN sites, model execution facilities, installed GPUs/stock and facility ownership/campus aliases remain gaps. A next refresh should prioritize public product exports, service-specific model/region matrices, official operator filings and environmental/energy approvals; then reconcile named sites and aliases. Broader carrier/IX datasets should remain typed evidence until their source supports individual site identity. Named station/cable milestones require later operational evidence.

## Reproduce from retained sources

Install `requirements.txt`, `jq` and Poppler `pdftotext`. Run these commands in order; they use retained evidence and do not contact endpoints:

```sh
python3 -B scripts/update_china_enrichment.py
python3 -B scripts/update_china_ai.py
python3 -B scripts/update_china_facilities.py
python3 -B scripts/update_china_carriers.py
python3 -B scripts/update_china_network.py
python3 -B scripts/report_china_enrichment.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-11
make RETRIEVED_AT=2026-10-11 csv
make check
```

Each normalizer accepts `--output-root` for isolated regeneration; historical snapshots must be present there to reproduce first-seen history. `capture_china_network.py` is a separate live collector with a 24-host/12-IP bound. It must use a new dated snapshot before future live runs; rerunning it would change the immutable observations. Literal JSON embedded in source scripts is parsed as data and never executed.
