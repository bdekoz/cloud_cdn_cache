# AWS and Oracle Gulf enrichment

Follow-up: the [completion review](enrichment-completion.20261019.md) records subsequent additions, completed monitoring, and the remaining source-evidence dependencies. Counts and gaps below describe this document’s original implementation boundary.

Implemented October 19, 2026, for UAE, Saudi Arabia, Bahrain, Oman, Qatar and Kuwait. The [original assessment](gulf-coverage-plan.20261019.md), [frozen pre-implementation manifest](../data/raw/repository/manifest-before-gulf.20261019.json) and [implementation audit](../data/gulf/enrichment-implementation.20261019.json) preserve the review boundary. All sources are indexed in the [bibliography](bibliography.20261019.md), now containing 181 references.

The update preserves all 19 existing Gulf location IDs and the repository's 28,024 canonical location records. It refreshes evidence for 18 Gulf rows and marks the historical Muscat Local Zone's lifecycle unknown. Rows outside the Gulf keep their previous properties, coordinates and retrieval dates. Earlier snapshots remain byte-for-byte intact.

| Addition | Count | Meaning |
| --- | ---: | --- |
| OCI public-region locality points | 4 | Dubai, Abu Dhabi, Jeddah and Riyadh city reference points |
| CloudFront locality points | 5 | Dubai, Jeddah, Riyadh, Muscat and Doha city reference points |
| Interconnect endpoint references | 10 | Deduplicated source labels or explicit operator/site codes; no physical-site total |
| Interconnect memberships | 11 | Five AWS Direct Connect entries and six OCI FastConnect region/endpoint associations |
| Oracle dedicated product references | 6 | EPM-scoped references in OC9, OC21, OC29 and OC36 |
| Prefix declarations | 563 | 488 AWS and 75 OCI rows, with service and region scope retained |

## Locations and unresolved status

The [Gulf locality view](../data/gulf/provider-localities.20261019.geojson) uses the same schema as the China view. Nine provider/service/city points use reviewed GeoNames populated-place IDs and WGS 84 reference coordinates under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). They identify city-level coverage, carry canonical record links, and are excluded from location and physical-site totals. Its report accounts for every input: nine mapped and ten held.

AWS's [region guide](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html) and [AZ guide](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html) establish UAE `me-central-1` and Bahrain `me-south-1`, each with three stable AZ IDs. These eight records remain at country scope with null geometry and no inferred city. The schema's `region` precision is qualified by `properties.geography_scope=country_only`. CloudFront's Bahrain label is also country-scoped; its historical city field is corrected to null without changing its ID.

