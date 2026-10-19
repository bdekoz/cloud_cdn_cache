# Canonical location schema

Connectivity systems, regulatory authorizations, fiber links, optical/quantum projects, and other emergent units use the separate [`infrastructure-evidence.schema.json`](infrastructure-evidence.schema.json). Its category vocabulary is open, every category has a definition, and every record states its unit. It does not modify the retained location/network contracts or combine their totals. See [`infrastructure-expansion.20261011.md`](../docs/infrastructure-expansion.20261011.md).

Derived provider/service/locality points use [`geographic-footprint.schema.json`](geographic-footprint.schema.json), published under `geographic_footprint_views` in the manifest. They have their own `footprint_id`, grouped canonical `source_record_ids` or named-evidence `source_claim_ids`, and reviewed GeoNames provenance. Their geometry is a city or county reference point; `physical_site_confirmed=false` and `excluded_from_canonical_totals=true` are required. Availability zones do not generate separate locality points. See [China locality enrichment](../docs/china-geography-enrichment.20261019.md).

[`location-v1.3.schema.json`](location-v1.3.schema.json) is the current location contract, accepting retained `1.1.0`/`1.2.0` records and new `1.3.0` records. [`location.schema.json`](location.schema.json) remains the unchanged 1.2 contract for historical manifests. Both define the same canonical fields and CSV column order. Service names are stable snake_case identifiers and entity types distinguish unlike infrastructure classes. CSV is a deterministic projection of canonical GeoJSON.

Version 1.1 adds fields needed to represent Chinese provider catalogs without collapsing unlike products or jurisdictions:

- `parent_record_id` links an availability zone to its published parent region.
- `jurisdiction_scope` separates mainland China, Hong Kong, Macao, Taiwan, and other/global records.
- `access_status` keeps public, sales-restricted, invite-only, and dedicated access separate from lifecycle.
- `service_scope` records the product surface that established membership, such as compute, VPC, Cloud Connect, financial cloud, or colocation.
- `coordinate_crs` makes WGS 84 (`EPSG:4326`) explicit and prevents source coordinates in GCJ-02 or BD-09 from being silently serialized as GeoJSON.
- `cloud_resource_pool` represents a provider-published pool when the source does not justify inventing region or availability-zone children.

Version 1.2 adds two source-preserving values:

- `super_region` represents CoreWeave's published grouping of availability zones without pretending that it is an ordinary cloud region.
- `access_status=restricted` represents subscription-, partition-, government-, or scenario-gated access that is broader than a temporary sales restriction and is not dedicated to one customer.

Version 1.3 permits an availability zone with an unpublished parent identity to retain `parent_record_id=null`, only when `properties.parent_region_not_published_in_source=true` and `properties.parent_identity_evidence` supplies a source URL, raw reference and hash. Earlier versions still require a parent. This supports Cloud.ru Evolution without fabricating a region; other known parent relationships remain mandatory.

The consolidated 2026-08-05 manifest is intentionally mixed-version and mixed-date: the 2026-08-04 layers retain schema version 1.1 and their original retrieval date, while the new hyperscaler layers use schema version 1.2 and retrieval date 2026-08-05.

## Google classification

| Layer | `service` | `entity_type` | `source_collection` |
|---|---|---|---|
| Google Edge | `google_edge` | `edge_pop` | `google_peering_infrastructure` |
| Google Data Centers | `google_data_centers` | `data_center` | `google_data_centers_directory` |
| Google Global Cache | `google_global_cache` | `embedded_cache` | `google_peering_infrastructure` |
| Google Cloud standard hierarchy | `google_cloud` | `cloud_region`, `availability_zone` | `google_compute_regions_and_zones` |
| Google Cloud AI zones | `google_cloud` | `availability_zone` | `google_compute_ai_zones` |

These classes must not be combined into a count of equivalent physical assets. An edge POP is an interconnection location, an owned data center is a campus or facility, and a GGC node is an embedded cache in another network.

Google AI zones use `properties.zone_kind=ai` and restricted project visibility. The canonical parent is the Cloud region; `properties.parent_zone_record_id` separately links to the standard zone whose software schedule and sometimes infrastructure are shared. GPU and GCPing joins keep their own provenance inside properties. Endpoint metadata does not create locations or coordinates. See [`Google enrichment`](../docs/google-enrichment.20261011.md).

## Registered services

