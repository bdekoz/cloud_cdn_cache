# Independent observation and network-evidence implementation

Date: 2026-08-05

This record implements the safe, reproducible portions of items 4 and 5 from the immutable [`assessment.20260804.md`](assessment.20260804.md). Provider declarations, independent geolocation, provider prefix feeds, routing/RPKI observations, and registry relationships remain separate evidence classes. None of the network layers is a physical-site inventory.

## Implemented outputs

| Layer | Records | Evidence unit | Physical-location claim |
|---|---:|---|---|
| `observations/cdn-mapping.20260804.geojson` | 13,631 | Valid provider/ASN TLS observation | None; geometry is null |
| `observations/cdn-mapping-cities.20260805.geojson` | 11,659 | Provider/ASN/MaxMind city-coordinate observation | City geolocation only; not a facility |
| `network/provider-prefixes.20260805.json` | 1,581 | Provider-published CIDR/service assertion | None |
| `network/ripestat-routing.20260805.json` | 15 | Eight sampled route lookups and seven RPKI results | None |
| `network/peeringdb-relationships.20260805.json` | 1,529 | Registered network/facility or network/IX relationship | Registration only; not CDN presence or ownership |

The current manifest counts 27,378 location-schema records across 28 layers and 3,125 non-spatial network-evidence records across three layers. Network records are excluded from the location `record_count`.

## ASN observation correction

Each of the seven study CSVs contains one `ASN 0` row with a blank AS name. The raw files and their reported 13,638 rows remain unchanged. Normalization now rejects those seven rows and emits 13,631 valid records:

| Provider | Raw | Accepted | Rejected |
|---|---:|---:|---:|
| Google | 4,247 | 4,246 | 1 |
| Netflix | 2,903 | 2,902 | 1 |
| Meta | 2,548 | 2,547 | 1 |
| Microsoft | 1,655 | 1,654 | 1 |
| Akamai | 1,094 | 1,093 | 1 |
| Apple | 974 | 973 | 1 |
| CloudFront | 217 | 216 | 1 |

The report preserves raw, accepted, and rejected counts and identifies every rejected row. Source totals are therefore reproducible without promoting invalid AS0 records.

## Partial city map

The public Google My Maps KML embedded by the June 2026 study contains 11,663 placemarks for Google GGC, Meta FNA, and Netflix OCA. Four Netflix placemarks use ASN 0 and are rejected, leaving 11,659 observations. Coordinates are labeled `coordinate_method=geocoded`, `location_precision=city` when a city exists, and `geolocation_database=MaxMind GeoIP Lite`. A total of 599 accepted Netflix records have the source city marker `\N`; their city and precision are null/unknown while their source value remains in properties.

| Dataset | Accepted rows | Unique valid ASNs | Countries in KML | Article countries | Gap |
|---|---:|---:|---:|---:|---:|
| Google GGC | 4,802 | 3,344 | 198 | 215 | 17 |
| Meta FNA | 2,736 | 1,896 | 183 | 204 | 21 |
| Netflix OCA | 4,121 | 2,902 | 181 | 181 | 0 |

Five KML folders contain exactly 2,000 placemarks. Together with the Google and Meta country gaps and absence of Akamai, Microsoft, Apple, and CloudFront, this establishes that the map is partial. The layer complements the ASN CSV observations; it is not a replacement or a complete export. Its license remains unstated, so provenance warns that redistribution rights require review.

## Provider prefix feeds

