# Microsoft infrastructure enrichment — 2026-10-21

Microsoft is represented as a global cloud, network, service-residency and
datacenter operator with separate third-party capacity relationships. The
public evidence supports broad geographic coverage, but it does not expose
a complete owned/leased property inventory. This release therefore expands
coverage without presenting a count of unique Microsoft buildings.

The current consolidated source is
[`data/manifest.20261021.json`](../data/manifest.20261021.json). The October 19
manifest and all earlier data remain unchanged. Other vendors retain their
existing snapshot dates and contents.

## Coverage delivered

| Collection | Records | Unit and interpretation |
| --- | ---: | --- |
| Front Door metro directory | 110 | 107 commercial metro rows and three government location rows; a row can describe several POPs. |
| Front Door abbreviation directory | 128 | Published code/location rows, including combined abbreviations. Overlaps the metro directory. |
| Microsoft global-network map | 206 | Distinct published network POP identifiers; 201 unspecified-type entries and five explicitly typed AI POPs. Overlaps Front Door; not another additive facility inventory. |
| Azure public-cloud directory | 58 | Published region identities, including the planned Taiwan North entry. India South Central is new relative to the retained August snapshot. |
| Additional announced regions | 7 | Globe entries absent from the public-region table: East US 3, Greece Central, North Europe 3, North Europe 4, Saudi Arabia East, Southeast Asia 3 and Thailand South. Internal globe IDs are not asserted programmatic Azure names. |
| Azure Government | 5 | Three general government regions and two DoD-only regions, with restricted access. |
| Azure China | 6 | Refreshed 21Vianet-operated region identities; Microsoft ownership and direct operation are not asserted. |
| Datacenter community assertions | 67 | Locality/phase statements from all forty-one listed community pages. Country, state, county, metro and city scope remain distinct. Japan's intro supplies no local datacenter assertion. |
| Microsoft 365 locality assertions | 56 | Distinct country/city pairs from both country and macro-region tables; repeated macro memberships are deduplicated. |
| ExpressRoute assertions | 124 | Directory location groups and disclosed host labels, including commercial, government and China sections. Interconnection does not establish Microsoft-owned compute hosting. |
| Third-party capacity agreements | 7 | Dated IREN, Nebius, Nscale/Start Campus/Ionic Digital and G42/Khazna relationships, with explicit scope and lifecycle qualifications. |
| Geographic locality view | 96 | Provider/service/locality references linked to claims, excluded from canonical totals and carrying zero facility weight. |

The consolidated manifest now contains 28,243 location-schema records across
forty-two layers, 683 infrastructure assertions across ten layers, six
geographic-footprint views and 365 bibliographic references. The location
increase is 219 records. Historical observations, network evidence and
derived location views keep their original counts and evidence dates.

The [source catalog](../data/raw/microsoft-enrichment/catalog.20261021.json)
contains seventy retained sources, including a selected-row GeoNames
gazetteer. Each capture has its URL, retrieval date, available publication or
update date, capture method and SHA-256. IREN's direct HTTP request returned
403; its retained primary-page evidence is explicitly a web-reader extraction.
The selected GeoNames rows retain the downloaded archive hash, member name
and CC BY 4.0 attribution. Other publisher terms remain source-specific.

## Vendor assessment

