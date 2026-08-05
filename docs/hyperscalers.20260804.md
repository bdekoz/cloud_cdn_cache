# Hyperscaler coverage assessment and plan

Date: 2026-08-04

Implementation note (2026-08-05): the public-source phases are complete and recorded in [`hyperscalers.implementation.20260805.md`](hyperscalers.implementation.20260805.md). Retained-source parsing corrected the rough CoreWeave, AWS, OCI, and Meta estimates below; the corrected exact output is 613 records across eight layers.

## Scope

This is a coverage-priority cohort, not a claim that the providers rank one through ten by revenue, capacity, or capital expenditure. It combines eight customer-facing public clouds with one consumer hyperscale operator and one AI-focused neocloud:

1. Amazon Web Services
2. Microsoft Azure
3. Google Cloud
4. Oracle Cloud Infrastructure
5. Alibaba Cloud
6. Tencent Cloud
7. Huawei Cloud
8. IBM Cloud
9. Meta
10. CoreWeave

The mixed cohort is intentional. Public cloud regions, provider-operated data-center campuses, edge POPs, embedded caches, and GPU-cloud availability zones are different units and must remain separate. ByteDance/Volcano Engine and Baidu are adjacent priority providers already represented by canonical cloud layers; Apple, Crusoe, Lambda, Nebius, Nscale, and Fluidstack belong on the watchlist rather than being silently folded into this ten-provider baseline.

## Executive result

Current core-cloud coverage is much narrower than provider-name coverage suggests:

- Alibaba and Tencent are the only cohort members with broad, itemized region-and-zone hierarchies.
- Huawei has nine product-scoped mainland region records, not a global or universal cloud inventory.
- AWS, Microsoft, Google, and Meta have useful adjacent layers—edge, local zone, data-center, recovery, or observations—but no canonical core-cloud region hierarchy.
- Oracle, IBM, and CoreWeave have no canonical records.

In short, two of ten have meaningful core region/zone coverage, one has partial core coverage, four have adjacent infrastructure coverage only, and three are absent. The most valuable next work is therefore not more geocoding; it is ingesting stable official region, zone, access, realm, lifecycle, and parent identifiers.

The pre-implementation estimate was roughly 660 additional hierarchy or site records plus a separate 42-row IBM classic data-center layer. Retained-source parsing produced 571 hierarchy/site records plus 42 IBM classic data centers, or 613 exact records. The difference comes principally from preserving seven CoreWeave super regions rather than inventing ordinary regions, retaining only 108 itemized AWS stable AZ IDs rather than synthesizing the 123-AZ aggregate, using OCI's 45-row itemized table, and following Meta's current 33-card directory.

## Existing repository coverage

| Provider | Current retained or canonical coverage | What it does not establish | Assessment |
|---|---|---|---|
| AWS | 102 CloudFront metro records, 45 Local Zones, and 217 ASN observations | AWS Regions and ordinary Availability Zones | Adjacent only |
| Microsoft | 110 Front Door metro rows, 128 Front Door code rows, and 1,655 ASN observations | Azure compute regions or zone hierarchy | Adjacent only |
| Google | 65 edge metros, 59 owned data-center directory entries, and 4,247 ASN observations; legacy GGC remains separate | Google Cloud compute regions and zones | Adjacent only |
| Oracle | None | OCI regions, realms, and availability-domain counts | Absent |
| Alibaba | 32 regions and 105 zones | Cross-product availability, endpoints, and richer lifecycle monitoring | Strong core layer |
| Tencent | 22 regions and 62 zones | Cross-product availability and endpoint matrices | Strong core layer |
| Huawei | 9 mainland Cloud Connect-scoped regions | Global membership and itemized AZ identity | Partial core layer |
| IBM | None | VPC regions, stable universal zones, and classic data centers | Absent |
| Meta | 8,360 recovered FNA observations outside the canonical manifest and 2,548 ASN observations | Current provider-declared data-center sites and lifecycle | Adjacent only |
| CoreWeave | None | Regions, AZs, access class, and GPU/service availability | Absent |

Counts in different rows are not additive measures of physical facilities. Front Door codes and metros overlap conceptually; a cloud region can contain several facilities; an observation can reflect network behavior without locating a site.

## Official evidence now available

### AWS

The current [AWS global infrastructure page](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/) reports 39 launched geographic regions and 123 Availability Zones. The [AWS AZ directory](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html) publishes stable AZ IDs, parent region codes, and geography. AZ IDs—not account-mapped letter names—are the correct cross-account identity. China, GovCloud, commercial, and sovereign realms must remain explicit.

Implemented target: 39 `cloud_region` records and 108 itemized stable `availability_zone` records. The 15-AZ difference from AWS's 123-AZ aggregate remains a reported coverage gap. Existing Local Zones remain a distinct class and now link to their canonical parent regions across layers.

### Microsoft Azure