The current [CloudFront list](https://aws.amazon.com/cloudfront/features/) supplies six Gulf labels but no per-city asset counts. Older counts are preserved under `historical_asset_count`, with their original evidence; current counts are null. The 2022 UAE launch post's Fujairah edge claim remains historical because the current directory does not list Fujairah.

Muscat `mes1-mct1-az1` is absent from the current [Local Zones guide](https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html). Its August source, last-seen date and legacy coordinate remain preserved; the new row records the discrepancy and uses lifecycle `unknown`. Four current AWS prefix declarations still carry network border group `me-south-1-mct-1`. That network evidence does not resolve operational Local Zone status, and absence from the directory does not prove retirement.

Saudi's core AWS region remains planned for December 2026, as stated in the [October 15 migration guidance](https://aws.amazon.com/blogs/migration-and-modernization/how-to-plan-your-migration-to-the-aws-region-in-saudi-arabia/). The launch watch has no invented region or AZ identifiers. An explicit launch statement and published identifiers are required for admission. Saudi CloudFront and IP-geolocation evidence remain independently scoped.

The four [OCI public regions](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm) remain in realm OC1, each with one declared availability domain. No universal AD name or building count is inferred. Oracle EPM's [dedicated-region directory](https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/tsepm/opc_gen_2_regions.html) supplies six additional product references. These use realm-qualified identities, dedicated access scope and unknown lifecycle in the infrastructure collection, outside the public-region inventory.

## Interconnect identity

The [connectivity collection](../data/infrastructure/gulf-cloud-connectivity.20261019.json) separates endpoints from memberships. [AWS Direct Connect](https://aws.amazon.com/directconnect/locations/) and [OCI FastConnect](https://www.oracle.com/cloud/networking/fastconnect/partners/) both identify Equinix DX1, so their memberships link one shared endpoint reference. OCI memberships also link the published OC1 region; AWS region associations are left unasserted.

The operator's [DX1 page](https://www.equinix.com/data-centers/europe-colocation/united-arab-emirates-colocation/dubai-data-centers/dx1) corroborates the code but exposes only a Dubai/postal label in the retained page. The [MC1 page](https://www.equinix.com/data-centers/europe-colocation/oman-colocation/muscat-data-centers/mc1) identifies Barka in the Muscat metro. Barka remains the locality, with Muscat recorded separately as metro.

All ten endpoint references still lack a verified street address. Eight lack independent operator-code corroboration; some directories name only an operator and city. Those entries remain `source_label_only` unless an explicit code is published. The Abu Dhabi Equinix entry is not assigned to AD1 merely by matching its city. No endpoint geometry, ownership inference or region-building identity is admitted.

## Network scope and freshness

The [prefix collection](../data/network/gulf-provider-prefixes.20261019.json) selects AWS UAE/Bahrain region rows from the [AWS public feed](https://ip-ranges.amazonaws.com/ip-ranges.json), and the four OCI OC1 Gulf regions from the [OCI public feed](https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json). AWS rows preserve service and network border group; OCI rows preserve all service tags. There are 318 IPv4 and 245 IPv6 declarations, representing 368 distinct provider/prefix pairs. Overlapping service declarations are not extra addresses or locations.

AWS's [geofeed](https://ip-ranges.amazonaws.com/geo-ip-feed.csv) is joined by exact, covering or contained CIDR overlap. Each match retains its original prefix, labels, source line and overlap relationship. Address coverage uses the union of matched ranges, so overlapping declarations cannot inflate it. Of 293 distinct AWS prefixes, 282 have full geofeed coverage and 11 have none. The report retains 93 GCC geofeed rows with no overlap in the selected AWS regions: 60 Saudi, 16 UAE, 14 Bahrain and three Oman rows. These remain network evidence; none is promoted to a live region or building.

One concrete ambiguity is `13.152.0.0/16`: its region is Bahrain, while overlapping geofeed entries include both Bahrain and Oman labels. All labels and their prefix scopes are retained; the join assigns no single physical locality to that range.

[AWS documentation](https://docs.aws.amazon.com/vpc/latest/userguide/aws-ip-ranges.html) explains that Local Zone geography can differ from its parent region, and public ranges do not cover every service or BYOIP. [OCI documentation](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/addressranges.htm) defines commercial-region ranges and service tags. AWS's retained feed is published October 19; OCI's update timestamp is August 25, 55 days before capture. OCI's timezone-less timestamp is preserved verbatim, its update date is separate from publication date, and `observed_at` records the actual HTTP capture time. No new routing, latency, DNS, origin-hosting or service-health measurements were made.

## Source review and reproduction

The [weekly workflow](../.github/workflows/gulf-source-review.yml) runs Mondays at 08:23 UTC and supports manual dispatch. It checks 12 official sources, compares meaningful directory/feed rows, and uploads raw responses, hashes, capture metadata, JSON differences and a summary as a 60-day Actions artifact. It has read-only repository permission and does not edit datasets or post issues/comments. Changes, fetch/parser errors or an overdue launch review fail the run for attention. GitHub repository Actions settings govern scheduled execution.

Directory comparisons cover Gulf labels; AWS AZ/prefix and EPM identifier monitoring also includes other `me-` entries to catch new identifiers or realm changes. Monitoring scope is broader than admission scope. The report distinguishes current source-row counts from the last reviewed coverage counts (18 reconfirmed, one historical unconfirmed, nine mapped and ten held), reports baseline age and feed age, and never interprets a changed listing as automatic launch or closure. The initial live check completed with all 12 sources parsed and no semantic differences.

Offline reproduction:

```sh
python3 -B scripts/update_gulf_enrichment.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make check
make RETRIEVED_AT=2026-10-19 csv
```

For an offline monitor check, use `python3 -B scripts/check_gulf_sources.py --offline --as-of 2026-10-19 --output-dir /tmp/gulf-review-offline`. Omit `--offline` for a live comparison. The destination must be empty to preserve prior captures. Reviewing a change requires a new dated evidence snapshot, reconciliation of all added/removed identifiers and deliberate baseline updates; the checker never updates its own baseline.

Remaining accuracy work is concrete: verify street addresses and endpoint identities, obtain explicit Muscat/Fujairah status evidence, and review the Saudi launch with provider documentation. These gaps stay visible instead of becoming synthetic facilities.
