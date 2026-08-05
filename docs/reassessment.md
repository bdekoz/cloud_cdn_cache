# Post-refresh Dataset Reassessment

Date: 2026-08-04

This is a new assessment of the implemented refinement work. The original [`assessment.20260804.md`](assessment.20260804.md) is the immutable baseline and is not revised here. Methods and reproducibility details are in [`methods.md`](methods.md).

## Outcome

The repository now has a defensible normalized update path for the highest-priority provider layers. Historical files remain available, while refreshed sources are archived with hashes and generated into schema-validated CSV and GeoJSON. Provider declarations, inferred coordinates, independently observed ASN presence, and quarantined claims are now explicitly separated.

The refresh adds 14,957 canonical records: 124 Google records, 1,195 records across nine additional authoritative source layers, and 13,638 independent provider/ASN observations. These counts describe unlike entities and must not be added together as a physical-site total.

## Current normalized coverage

| Layer | Normalized records | What a record means | Geometry |
|---|---:|---|---:|
| Google Edge | 65 | Provider-declared edge metro | 65 points |
| Google owned data centers | 59 | Directory entry; 27 are in development | 12 points, 47 null |
| Cloudflare | 338 | Geographic status-API component/site code | 243 points, 95 null |
| Azure Front Door | 110 | Listed metro with explicit asset count | 104 points, 6 null |
| Azure Front Door codes | 128 | Provider abbreviation-directory row | 97 points, 31 null |
| AWS CloudFront | 102 | Standard-POP metro with explicit asset count | 56 points, 46 null |
| AWS Local Zones | 45 | Currently available Local Zone ID | 41 points, 4 null |
| Fastly | 164 | Provider POP ID | 164 provider points |
| CacheFly | 87 | Explicit location; one is planned | 63 points, 24 null |
| Alibaba Cloud | 137 | 32 public regions plus 105 availability zones | 83 regional centroids, 54 null |
| Tencent Cloud | 84 | 22 regions plus 62 availability zones | 75 regional centroids, 9 null |
| June 2026 observation layer | 13,638 | Positive provider/ASN TLS observation | 13,638 null |

Null geometry is an intentional representation of missing coordinate evidence. Regional or city centroids do not imply facility precision.

## Material improvements

- A provider-neutral JSON Schema now distinguishes edge POPs, regional caches, data centers, cloud regions, availability zones, Local Zones, embedded caches, and observed presence.
- Every generated record has a stable ID, provenance URL, raw snapshot reference and SHA-256, source/retrieval dates, lifecycle and source scope, location precision, coordinate method, and confidence.
- Provider site/region/zone IDs are preserved where published instead of collapsing them to city labels.
- Repeated Azure and CloudFront rows are replaced by one metro record with explicit `asset_count`.
- Cloudflare live health is retained separately from lifecycle status.
- Fastly's 164 POP IDs and provider-published approximate coordinates are retained instead of reducing the layer to 80 metros.
- Alibaba and Tencent are rebuilt from official region and availability-zone IDs.
- Apple is present for the first time through 974 independent ASN observations.
- Provider-declared infrastructure and independent measurements are published as different layers and cannot silently overwrite each other.
- Unsupported Baidu global claims and an uncited Alibaba capacity-estimate layer are quarantined without deleting or altering their bytes.

## Reconciliation findings

Machine parsing exposed three internal source inconsistencies that aggregate marketing figures conceal:

- The Azure table contains 107 commercial metros representing 191 assets and three US Government metros. Page prose claims 109 commercial metros, 192 commercial assets, and four government assets.
- The AWS CloudFront city list contains 102 standard-POP metros whose counts sum to 749. Page prose says 750+ standard POPs in 100+ cities, and separately reports 15 regional caches and 1,140+ embedded POPs without itemized locations.
- CacheFly's explicit country lists contain 87 locations, including Marseille as coming soon, while its regional headings sum to 88.

Both sides of each discrepancy are retained in machine-readable reports. No synthetic record was added merely to force agreement with an aggregate claim.

## Independent observation coverage

The June 2026 TLS study contributes positive presence observations for seven providers:

| Provider | ASN observations |
|---|---:|
| Google | 4,247 |
| Netflix | 2,903 |
| Meta | 2,548 |
| Microsoft | 1,655 |
| Akamai | 1,094 |
| Apple | 974 |
| AWS CloudFront | 217 |

The published provider CSVs contain ASN and AS name only. They therefore produce ASN-scoped records with null geometry, not reconstructed locations. The layer is useful for network-presence analysis but cannot establish appliance counts, physical facilities, or exhaustive coverage. The source page states no explicit data license, so the provenance and report require redistribution review.

## Remaining gaps and next enrichment paths

1. Coordinate completeness remains uneven. Future enrichment should prefer provider coordinates, then reviewed PeeringDB/facility evidence. Bulk geocoding should remain separate and must not imply facility accuracy.
2. CloudFront regional and embedded POP aggregates lack itemized provider location evidence. Do not expand them into points until an authoritative list is available.
3. Cloudflare, Azure, CloudFront, CacheFly, Alibaba, and Tencent need scheduled semantic diffs so additions, retirements, renames, and count changes are reviewed rather than overwritten.
4. Current ASN observations should be enriched only from a licensed detailed source or a newly reproducible measurement run. IP, prefix, country, and city evidence should retain observation time and method.
5. PeeringDB can add facility and IX relationships; RIPEstat can add prefix origin and RPKI context; RIPE Atlas can add sampled latency/reachability. These should be evidence tables linked by ASN or stable site ID, not replacements for provider declarations.
6. The historical Akamai layer still needs a defensible current abstraction. Akamai's embedded platform scale is not comparable to the repository's old map markers.
7. Baidu remains excluded until each claimed location has authoritative evidence and stable identifiers.
8. Source-specific licensing and redistribution terms require a formal manifest review before wider publication of raw snapshots or independent downloads.

## Verification status

The validation suite checks schema conformance, stable-ID uniqueness, raw hashes, CSV/GeoJSON parity, nullable geometry, provider-specific semantic counts, quarantine evidence, and byte-for-byte regeneration. At this assessment date it passes for all 14,833 non-Google records in the new authoritative and observation pipeline; the separate Google and recovery suites also pass.

Recommended update flow:

`fetch → checksum/raw snapshot → parse → normalize → validate → semantic diff → review → publish`

Suggested starting cadence is weekly for APIs, monthly for documentation pages, and quarterly or release-driven for independent measurements.