The current [Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list) itemizes 57 public-cloud region rows with programmatic name, physical-location label, geography, paired region, availability-zone support, and restricted-access markings. Microsoft separately documents sovereign clouds.

Immediate target: 57 `cloud_region` records. Do not manufacture three child zones merely because a region supports zones: Azure logical zone-to-physical-zone mapping can be subscription-specific. Retain zone support as a region property until a stable, globally meaningful physical identifier is available.

### Google Cloud

The current [Google Cloud locations page](https://cloud.google.com/about/locations) reports 43 regions and 130 zones. Google also operates the GA [Cloud Location Finder](https://docs.cloud.google.com/location-finder/docs/overview), which updates every 24 hours and provides region/zone hierarchy, provider, location type, and ISO territory for Google Cloud, AWS, Azure, and OCI. Third-party entries are a cross-check, not a replacement for each provider's declaration.

Immediate target: 43 `cloud_region` records and 130 `availability_zone` records. Keep Google Cloud, Google Edge, owned data centers, and GGC as separate services. Cloud Location Finder does not publish facility coordinates, so geometry remains null unless another approved source justifies a labeled centroid.

### Oracle Cloud Infrastructure

Oracle's broader marketing material has reported more than 50 public regions, while the retained [OCI region and availability-domain table](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm) itemizes 45 current commercial-realm regions with name, identifier, location, region key, realm, and availability-domain count.

Implemented target: 45 `cloud_region` records, with realm, region key, and AD count. No globally canonical availability-domain children are emitted from tenancy-specific AD names. Cloud Location Finder can be used as an independent membership and hierarchy cross-check.

### Alibaba Cloud

The retained provider source already yields 32 regions and 105 zones. The current [Alibaba regions and zones guide](https://www.alibabacloud.com/help/en/cloud-migration-guide-for-beginners/latest/regions-and-zones) remains itemized and also exposes closing-down status. Product pages such as [ECS regions and zones](https://www.alibabacloud.com/help/en/ecs/user-guide/regions-and-zones) and [OSS endpoints](https://www.alibabacloud.com/help/en/oss/user-guide/regions-and-endpoints) can enrich product support and endpoints without changing the core identity layer.

Immediate target: preserve membership, monitor lifecycle, and add service-availability joins keyed by stable region/zone ID. Product matrices should not silently redefine the provider-wide layer.

### Tencent Cloud

The retained provider table yields 22 regions and 62 zones. The current [Tencent regions and zones documentation](https://intl.cloud.tencent.com/document/product/416/64284?lang=en) preserves explicit IDs and region/AZ relationships.

Immediate target: preserve membership and add service-specific availability, endpoint, sales restriction, and dedicated-product joins. General public, financial, and automotive cloud scopes remain distinct.

### Huawei Cloud

Huawei's [global infrastructure page](https://www.huaweicloud.com/intl/en-us/about/global-infrastructure.html) reports 34 regions and 102 AZs, while the repository's nine records come only from Cloud Connect's mainland membership. Huawei publishes itemized region/endpoint tables and product-scoped AZ APIs, but the aggregate global count alone cannot generate 102 stable AZ records.

Immediate target: build an itemized global region layer from stable region IDs and make the nine current Cloud Connect records a scoped view or product-membership join. Add AZs only from retained, itemized product responses; label their product scope and authentication basis.

### IBM Cloud

The current [IBM Cloud locations documentation](https://cloud.ibm.com/docs/overview?topic=overview-locations) itemizes 13 regions, 39 account-logical zone labels, 40 stable universal zone names, and 42 classic data-center codes. The counts differ because IBM maps logical zone slots to physical universal zones per account, and Dallas currently offers four universal candidates for three logical slots.

Immediate target: 13 `cloud_region` records and the 40 provider-published universal zones. Store logical zone labels and account-mapping semantics as properties rather than treating them as stable physical identity. Publish the 42 classic data-center codes as a separate layer, join the closure list, and do not add it to region/zone totals.

### Meta

Meta's current [data-center directory](https://datacenters.atmeta.com/all-locations/) itemizes its fleet, and an April 2026 provider article states that Meta has [32 owned and operated data centers](https://about.fb.com/news/2026/04/infrastructure-explained-meta-data-centers/). The directory also includes construction dates and investment/community details. Meta separately describes hundreds of POPs but does not publish an itemized current POP directory.

Implemented target: 33 provider-directory `data_center` records. This preserves the current directory's 33 cards and reports its discrepancy with the earlier 32-site article. Lifecycle remains `unknown` unless current directory/project language explicitly establishes it. Existing FNA and ASN observations remain observation layers, not facility records.

### CoreWeave

CoreWeave's current [All Availability Zones](https://docs.coreweave.com/platform/regions/all-availability-zones) directory itemizes 56 AZs with stable name, location, General or Dedicated Access, and AI Object Storage availability. The source groups them into seven explicitly named **Super Regions**; the earlier 52-region interpretation was incorrect. On the assessment date, 18 AZs are General Access and 38 are Dedicated Access. The [instance availability matrix](https://docs.coreweave.com/platform/instances/availability-matrix) adds GPU and CPU product availability by General Access AZ.

Implemented target: 56 `availability_zone` records under seven `super_region` parents. General Access maps to `access_status=public` and Dedicated Access to `access_status=dedicated`; product availability is a keyed join. Geometry is null because the provider supplies locality labels, not facility coordinates.

## Enrichment model

The following fields have more value than speculative points:

- stable provider region, zone, facility, and realm identifiers;
- parent region and provider hierarchy;
- public, restricted, invite-only, or dedicated access;
- operational, in-development, planned, closing, inactive, or unknown lifecycle;
- jurisdiction and sovereign/commercial realm;
- provider physical-location label and ISO country code;
- product/service availability keyed to canonical location ID;
- public, private, dual-stack, or product endpoint metadata;
- GPU/accelerator family availability for AI clouds;
- source-published pairings, AD/AZ counts, and account-mapping caveats;
- first-seen, last-seen, additions, removals, and source-structure changes.

Coordinates remain null unless a provider supplies WGS 84 coordinates or a separate, reviewed centroid layer is explicitly requested. A locality label does not establish a facility address, and a region or AZ must never be multiplied by a provider's marketing data-center count.

## Implementation plan

### Phase 0: identity and relationship rules

1. Register service IDs for `aws_cloud`, `azure_cloud`, `google_cloud`, `oracle_cloud`, `ibm_cloud`, `meta_data_centers`, and `coreweave_cloud` in the schema documentation.
2. Define provider-specific stable identity: AWS AZ ID, Azure programmatic region name, Google region/zone ID, OCI region identifier, IBM universal zone name, Meta directory slug, and CoreWeave AZ name.
3. Decide how parent links cross class-specific views. Prefer one canonical provider hierarchy with class views over duplicating region records in several layers.
4. Add assertions that account-specific labels are never treated as universal physical IDs.

### Phase 1: missing public-cloud anchors

1. Build CoreWeave first because the provider supplies a compact, complete, high-value itemized directory with access semantics.
2. Add AWS regions and stable AZ IDs; then link the existing Local Zone layer.
3. Add Google Cloud regions and zones from provider sources, using Cloud Location Finder for a daily hierarchy and territory cross-check.
4. Add Azure public regions, restricted status, pairing, geography, and zone-support properties; keep sovereign clouds separate.
5. Add OCI regions, realm, region key, and AD count without manufacturing tenancy-specific AD identities.

### Phase 2: operator and IBM inventories

1. Add IBM regions and stable universal zones, then a separately counted classic data-center layer with closure state.
2. Add Meta's owned-and-operated data-center directory with explicit lifecycle and ownership model.
3. Keep Meta edge and embedded-cache work in an observation track until an itemized provider source exists.

### Phase 3: enrich existing Asian cloud layers

1. Join Alibaba ECS/OSS/product availability and endpoints without changing stable membership.
2. Join Tencent service coverage and preserve general, restricted, and dedicated products separately.
3. Expand Huawei to a global itemized region layer; add only product-scoped AZs returned by approved, retained sources.
4. Continue monitoring Baidu and ByteDance/Volcano as adjacent hyperscale providers already in the canonical dataset.

### Phase 4: recurring operation

- Refresh machine-readable location APIs weekly.
- Refresh provider documentation and CoreWeave's AZ/product matrices monthly.
- Review Meta and IBM site lifecycle quarterly and on announced openings or closures.
- Snapshot every raw response with retrieval date, URL, media type, checksum, and license note.
- Produce semantic diffs for IDs, parents, access, lifecycle, realms, product availability, and aggregate/source discrepancies.

## Acceptance gates

A provider layer is publishable only when:

1. membership comes from an approved provider source or an explicitly labeled independent cross-check;
2. every record has a stable, documented identity rule;
3. parent relationships and access/lifecycle meanings are source-supported;
4. source counts and structural expectations are asserted;
5. planned, restricted, dedicated, sovereign, and product-scoped entries are not flattened into ordinary public capacity;
6. geometry is null unless its method, CRS, and precision are defensible;
7. raw provenance and deterministic regeneration pass;
8. derived CSV parity and the complete `make check` suite pass.

Unauthorized or leaked inventories remain excluded. Provider-approved non-public exports can be considered only with documented authority, permitted use, redistribution terms, retrieval date, and sensitive-field minimization.

## Recommended first increment

Completed on 2026-08-05: CoreWeave, AWS, Google Cloud, Azure, OCI, IBM, IBM classic, and Meta were published as eight separate layers with stable identities and source-specific gates. The next reviewed work is keyed product/endpoint enrichment for Alibaba, Tencent, and Huawei plus recurring lifecycle and source-structure monitoring; those joins must not destabilize canonical IDs.