The non-spatial `network-evidence.schema.json` prevents CIDRs from being serialized as GeoJSON points. It uses the official [AWS IP ranges](https://docs.aws.amazon.com/vpc/latest/userguide/aws-ip-ranges.html), [Google-owned and Google Cloud range feeds](https://docs.cloud.google.com/appengine/docs/standard/outbound-ip-addresses), and [Azure Service Tags](https://learn.microsoft.com/en-us/azure/virtual-network/service-tags-overview). The retained prefix layer contains:

| Feed scope | Records | Selection boundary |
|---|---:|---|
| AWS CloudFront | 150 | `service=CLOUDFRONT` and `region=GLOBAL`; regional and origin-facing records excluded |
| Google-owned | 114 | Broad `goog.json` ranges; not GGC-specific |
| Google Cloud customer ranges | 1,091 | `cloud.json`; customer-resource address space, not Google facilities |
| Azure Front Door | 226 | `AzureFrontDoor.Frontend`; backend, first-party, and security tags excluded |

There are 1,337 IPv4 and 244 IPv6 records. Every row says that the provider feed declared a prefix for a scope. It does not say that the entire prefix is currently routed, that a prefix belongs to one origin ASN, or that it identifies a POP.

## RIPEstat pilot

The pilot deterministically selects one IPv4 and one IPv6 prefix from each of the four feed scopes. It samples one address inside each selected prefix with RIPEstat [`network-info`](https://stat.ripe.net/docs/data-api/api-endpoints/network-info.html), then validates every returned origin/prefix pair with [`rpki-validation`](https://stat.ripe.net/docs/data-api/api-endpoints/rpki-validation). Exact request URLs, API payloads, versions, status, response time, sampled address, declared prefix, and returned routed prefix are retained in one raw bundle.

Seven sampled addresses returned an origin and all seven origin/prefix pairs were RPKI-valid at observation time. The sampled AWS CloudFront IPv6 address did not return a route; this remains a `not_announced` sampled result, not a claim that the entire declared prefix is unused. RIPEstat geolocation endpoints are deliberately not queried because the study already uses MaxMind and would not gain independent geolocation corroboration.

## PeeringDB pilot

The bounded [PeeringDB API](https://docs.peeringdb.com/api_specs/) pilot covers four origin ASNs found by the RIPEstat sample: AS8075, AS15169, AS16509, and AS396982. Paginated `netfac` and `netixlan` responses produce 498 facility registrations and 1,031 IX memberships.

These are relationships registered for the network ASN. For embedded caches, the observed ASN can instead be the host/eyeball network. Even for provider-owned ASNs, a registered facility or IX relationship does not prove that a CDN appliance is installed there or that the provider owns the facility. Every record carries both `registration_not_cdn_presence` and `registration_not_provider_ownership` safeguards. [PeeringDB's AUP](https://www.peeringdb.com/aup) remains applicable; the report requires a rights review before bulk reuse or redistribution beyond this bounded research snapshot.

## RIPE Atlas gate

No [RIPE Atlas](https://atlas.ripe.net/docs/apis/rest-api-manual/introduction/) measurement was created. The workspace has neither an Atlas API key/credits nor provider-approved measurement targets. Arbitrary addresses selected from a provider prefix feed are not automatically safe or meaningful latency targets, and a DNS/anycast response cannot be converted into a facility coordinate.

A future run must first define:

1. provider-approved DNS names or IP targets and a control target;
2. a stable probe sample stratified by country and probe ASN;
3. IPv4 and IPv6 coverage, resolver choice, and DNS answers retained per probe/run;
4. ping and traceroute parameters, rate, repetition window, and stop conditions;
5. measurement ID, probe ID/ASN/country, timestamps, RTT/loss, and path output;
6. API-key handling, credit budget, RIPE Atlas terms, and publication scope;
7. an explicit rule that latency, anycast selection, and obfuscated probe coordinates are not facility-location evidence.

Until these conditions are met, the correct Atlas output count is zero rather than an unreviewed active measurement.

## Source-rights status

| Source | Retention/use status | Publication boundary |
|---|---|---|
| June study CSVs and KML | Public research downloads; explicit data license not found | Retained for reproducibility with warning; review before downstream redistribution |
| AWS, Google, and Microsoft prefix feeds | Official public operational feeds; source-specific terms apply | Normalized assertions do not imply blanket relicensing |
| RIPEstat | Public Data API responses; RIPE service terms apply | Bounded cached pilot with `sourceapp`; preserve endpoint/version/status |
| PeeringDB | Public API used for a bounded operational-research pilot; AUP applies | Do not expand or bulk redistribute without a confirmed permitted-use basis |
| RIPE Atlas | No data collected | API key, credits, target authorization, service terms, and publication scope required first |

## Reproduction

Regenerate from retained sources:

```sh
python3 -B scripts/update_observations.py --retrieved-at 2026-08-04
python3 -B scripts/update_observation_cities.py --retrieved-at 2026-08-05
python3 -B scripts/update_network.py --retrieved-at 2026-08-05
python3 -B scripts/update_peeringdb.py --retrieved-at 2026-08-05
python3 -B scripts/build_manifest.py --retrieved-at 2026-08-05
make check
```

Take a new network snapshot deliberately with `make refresh-network`. This fetches current provider feeds, the bounded RIPEstat sample, and PeeringDB relationships before rebuilding the manifest. Review source terms, changes, and semantic diffs before publication.
