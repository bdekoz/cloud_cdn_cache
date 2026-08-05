# Hyperscaler coverage implementation

Date: 2026-08-05

This report records implementation of the public-source portion of the plan in [`hyperscalers.20260804.md`](hyperscalers.20260804.md). The original dataset baseline, [`assessment.20260804.md`](assessment.20260804.md), remains read-only. General refinement methods and the consolidated result are documented in [`methods.md`](methods.md) and [`reassessment.md`](reassessment.md).

## Outcome

Eight new canonical layers add 613 provider-declared records:

| Layer | Records | Canonical unit | Principal boundary |
|---|---:|---|---|
| CoreWeave regions and zones | 63 | 7 super regions + 56 AZs | Provider calls the parents “Super Regions”; no ordinary region hierarchy is invented |
| AWS regions and zones | 147 | 39 regions + 108 stable AZ IDs | AWS reports 123 AZs globally, but only 108 stable IDs are itemized in the retained directory |
| Google Cloud regions and zones | 173 | 43 regions + 130 zones | Product availability is joined from the same Compute table |
| Azure public-cloud regions | 57 | Region | Zone support is a property; subscription-mapped child zones are not manufactured |
| OCI commercial regions | 45 | Region | AD count is retained; tenancy-specific AD names are not made canonical |
| IBM regions and universal zones | 53 | 13 regions + 40 universal zones | 39 account-logical labels remain properties, never physical identities |
| IBM classic data centers | 42 | Stable data-center code | Kept separate from VPC region/zone totals |
| Meta data centers | 33 | Current directory card | Lifecycle is unknown unless the directory explicitly states current status |

The consolidated [`manifest.20260805.json`](../data/manifest.20260805.json) now contains 15,726 canonical records across 27 layers. Its five existing mainland views contain 160 repeated IDs and remain excluded from the canonical count.

All 613 new records have null geometry. Provider locality labels support country, jurisdiction, and descriptive properties, but they do not establish a WGS 84 facility point.

## Corrections to the planning estimate

The retained sources resolved several ambiguities in the 2026-08-04 assessment:

- CoreWeave publishes seven named **super regions** containing 56 AZs. The earlier interpretation of 52 ordinary parent regions was incorrect and is not used.
- AWS publishes 39 launched regions and an aggregate 123 AZs, but its retained stable-ID directory itemizes 108 AZ IDs. The 15-row difference is reported rather than synthesized.
- OCI's current itemized commercial-realm table contains 45 regions. A broader marketing statement of “more than 50” cannot substitute for itemized identities.
- Meta's current directory contains 33 location cards, while an April 2026 article described 32 owned and operated data centers. The current directory is used for membership and the discrepancy is preserved; no lifecycle is inferred from a break-ground year.
- IBM has 39 logical zone slots but 40 stable universal zone names because Dallas exposes four physical candidates for three account-logical slots.

The exact implemented increment is therefore 571 hierarchy/site records plus 42 separately counted IBM classic data centers, or 613 total—not the earlier rough estimate of roughly 660 plus 42.

## Provider methods and semantics

### CoreWeave

