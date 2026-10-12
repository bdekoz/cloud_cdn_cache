# China vendor coverage review and enrichment plan

Reviewed: 2026-10-11. This is a coverage assessment and plan, not an implementation
of the proposed location refresh. The review covers 31 vendors/platforms and 25
primary-source pages or filings. Some sources are indexed first-party extracts;
their capture method, publication/update dates and retrieval limitations are explicit.

## Finding

The repository has useful Chinese public-cloud hierarchies but incomplete coverage
of overseas offerings, operated cloud partitions, AI service deployment, consumer
content delivery, carrier pools and physical facilities. Vendor-name coverage
overstates infrastructure coverage. Current directories also differ from the August
snapshots, making freshness and scope reconciliation the first priority.

The eight existing Chinese cloud layers contain 373 canonical records across Alibaba,
Tencent, Baidu, Huawei, Volcano, Tianyi, Kingsoft and JD. These are regions, zones
and resource pools, not 373 data centers. Chindata contributes a separate four-code
partial facility directory. Five mainland views repeat 160 canonical IDs and must
not be added to the totals. This review adds zero canonical locations.

The structured outputs are:

- [Vendor assessment and computed ID differences](../data/china/vendor-coverage-assessment.20261011.json).
- [Reviewed source facts and capture limitations](../data/china/review-evidence.20261011.json).
- [Vendor-specific priorities and enrichment phases](../data/china/enrichment-plan.20261011.json).

## Overlapping and competing datasets

| Dataset role | Examples | Reconciliation rule |
|---|---|---|
| Canonical provider hierarchy | Alibaba 137; Tencent 84 | Stable provider IDs, dated source, product scope |
| Derived jurisdiction/access view | Alibaba mainland 73; Tencent general 31 and specialized 17 | Subset of parent IDs; exclude from additive counts |
| Legacy retained file | `alibaba_cloud_data_centers_2.geojson` 19; `tencent_cloud_data_centers.geojson` 41 | Historical alias candidates; not current canonical inventories |
| Quarantined claim layer | Alibaba 14; Baidu 35 | Retain exclusions and reasons; no authoritative inheritance |
| Product-specific inventory | BCC, Cloud Connect, ECS, VPC pools, Model Studio | Preserve product scope; compare shared IDs without assuming equal availability |
| Marketing or portfolio claim | CDN nodes, Huawei global totals, colocation MW | Dated aggregate assertion; never synthesize sites or child IDs |
| Network/independent observation | ASN, routing, IX, DNS/TLS/HTTP | Separate evidence; does not establish facility ownership |

The new assessment hashes and profiles all nine selected canonical vendor layers,
their five derived views, and four legacy/quarantined files. This is an inventory of
overlap, not a completed row-by-row legacy alias merge. The August public-cloud,
China-edge and colocation assessments remain historical baselines.

