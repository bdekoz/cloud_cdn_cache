# Canonical location schema

`location.schema.json` defines the normalized record serialized as a provider layer's canonical GeoJSON. The current contract is version `1.2.0`; it accepts retained `1.1.0` records and newly generated `1.2.0` records so an older snapshot never has to be silently relabeled. Service names are stable snake_case identifiers and entity types distinguish unlike infrastructure classes. CSV is a deterministic projection generated from that GeoJSON on demand.

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

The consolidated 2026-08-05 manifest is intentionally mixed-version and mixed-date: the 2026-08-04 layers retain schema version 1.1 and their original retrieval date, while the new hyperscaler layers use schema version 1.2 and retrieval date 2026-08-05.

## Google classification

| Layer | `service` | `entity_type` | `source_collection` |
|---|---|---|---|
| Google Edge | `google_edge` | `edge_pop` | `google_peering_infrastructure` |
| Google Data Centers | `google_data_centers` | `data_center` | `google_data_centers_directory` |
| Google Global Cache | `google_global_cache` | `embedded_cache` | `google_peering_infrastructure` |

These classes must not be combined into a count of equivalent physical assets. An edge POP is an interconnection location, an owned data center is a campus or facility, and a GGC node is an embedded cache in another network.

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
| Chindata | `chindata_colocation` | `data_center` |
| Amazon Web Services | `aws_cloud` | `cloud_region`, `availability_zone` |
| Microsoft Azure | `azure_cloud` | `cloud_region` |
| Google Cloud | `google_cloud` | `cloud_region`, `availability_zone` |
| Oracle Cloud Infrastructure | `oracle_cloud` | `cloud_region` |
| IBM Cloud | `ibm_cloud` | `cloud_region`, `availability_zone` |
| IBM Cloud | `ibm_classic` | `data_center` |
| Meta | `meta_data_centers` | `data_center` |
| CoreWeave | `coreweave_cloud` | `super_region`, `availability_zone` |
| Multi-provider measurements | `cdn_mapping_observation` | `observed_presence` |

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