The official [AZ directory](https://docs.coreweave.com/platform/regions/all-availability-zones) supplies super-region membership, AZ identity, locality, General or Dedicated Access, and AI Object Storage availability. The [instance matrix](https://docs.coreweave.com/platform/instances/availability-matrix) joins GPU and CPU types to all 18 General Access AZs.

General Access maps to `access_status=public`; Dedicated Access maps to `dedicated`. Seven `super_region` parents preserve provider terminology. The layer contains 18 public and 38 dedicated AZs, including 25 with AI Object Storage.

### AWS

The official [stable AZ directory](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html) supplies 108 account-stable AZ IDs in 34 ordinary commercial regions. Account-mapped letter names are deliberately not identities. China adds `cn-north-1` and `cn-northwest-1`; GovCloud adds `us-gov-west-1` and `us-gov-east-1`; the European Sovereign Cloud adds `eusc-de-east-1`. Partition and realm are explicit properties.

China and GovCloud regions use restricted access. The European Sovereign Cloud remains sovereign but public because the retained launch source says it is available to all customers. Existing Local Zones remain a separate class and now link across layers to `aws:cloud_region:<region-code>`.

### Google Cloud

The official [Compute regions and zones table](https://docs.cloud.google.com/compute/docs/regions-zones) supplies 130 zone IDs, from which 43 published region IDs are structurally recovered. Each zone retains machine-type families, CPU platforms, options, low-CO2 marking, locality label, and its canonical region parent.

Google Cloud remains distinct from the existing Google Edge, owned-data-center, and GGC surfaces.

### Microsoft Azure

The official [Azure public regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list) supplies 57 programmatic region names. Eight are marked restricted and 39 indicate availability-zone support. Pair, geography, and physical-location text are retained as properties.

No child AZ rows are emitted: zone support does not establish globally stable physical identities when subscription mappings can differ.

### Oracle Cloud Infrastructure

The official [regions and availability domains table](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm) supplies 45 commercial-realm region IDs, names, localities, region keys, realm keys, and AD counts. Forty regions report one AD and five report three.

AD names remain noncanonical because they are tenancy-specific. The source-published count stays on each region.

### IBM Cloud

The official [locations directory](https://cloud.ibm.com/docs/overview?topic=overview-locations) supplies 13 regions, 39 account-logical zone labels, 40 universal zone names, and 42 classic data-center codes. Only universal names identify physical zones. Logical labels and their per-account mapping caveat live on region/zone properties.

Classic infrastructure is a separate layer. `DAL08` and `WDC03` retain the provider's government-cloud restriction. `CHE01` is still operational on the assessment date but sales-restricted: end of market was 2026-06-15, new deployments end 2026-12-10, and closure is 2027-06-10.

### Meta

The official [data-center directory](https://datacenters.atmeta.com/all-locations/) yields 33 unique directory cards. Country/state, directory summary, primary information link, social link, and break-ground year are retained. Break-ground year does not prove current operation, so lifecycle is `unknown` pending explicit current project language.

Meta data centers remain separate from FNA, edge/POP, and ASN observation layers.

## Schema and snapshot handling

Schema contract 1.2 adds `super_region` and `access_status=restricted`. It continues to validate retained schema-1.1 records. New outputs use record version 1.2; old 2026-08-04 records remain version 1.1.

The 2026-08-05 manifest is intentionally mixed-date:

- 19 baseline layers and five views still point to their actual 2026-08-04 artifacts;
- eight hyperscaler layers point to 2026-08-05 artifacts;
- assessments remain dated 2026-08-04.

This avoids changing retrieval history merely to create a newer consolidated index.

## Reproduction and validation

Normalize the retained snapshots, rebuild the manifest, and validate with:

```sh
python3 -B scripts/update_hyperscalers.py --retrieved-at 2026-08-05
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-05
make check
```

Take a deliberate new upstream snapshot by adding `--fetch` and a new retrieval date. The updater writes provenance sidecars with the raw path, URL, media type, date, and SHA-256.

The hyperscaler validation suite checks exact source counts, schema conformance, global ID uniqueness, parent integrity, AWS Local Zone cross-links, access/lifecycle semantics, IBM identity boundaries, raw hashes, jq CSV parity, manifest hashes, mixed snapshot tags, and byte-for-byte regeneration.

## Remaining enrichment paths

1. Join AWS service/endpoint availability and add new stable AZ IDs only when AWS itemizes them; do not close the aggregate gap synthetically.
2. Add an Azure sovereign-cloud layer separately and keep zone support region-level until a universal physical identity exists.
3. Track Google product changes as keyed properties and use Location Finder only as a documented cross-check.
4. Monitor OCI realms and AD counts without emitting tenancy labels.
5. Refresh CoreWeave's directory and GPU/CPU matrix monthly, preserving access transitions independently from lifecycle.
6. Review Meta and IBM lifecycle quarterly and on launches/closures; replace `unknown` only with explicit evidence.
7. Continue Alibaba, Tencent, and Huawei product/endpoint enrichment as joins that do not redefine existing stable membership.
8. Keep Meta edge, embedded-cache, colocation, and active-measurement work in separate tracks.

Unauthorized or leaked inventories are excluded. Provider-approved non-public material can be considered only after authority, permitted scope, redistribution terms, retrieval date, and sensitive-field minimization are documented.