Identity keys must include provider/operator and offering. For example, Qiniu's
QVM documentation contains Alibaba-style region tokens but also separate pool-three
IDs. Similar tokens do not establish the underlying host or shared ownership.
The [QVM directory](https://developer.qiniu.com/qvm/4190/region-zone) explicitly
separates resource pools and their product availability.

## Current cloud directory differences

| Provider | Retained canonical layer | Reviewed directory | Enrichment candidates |
|---|---|---|---|
| Alibaba | 32 regions + 105 AZs | Public: 33 + 108; finance: 4 + 20; government: 1 + 5 | 34 additional IDs across all scopes; no old IDs absent |
| Tencent | 22 regions + 62 AZs | Public: 21 + 56; specialized: 5 + 14 | 13 additional IDs; one old finance-zone ID absent |
| Huawei | 9 mainland Cloud Connect regions | Global marketing: 34 regions/103 AZs; trust selector: 18 labels | Global and product-specific identity reconciliation |

Alibaba's [directory](https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones),
updated October 10, lists Brazil `sa-east-1` and its two zones, plus Seoul zone
`ap-northeast-2c`, outside the retained public inventory. Finance and government
sections account for the other 30 additional IDs. Beijing Finance is labeled preview;
Nanjing and Fuzhou local regions are labeled closing down. These require lifecycle
and access treatment, rather than a uniform operational-public classification.
Review the four August records with unknown jurisdiction before rebuilding the
mainland view; the current directory explicitly places the closing-down local
regions in China.

Alibaba's [marketing location page](https://www.alibabacloud.com/en/global-locations)
declares three Johor AZs, while the directory explicitly supplies only two IDs. Keep
the disagreement visible and do not invent a third ID. Partner-region operation,
closing-down regions, and dedicated finance/government scope also explain why
different provider pages cannot be expected to have identical totals.

Tencent's [CVM directory](https://www.tencentcloud.com/document/product/213/6091),
updated September 18, adds Johor Bahru, Osaka, Queretaro and Zhongwei automotive
region IDs, plus additional explicit zones. The old `ap-shanghai-fsi-1` is absent
from this reviewed table; that alone does not establish closure. Asterisks indicate
sales availability differences. The retained international dedicated-host source
and current CVM source must be compared by product and edition before publication.

Huawei's [global page](https://www.huaweicloud.com/intl/en-us/about/global-infrastructure.html)
provides an aggregate and mentions partner nodes. Its
[trust-center selector](https://www.huaweicloud.com/intl/en-us/securecenter/data_protection/region_query.html)
provides named service regions, including overseas coverage. Neither is a complete
stable AZ directory. Join IAM identifiers, service matrices and operator roles
without expanding aggregate numbers into guessed facilities.

## Requested platforms and AI services

| Vendor or name | Classification and supported finding | Main gap |
|---|---|---|
| Alibaba / Qwen | Public cloud and model-service platform; six Model Studio access/storage regions | Model/execution scopes and feature availability absent from current layers |
| Tencent / Hunyuan | Public cloud; financial/automotive scope separate | Hunyuan deployment/endpoint matrix not reviewed here |
| ByteDance / Volcano / Seedance | Cloud offering and model developer; official Seedance belongs to ByteDance Seed | Ark/BytePlus product coverage and developer-host relationships |
| Bilibili | Consumer platform and content delivery; supplier infrastructure disclosed | No vendor/CDN location layer or verified facility directory |
| DeepSeek | Model developer and direct API operator | Training/inference facilities and third-party serving relationships |
| Moonshot / Kimi | Separate China/overseas open-platform and coding endpoints | Endpoint audience does not establish physical deployment or storage geography |
| fal | Generative-media inference platform headquartered in San Francisco | Global platform coverage and model-serving relationships |
| seedance2.ai | Independent application platform; indexed terms disclaim ByteDance affiliation | Legal jurisdiction, upstream service provenance and hosting unresolved |

Alibaba [Model Studio](https://www.alibabacloud.com/help/en/model-studio/regions)
lists Beijing, Singapore, Frankfurt, Tokyo, Hong Kong and Virginia. Access/storage
region and inference execution scope are separate: Global execution can use a
different pool of compute resources. This should become product deployment evidence,
not six inferred new data centers or a claim that every model runs in every region.

The official [Seedance page](https://seed.bytedance.com/en/seedance2_0) identifies
ByteDance Seed and links a BytePlus playground. Its current navigation also lists
Seedance 2.5, so the requested 2.0 name should not freeze the catalog. BytePlus
[ModelArk region documentation](https://docs.byteplus.com/en/docs/modelark/region-availability?redirect=1)
lists Johor `ap-southeast-1` and Dublin `eu-west-1`, with possible cross-region
inference routing. Do not interpret its `ap-southeast-1` token as Singapore merely
because another vendor uses that token there. The indexed regional content and
reader-visible September 28 update are retained separately from a failed full-body
read; refresh the full document before canonical ingestion.

DeepSeek's [direct API documentation](https://api-docs.deepseek.com/) establishes
an endpoint. Its [identity policy](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html)
names Hangzhou DeepSeek Artificial Intelligence Co., Ltd.; a registered address does
not locate compute. Third-party hosted DeepSeek models require separate host records.
Kimi's [official FAQ](https://www.kimi.com/en/help/kimi-code/faq) distinguishes four
base URLs by service and audience, but does not provide facility coordinates.

[fal's own description](https://fal.ai/about) establishes San Francisco headquarters.
It belongs in a global inference-platform track linked to Chinese model developers.
The indexed [seedance2.ai terms](https://seedance2.ai/zh-hant/terms-of-service),
updated October 29, 2025, explicitly disclaim ByteDance affiliation. Direct retrieval
failed, so this is an identity finding with freshness limits, not a verified China
operator or a proven official Seedance reseller.

Bilibili's current [2025 annual report](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0416/2026041601346.pdf),
published April 16, 2026, reports 116 telecom suppliers for servers and bandwidth;
four suppliers met the expenditure threshold and jointly accounted for 57% in 2025
(printed page 126). This establishes supplier dependence, not 116 facilities.
Older indexed server totals were not adopted as current inventory. Named operators,
public endpoints, registry relationships and measured delivery observations are
the practical next evidence sources.

## Largest remaining gaps and new vendors

1. **Cloud identities and operated partitions.** Refresh Alibaba/Tencent first,
   expand Huawei globally, then ingest Azure China independently. Microsoft's
   [China region list](https://docs.azure.cn/en-us/reliability/regions-list), updated
   October 5, names six regions; `chinaeast3` is restricted and `chinanorth3` explicitly
   supports AZs without publishing child IDs. The retained Azure global layer has
   zero China rows. AWS already has Beijing/Ningxia `aws-cn` region rows, but no
   stable child AZ inventory. Preserve the
   [21Vianet operator relationship](https://learn.microsoft.com/en-us/azure/china/overview-operations)
   and product-availability differences.
2. **Carrier pools and AI deployment.** China Mobile remains a source gap; province
   filters on its marketplace do not identify pools. China Unicom's
   [AISP promotion section](https://support.cucloud.cn/document/127/591/2357.html?arcid=7011&id=2357)
   names Hohhot, Wuhan, Jinan and Guiyang pools with four base URLs. The promotion
   dates and August update differ; verify current availability and pool IDs before
   treating it as a live service directory. This advances a product-specific source
   gap without pretending to supply general ECS coverage.
3. **New cloud vendors.** Add UCloud and Qiniu. The
   [UCloud UPHost directory](https://docs.ucloud.cn/uphost/concepts/az) itemizes
   eight bare-metal product regions, including Quanzhou GPU availability. Scope it
   to that product and join stable IDs before generalizing across UCloud.
4. **New model and inference vendors.** Add
   [SiliconFlow](https://docs.siliconflow.com/en/userguide/introduction),
   [MiniMax](https://platform.minimax.io/docs/api-reference/api-overview),
   [Z.ai/GLM](https://docs.z.ai/guides/overview/quick-start), and
   [Kuaishou/Kling](https://ir.kuaishou.com/news-releases/news-release-details/kling-ai-celebrates-first-anniversary-achieves-annualized).
   Their sources establish offerings or identity, not complete facility inventories.
   Keep developer, API operator, managed serving, BYOC and underlying host distinct.
   StepFun, SenseTime, Zhipu legal/brand mapping and other candidates merit subsequent
   identity/source discovery; this review does not claim complete coverage of them.
5. **Physical and network infrastructure.** Extend Bilibili/ByteDance/Kuaishou
   delivery evidence; refresh GDS/VNET/Chindata and Wangsu/Baishan. Add itemized
   carrier backbone, IX, cross-border fiber, AI compute hubs and power/cooling
   dependencies when useful sources emerge. Campus, building, GPU product support,
   installed compute and MW are separate evidence units. Province coverage, IP
   geolocation and IX membership are not owned-facility evidence.

An additional cross-vendor directory is the final
[MIIT 2025 green computing facilities list](https://www.miit.gov.cn/cms_files/filemanager/1226211233/attach/202512/7ac215f191d84b5c833c9a3d76a6346b.pdf),
attached to the [December 29 announcement](https://www.miit.gov.cn/jgsj/jns/gzdt/art/2025/art_d8a6906d6e5048369ae66b3a40ea20b8.html).
Its 60 entries include Douyin-associated building 6, DataPort/Alibaba Heyuan building
C, Alibaba Fengjing building B, Kuaishou Ulanqab building B1, Meili Cloud Zhongwei
C1, Heying Huailai ND11 and Runze A-8. DataPort, Runze, Heying and Meili Cloud are
additional operator candidates in the assessment. Verify legal names, operation
roles and building/campus aliases before generating facilities. The earlier
consultation draft is a separate edition; recognition in 2025 does not establish
current operation, ownership, facility coordinates or a cloud region assignment.

## Implementation sequence and reproduction

The serialized plan orders identity/dataset reconciliation, core cloud refresh,
AI/new-vendor service layers, physical/network expansion, and independent observation
or monitoring. Each phase has deliverables and acceptance criteria. No API calls
requiring credentials, active measurements, paid exports, or inferred coordinates
were executed in this review.

The fact collection is a curated source-backed input, not original raw HTML. The
assessment hashes that input and the plan, profiles retained files, and derives
itemized directory comparisons offline:

```sh
python3 -B scripts/assess_china_coverage.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-11
make check
```

Source retrieval limitations include shell DNS failure; inaccessible Bilibili IR
directory pages (resolved using the current HKEX filing); seedance2.ai direct page
errors; a large Unicom document rejected by the reader; and BytePlus's reader shell.
Dates and extract methods identify which findings need a fresh source capture before
location ingestion. Canonical location, network and infrastructure counts remain
27,395, 3,125 and 84 respectively.