Azure's [public-region directory](https://learn.microsoft.com/en-us/azure/reliability/regions-list)
provides useful programmatic identities, access restrictions, paired-region
information and availability-zone declarations. Those are the controlling
fields for the public-cloud hierarchy. The
[globe directory](https://datacenters.microsoft.com/globe/explore/) adds
announced-region coverage and supplementary map references. When the sources
use different identifiers or stale lifecycle wording, both scopes are retained
instead of treating a map label as an API identity or opening announcement.

Government and China are separate service partitions. The
[Government overview](https://learn.microsoft.com/en-us/azure/azure-government/documentation-government-welcome)
and [DoD documentation](https://learn.microsoft.com/en-us/azure/azure-government/documentation-government-overview-dod)
support three general government and two DoD-only regions.
[Azure China operations](https://learn.microsoft.com/en-us/azure/china/overview-operations)
identify the 21Vianet operating relationship. These distinctions matter when
evaluating service access and operating responsibility; brand affiliation does
not make every facility Microsoft-owned.

The [community directory](https://local.microsoft.com/communities/) is useful
for explicitly disclosed construction and operating localities. Its forty-one
pages were traversed in full. Only the introductory datacenter statements
enter this bounded release; towns mentioned solely as recipients of community
benefits do not become datacenter locations. Introductory construction wording
can coexist with a later cloud-region opening because a project phase and a
service region are different units. More detailed project articles remain a
future source of finer campus and phase identities, not an omitted private
facility inventory.

[Microsoft 365 residency cities](https://learn.microsoft.com/en-us/microsoft-365/enterprise/m365-dr-datacenter-locations)
expand service-level geography. All country-table cities and named cities in
the macro tables are reconciled, including Helsinki, Dublin and Amsterdam,
which appear outside the country table. Residency declarations cannot identify
the building used by a particular tenant. Similarly,
[ExpressRoute host locations](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-locations-providers)
provide connectivity evidence, not a guarantee that Azure compute is hosted
in every listed building.

Microsoft is therefore a geographically broad candidate for cloud deployment,
but region membership alone cannot establish product availability, capacity,
latency, workload eligibility or a particular data-residency outcome. This
work evaluates infrastructure evidence; it does not perform account-level
capacity checks, procurement pricing, benchmarks or contractual review.

## Ownership and affiliated capacity

The partner layer retains IREN Childress, Nebius Vineland, Nscale Narvik,
Nscale/Start Campus Sines, Nscale's Texas capacity, G42/Khazna's UAE expansion
and the disputed Loughton relationship. Locality references are admitted for
Childress, Vineland, Narvik and Sines only. The Texas agreement does not
establish a city in the selected disclosure; the UAE announcement is
country-scoped. Expected delivery dates are not promoted to observed operation.

Loughton is retained with `lifecycle_status=unknown` and excluded from the map.
The earlier [Microsoft announcement](https://ukstories.microsoft.com/features/building-the-foundations-of-the-uks-intelligence-economy/)
and [Nscale agreement](https://www.nscale.com/press-releases/nscale-microsoft-2025)
conflict with [October withdrawal reporting](https://www.itpro.com/infrastructure/data-centres/microsoft-pulls-plug-on-essex-data-center-development-over-power-supply).
The latter is retained as a conflict-review source, not as a primary facility
admission. A current Microsoft/Nscale clarification is needed to resolve the
relationship. CoreWeave's general relationship with Microsoft does not assign
Microsoft occupancy to every CoreWeave site, so no such site expansion is made.

No complete parcel-title or lease schedule was available in the selected
public sources. Community statements establish Microsoft's disclosed role in
building or operating local infrastructure; ownership remains `not_disclosed`
unless a named partner relationship establishes third-party capacity.

## Quality findings and geographic treatment

- **High severity, high confidence: overlapping directory units.** Front Door
  metro rows, abbreviation rows and network identifiers are not additive
  physical sites. The Front Door headline states 192 commercial POPs in 109
  metros and four government edge locations; the retained itemized table sums
  to 191 commercial POPs in 107 metro rows and three government rows. Both
  statements remain visible in the report; no rows are fabricated to close
  the discrepancy.
- **High severity, high confidence: locality is not a building.** All cloud
  regions retain null geometry. Global-network map points retain provider
  coordinates at city or explicitly broad regional precision and explicitly do not establish facility
  addresses or ownership. Service and community references use separate
  approximate marks, never counted physical facilities.
- **Medium severity, high confidence: lifecycle varies by source scope.**
  Taiwan North is planned in the public directory. East US 2 and North Central
  US show coming-soon zone support, separately from operational region status.
  Numeric zone declarations are parsed without inventing individual zone IDs.
  A coming-soon annotation retains an uncertain support value rather than
  asserting that support is unavailable.
  Community and partner phases retain their source qualifications.
- **High severity, high confidence: ambiguous place names require jurisdiction
  checks.** Quincy is matched to Washington, not Illinois or Massachusetts;
  New Albany, Heath and Hebron are matched to Ohio. Malaga, Washington is held
  because the selected gazetteer has no suitable populated-place row there;
  Malaga, California is explicitly not substituted.
- **High severity, unresolved current affiliation: Loughton.** Conflicting
  recent reporting prevents a current Microsoft locality admission.

Three global-network POPs grouped under `china` by the globe feed are
retained as Hong Kong (`HK`, `hong_kong`) after locality review: HKG33, HKG30
and HKB. The original source geography remains in properties. Six source
`City` labels are broad: Bay, Ontario (two identifiers), New Jersey,
Maharashtra and Municipio El Marqués. They retain regional precision and
null canonical city names instead of being promoted to cities or facilities.

The geographic join retains eighty-three reviewed locality labels and
seventy-seven distinct GeoNames rows. Different service/locality references
can share one place. Ninety-six claim memberships are admitted and no canonical
location record is attached twice. Region-only and unresolved assertions stay
in the evidence collection without acquiring invented city geometry. The
[selection review](../data/raw/microsoft-enrichment/locality-selection-review.20261021.json)
records the candidate counts, selected identities, state filters and holds.

The [machine-readable assessment](../data/microsoft/enrichment-review.20261021.json),
[layer reports](../data/microsoft/), source catalog, bibliography and
[`tests/validate_microsoft.py`](../tests/validate_microsoft.py) retain the audit
trail. A compact [quality notebook](microsoft-quality.20261021.ipynb) exposes
the current counts and source-boundary assertions for inspection.

## Reproduce and validate

The update runs offline against retained captures. It does not contact
Microsoft, require cloud credentials or create cloud resources:

```bash
python3 -B scripts/update_microsoft.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-21
make check
make RETRIEVED_AT=2026-10-21 csv
```

The focused suite checks schema conformity, source hashes, unique identities,
historical first-seen dates, region/zone semantics, country/state joins,
conflict exclusion, bibliography append-only behavior, byte-identical offline
replay, and reproduction of the unchanged October 19 manifest. Prior suites
continue to validate earlier provider snapshots.

The bibliography is a retained dated index extending the October 19 entries;
ordinary Microsoft layer replay does not rewrite either bibliography. To
refresh upstream evidence, use a new retrieval tag, retain fresh captures and
review structural, identifier, lifecycle and location changes before replacing
the current selection. Do not simply relabel these snapshots with a new date.

## Remaining evidence limits

Public material cannot establish every owned or leased campus, its boundaries,
current tenant, active capacity or exact address. This release is a substantial
bounded enrichment, not an exhaustive estate inventory. Finer evidence would
come from explicitly published project pages, public planning/property records,
operator disclosures and dated launch confirmations. It must be joined at its
stated precision; investment, network presence, a regional service listing or
an expired delivery target alone does not establish ownership or operation.

## Public-source credential redaction

Forty-three public community-site HTML captures contained an embedded Mapbox access token in
`modern_tribe_config.mapbox_key`. The archived setting is replaced with
`REDACTED_MAPBOX_TOKEN`; all other response bytes are preserved. Each affected
provenance record retains the original response SHA-256 and describes the
redaction. Catalog, bibliography and derived evidence hashes describe the
redacted archive. This changes provenance digests, not extracted infrastructure
assertions or map geometry. The rejected unpublished commits were replaced
before pushing; no push-protection exception was used.