| Provider | `service` | Principal `entity_type` |
|---|---|---|
| Cloudflare | `cloudflare_network` | `edge_pop` |
| Microsoft | `azure_front_door` | `edge_pop` |
| Amazon Web Services | `aws_cloudfront` | `edge_pop`, `regional_edge_cache` |
| Amazon Web Services | `aws_local_zones` | `local_zone` |
| Fastly | `fastly_network` | `edge_pop` |
| CacheFly | `cachefly_network` | `edge_pop` |
| Alibaba Cloud | `alibaba_cloud` | `cloud_region`, `availability_zone` |
| Tencent Cloud | `tencent_cloud` | `cloud_region`, `availability_zone` |
| Baidu AI Cloud | `baidu_cloud` | `cloud_region`, `availability_zone` |
| Huawei Cloud | `huawei_cloud` | `cloud_region` |
| Volcano Engine | `volcano_cloud` | `cloud_region`, `availability_zone` |
| Kingsoft Cloud | `kingsoft_cloud` | `cloud_region`, `availability_zone` |
| JD Cloud | `jd_cloud` | `cloud_region`, `availability_zone` |
| China Telecom Tianyi Cloud | `ctyun_cloud` | `cloud_resource_pool` |
| Qiniu Cloud | `qiniu_qvm` | `cloud_resource_pool`, `cloud_region` |
| Microsoft Azure operated by 21Vianet | `azure_china` | `cloud_region` |
| Chindata | `chindata_colocation` | `data_center` |
| Amazon Web Services | `aws_cloud` | `cloud_region`, `availability_zone` |
| Microsoft Azure | `azure_cloud` | `cloud_region` |
| Google Cloud | `google_cloud` | `cloud_region`, `availability_zone` |
| Yandex | `yandex_data_centers` | `data_center` |
| Yandex Cloud | `yandex_cloud`, `yandex_baremetal` | `cloud_region`, `availability_zone` |
| Yandex Cloud | `yandex_cdn` | `edge_pop` (city with one or more PoPs) |
| Selectel | `selectel_cloud` | `cloud_region`, `availability_zone`, `cloud_resource_pool` |
| Cloud.ru | `cloudru_advanced`, `cloudru_evolution` | `cloud_region`, `availability_zone` |
| IXcellerate | `colocation` | `data_center` |
| Oracle Cloud Infrastructure | `oracle_cloud` | `cloud_region` |
| IBM Cloud | `ibm_cloud` | `cloud_region`, `availability_zone` |
| IBM Cloud | `ibm_classic` | `data_center` |
| Meta | `meta_data_centers` | `data_center` |
| CoreWeave | `coreweave_cloud` | `super_region`, `availability_zone` |
| Multi-provider measurements | `cdn_mapping_observation` | `observed_presence` |
| Multi-provider city geolocation | `cdn_mapping_city_observation` | `observed_presence` |

The schema deliberately validates the service naming convention rather than a closed enum. New connectors can therefore be added without invalidating an otherwise compatible schema, but they must register their service here before publication.

## Stable identifiers

`record_id` has the form `provider:entity_type:identifier`.

1. Prefer a provider-supplied site code or stable identifier.
2. Otherwise derive the identifier from the source collection, normalized name, country code, and coordinates supplied by that source.
3. Preserve earlier identifiers in `aliases` when a source renames a location.
4. Never derive identity from a row number or retrieval date.

`source_record_id` retains the provider's identifier separately. It is `null` when the source provides none.

## Location semantics

Coordinates are nullable, but latitude and longitude must either both be numbers or both be `null`. `location_precision` describes what the point means; it must not imply facility-level accuracy for a city or metro centroid. `coordinate_method` records whether the provider supplied the point or it was geocoded or inherited from a legacy layer.

Serialized coordinates are always WGS 84 and use `coordinate_crs=EPSG:4326`. If a Chinese source supplies GCJ-02 or BD-09 coordinates, the original CRS and values belong in `properties`, the conversion must be reproducible, and `coordinate_method` must be `transformed`. A record with null geometry also has null `coordinate_crs`.

`lifecycle_status` answers whether an entity is operational, planned, inactive, or retired. `access_status` answers who may buy or use it. For example, a currently operational Tencent zone can be sales-restricted, and an operational financial-cloud region can be dedicated. These states must not be conflated.

Mainland views are generated as subsets of full provider layers. They reuse canonical IDs and are therefore views, not additional records. Hong Kong is never treated as mainland China merely because a provider groups it on a China-facing documentation page.

For GeoJSON, `[longitude, latitude]` becomes the feature geometry and the remaining canonical fields become feature properties. The GeoJSON is the retained publication artifact. `scripts/geojson-to-csv.jq` reconstructs every required schema field, restores latitude and longitude from point geometry, uses the schema's `required` array for column order, and encodes arrays or objects as compact JSON. Run `make csv` for every normalized layer or name one CSV target directly.

## Provenance and history

Every record points to a repository-relative immutable raw source with `raw_source_ref` and its SHA-256 digest. `retrieved_at` records the snapshot date. `source_published_at` is `null` when the provider publishes no source date. Initial snapshots use the retrieval date for both `first_seen` and `last_seen`; later refreshes retain `first_seen` and advance `last_seen` for matching stable IDs.

Provider-declared locations use `source_scope=provider_declared`. Independently measured ASN, DNS, TLS, or routing observations must use `observed` or `inferred` and must not overwrite provider-declared records.

