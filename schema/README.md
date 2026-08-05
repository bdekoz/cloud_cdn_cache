# Canonical location schema

`location.schema.json` defines the normalized record used before serializing a provider layer to CSV and GeoJSON. Version `1.0.0` is provider-neutral: service names are stable snake_case identifiers and entity types distinguish unlike infrastructure classes.

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
| Baidu AI Cloud | `baidu_cloud` | `cloud_region` |
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

For GeoJSON, `[longitude, latitude]` becomes the feature geometry and the remaining canonical fields become feature properties. For CSV, `aliases` and `properties` are encoded as compact JSON values. Both formats are generated from the same ordered canonical record stream.

## Provenance and history

Every record points to a repository-relative immutable raw source with `raw_source_ref` and its SHA-256 digest. `retrieved_at` records the snapshot date. `source_published_at` is `null` when the provider publishes no source date. Initial snapshots use the retrieval date for both `first_seen` and `last_seen`; later refreshes retain `first_seen` and advance `last_seen` for matching stable IDs.

Provider-declared locations use `source_scope=provider_declared`. Independently measured ASN, DNS, TLS, or routing observations must use `observed` or `inferred` and must not overwrite provider-declared records.

Entity-specific values that do not apply to every layer—such as `asset_count`, `asn`, `hostname`, IP-family, provider region ID, network-border group, or live component status—belong in `properties`. This keeps the cross-provider core compact while retaining source evidence.
