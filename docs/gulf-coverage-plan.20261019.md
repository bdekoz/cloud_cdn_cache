# AWS and Oracle Gulf coverage and accuracy plan

Reviewed October 19, 2026, covering UAE, Saudi Arabia, Bahrain, Oman, Qatar and Kuwait. This is an assessment and proposed implementation sequence; AWS and Oracle canonical layers are unchanged. The [machine-readable review](../data/gulf/aws-oracle-coverage.20261019.json) includes the full baseline, retained evidence and acceptance criteria. Sources are indexed in the [bibliography](bibliography.20261019.md).

**The baseline has 19 Gulf records; 18 have null geometry.** A mostly empty map therefore understates the inventory already present. Missing geometry, missing deployment records, stale evidence and unresolved source conflicts require different repairs.

| Existing layer | Gulf records | Geometry missing | Finding |
| --- | ---: | ---: | --- |
| AWS regions and AZs | 8 | 8 | UAE and Bahrain regions, each with three stable AZ IDs |
| CloudFront | 6 | 6 | Dubai, Jeddah, Riyadh, Muscat, Doha and a country-level Bahrain label |
| AWS Local Zones | 1 | 0 | Historical Muscat entry; current directory discrepancy |
| OCI public regions | 4 | 4 | Dubai, Abu Dhabi, Jeddah and Riyadh |

## AWS

The current [region guide](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html) confirms `me-central-1` as Middle East (UAE) and `me-south-1` as Middle East (Bahrain). The [AZ guide](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html) lists `mec1-az1`–`mec1-az3` and `mes1-az1`–`mes1-az3`. This supports country/region identity, not a Dubai facility assignment. A UAE region marker should retain country precision unless better evidence establishes its locality.

The Saudi region remains **planned**, with a December 2026 launch expected in AWS's [October 15 migration guidance](https://aws.amazon.com/blogs/migration-and-modernization/how-to-plan-your-migration-to-the-aws-region-in-saudi-arabia/). Its absence from the current live-region layer is not an omission to repair by inventing a code or AZs. Saudi edge presence is a separate matter: [CloudFront's current list](https://aws.amazon.com/cloudfront/features/) includes Jeddah and Riyadh, already retained in the dataset.

[Direct Connect's current directory](https://aws.amazon.com/directconnect/locations/) supplies five Gulf entries: two in Manama, one in Muscat, Equinix DX1 in Dubai and the Etisalat Smart Hub in Fujairah. These are useful interconnect additions, with site/operator matching still required. They do not establish the addresses of AWS region buildings.

Two discrepancies need explicit handling. The [2022 UAE launch post](https://aws.amazon.com/blogs/aws/now-open-aws-region-in-the-united-arab-emirates-uae/) mentions a Fujairah CloudFront location, while the current features list names only Dubai for UAE. Separately, the retained Muscat Local Zone `mes1-mct1-az1` is absent from the freshly captured [available Local Zones guide](https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html), which yielded no Gulf rows. Preserve both historical assertions and flag the listing differences; neither absence proves closure.

## Oracle

The [OCI region directory](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm) confirms all four existing Gulf public entries in realm `OC1`: `me-dubai-1`, `me-abudhabi-1`, `me-jeddah-1` and `me-riyadh-1`. Each has one declared availability domain. Their city labels support separate locality reference points. An availability-domain count does not disclose a building count, and tenancy-prefixed AD names should not become invented universal site IDs.

The [Oracle EPM directory](https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/tsepm/opc_gen_2_regions.html) supplies six additional, product-scoped dedicated-region references: Muscat in `OC9`, Doha in `OC21`, two Abu Dhabi references in `OC29`, and Riyadh/Al Khobar in `OC36`. These belong in a separate scoped evidence collection. Their appearance in a SaaS directory does not establish general public OCI access. The retained [Oracle SDK registry](https://github.com/oracle/oci-java-sdk/blob/master/bmc-common/src/main/java/com/oracle/bmc/Region.java) is useful for identity corroboration, with registration alone insufficient to establish launch or physical location.

[FastConnect's partner/location directory](https://www.oracle.com/cloud/networking/fastconnect/partners/) yields six Gulf region/site relationships: one for Riyadh, two for Jeddah, one for Abu Dhabi and two for Dubai. These can enrich interconnect coverage without equating an on-ramp with a region data center.

## Recommended implementation order

| Priority | Work | Acceptance criterion |
| --- | --- | --- |
| P0 | Add four OCI and five explicitly city-named CloudFront locality points using the China locality-view pattern | Keep the country-only Bahrain label and AWS core geography at country precision; no inferred building coordinates or additions to facility totals |
| P0 | Refresh region identities and retain a separate Saudi launch watch | Stable provider/service/realm-qualified IDs; no Saudi live-region assertion before launch evidence and published identifiers |
| P0 | Resolve the Muscat Local Zone listing discrepancy | Historical evidence retained; explicit provider status needed before retirement |
| P1 | Add five AWS interconnect entries and six Oracle region/interconnect relationships | Deduplicate endpoints separately from relationships; verify operator/address; retain original coordinate CRS if coordinates become available |
| P1 | Normalize the six Oracle dedicated product references | Keep `OC9`, `OC21`, `OC29` and `OC36` separate from public `OC1`; retain product and access scope |
| P2 | Join official prefix feeds/geofeeds and corroborating network observations | Network registration, routing, edge location and application-origin evidence remain distinguishable |
| P2 | Add weekly source-change checks and planned-launch review | Track publication, assertion and retrieval dates; alert on missing IDs and parser changes; show listed, mapped, held and stale counts separately |

Use composite identities: **AWS `me-central-1` is UAE, while Alibaba's is Riyadh; Alibaba `me-east-1` is Dubai, while Huawei's is Riyadh.** Joining on the region string alone would introduce cross-provider geographic errors. Certification jurisdiction, Outposts product availability, network registration and service health also need separate fields; none establishes a deployed facility address.

No periodic job or network measurements were started. Proposed changes should preserve all existing IDs and dated snapshots, pass schema and source-hash checks, account for every added/held/removed listing, and leave country-only regions unlocated at finer precision.