Entity-specific values that do not apply to every layer—such as `asset_count`, `asn`, `hostname`, IP-family, provider region ID, network-border group, or live component status—belong in `properties`. This keeps the cross-provider core compact while retaining source evidence.

## Network evidence schema

`network-evidence.schema.json` is a separate, non-spatial contract for provider prefix declarations, routing origins, RPKI validation, PeeringDB registrations, and RIPE Atlas measurements. These assertions are deliberately excluded from the location schema and from GeoJSON because none of them, by itself, establishes a physical POP or facility.

| Evidence type | Relationship | Meaning | Explicit non-claim |
|---|---|---|---|
| `provider_prefix` | `declares_prefix` | A provider feed published a CIDR for a named service or scope | The prefix is not a POP location |
| `routing_origin` | `originates_prefix` | RIPE RIS observed an ASN originating the sampled prefix | The origin ASN is not proof of ownership or colocation |
| `rpki_validation` | `validated_by_rpki` | RIPEstat reported the origin/prefix RPKI state | RPKI validity is not location evidence |
| `facility_registration` | `registered_at_facility` | A network registered a facility relationship | The CDN appliance is not thereby proven present |
| `ix_membership` | `present_at_ix` | A network registered an IX relationship | IX membership is not a provider-owned POP |
| `measurement_run` / `reachability_observation` | measurement relationships | A reproducible probe selection and sampled result | Latency and routing do not reveal exact server coordinates |

Network outputs are `NetworkEvidenceCollection` JSON documents. Records carry independent observation time, retrieval time, source version, raw checksum, validity interval, and confidence. Prefix and ASN relationships are many-to-many and time-bound. Location layers may reference network record IDs in future properties, but network evidence must never overwrite provider-declared location records or manufacture geometry.

## Derived CDN ASN comparisons

[`cdn-comparison.schema.json`](cdn-comparison.schema.json) defines `CdnAsnComparison`, a non-spatial view with one row per numeric ASN. Each row preserves all source AS names, seven nullable provider observation IDs and an optional APNIC allocation/assignment entry. A null provider ID means not observed in the retained study, not verified absence. A null registration means no eligible match in the selected APNIC file, not a negative country classification. Matching entries retain the country code, source line, ASN interval, status and allocation/assignment date.

The collection records its selection, June source dates, October build date and input hashes. APNIC country never fills a location field. The full matrix and India subset are listed separately as `observation_comparison_views` in the manifest and excluded from canonical counts. Apple and India-city GeoJSON views retain exact source features under the existing location schema. See the [implementation and reproduction notes](../docs/cdn-mapping-india-apple.20261019.md).

Version 1.1 adds the RIPE country selection and `rir_registration`, with an explicit `registry=ripencc` and the same interval/source-line evidence. Version 1.0 retains `apnic_registration`; the validator rejects mixing the two contracts. The [Russia comparison](../docs/russia-enrichment.20261019.md#june-registration-comparison-and-geographic-view) is a separate derived view, never a physical-country assignment.

## Application endpoint evidence

[`application-endpoint.schema.json`](application-endpoint.schema.json) defines a separately counted `ApplicationEndpointCollection`. Entities carry sourced identity/status context and optional provider-declared hosting. Query records have the grain entity/hostname/role/timestamp/RR type, retain the complete resolver response, and distinguish NOERROR without the requested RR from NXDOMAIN, DNS failure and transport failure. Confidence describes the observation, not an origin inference.

Address enrichment preserves routing and registry receipts separately. Neither `registry_country_code` nor an entity's declared cloud region populates `origin_country_code`. Any future non-null origin country or facility identity requires independent origin evidence with an explicit scope and method. The current crypto collection has no such attributed origins. It records one resolver without an explicitly located probe or ECS. CSV retains nested evidence as JSON cells; entity details remain in the source JSON. Application records and entity counts are excluded from location, network and infrastructure totals. See the [implementation](../docs/russia-enrichment.20261019.md#exchange-endpoint-evidence).

## China service and vendor evidence

The [October China implementation](../docs/china-enrichment.20261011.md) uses infrastructure-evidence schema 1.0.0 for AI product regions, API endpoints/templates, model listings, GPU product catalogs, recognized compute facilities, portfolios, cable/station declarations and carrier services. Each collection defines its categories and units. Access/storage region, inference scope, developer, API operator and physical host remain distinct. Aggregate or recognition entries do not become speculative location points.

`data/vendors/registry.20261011.json` uses that same record contract for identity metadata. It is separately counted in the manifest and excluded from infrastructure totals. Typed relationships can reference its vendor/brand IDs and explicit canonical region IDs. `validate_collection` resolves external references only against a caller-supplied set of known IDs; its default still rejects unresolved cross-collection joins. Endpoint DNS, ASN registration country, TLS and HTTP results remain non-spatial network evidence. Native observation time is UTC while the October retrieval date uses America/Los_Angeles.
