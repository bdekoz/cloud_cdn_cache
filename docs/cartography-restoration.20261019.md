# Akamai restoration and Apple secure DNS geography

Canonical source: `cloud_cdn_cache.bkoz`. Reviewed and normalized 2026-10-19.
The [20261019 manifest](../data/manifest.20261019.json) adds two location layers
to the unchanged 20261011 selection: **33 layers, 27,930 records**. Its older
31 layers and 27,500 records retain their original snapshots, IDs and hashes.
Alpha60 consumes this manifest by SHA-256; it does not maintain a second copy
of these infrastructure layers.

## Akamai: restore the retained geography

[Legacy locations](../data/akamai/legacy-locations.20261019.geojson) normalizes
all **416 points** from `data/akamai_13-07-2023.geojson`: 344 edge, 45 distributed
and 27 core records. Coordinates and original properties are retained exactly.
The raw file is copied byte-for-byte into `data/raw/cartography-restoration/`
to meet the canonical raw-source contract.

The source labels 355 rows existing and 61 planned. Canonical lifecycle values
are `operational` and `planned`, respectively, **as recorded in 2023**. The
per-row update date remains 2023-07-12. The October normalization date does
not confirm that these sites or plans still exist. Coordinates retain
`coordinate_method: legacy` and `location_precision: city`; they are not
verified facility coordinates. Country spelling aliases for Saint Lucia,
Myanmar and Trinidad and Tobago are explicit and preserve the original strings.

The existing 1,093 Akamai ASN observations remain separate, unlocated records.
No ASN count is added to a location's symbol weight. The restored layer supplies
the historical points that were omitted by the newer manifest selection.

## Apple: a bounded DNS observation layer

Apple's [enterprise-network documentation](https://support.apple.com/en-us/101555)
identifies `doh.dns.apple.com` as DNS over HTTPS on TCP 443. The new
[DNS city layer](../data/apple/dns-cities.20261019.geojson) has **14 records**:
13 US cities and Toronto, Canada. These describe secure DNS endpoint geography;
they do not establish Apple Edge Cache installations or physical facilities.

The reproducible evidence chain is:

1. Retain the public IPv4 and IPv6 resolved-hostname observations from
   [dibdot/DoH-IP-blocklists](https://github.com/dibdot/DoH-IP-blocklists), plus
   one public recursive DNS response for the Apple hostname. Match exact
   hostname tokens and deduplicate IP addresses across both inputs.
2. Match each address to the most specific prefix in
   [Apple's published geofeed](https://ip-geolocation.apple.com/). A service
   association comes from the DNS observations; the feed contributes its
   country, subdivision and city. No unobserved address or prefix becomes a point.
3. Review each city identity against GeoNames by country and subdivision.
   Fourteen selected populated-place rows and their explicit identity crosswalk
   are retained. New York maps to New York City; Toronto maps to Ontario.
   GeoNames coordinates are approximate city reference points, licensed CC BY 4.0.
4. Emit one `observed_presence` record per distinct country/subdivision/city,
   with service scope `dns_over_https`, `coordinate_method: geocoded`,
   `location_precision: city`, `source_scope: observed`, and lifecycle `unknown`.
   Every record retains its contributing IPs, raw source lines and geofeed
   prefixes. IP multiplicity remains metadata rather than a facility count.

The [endpoint audit](../data/apple/dns-endpoint-audit.20261019.json) conserves
all **108 addresses**: 104 match the 14 reviewed cities; four remain unlocated.
Those four are `64.78.200.1`, `64.78.201.1`, `2620:171:80c::1` and
`2620:171:80d::1`, with no matching Apple geofeed city. They remain in the
audit rather than receiving invented point coordinates. The selected cities
are Ashburn, Atlanta, Chicago, Dallas, Denver, Los Angeles, Miami, New York,
Newark, San Jose, Santa Clara, Secaucus, Southfield and Toronto.

### Coverage and the PCH/Woodynet lead

[Anurag Bhatia's June study](https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/)
mentions over 236 Apple DNS locations with PCH/Woodynet. In the reviewed HTML (its hash and extracted facts are retained),
the promised detailed list has no hyperlink. The published Apple CSV/JSON
contain ASN/name pairs, and the published city map has no Apple layer.
[PCH's own POP directory](https://www.pch.net/about/pops) identifies its network
locations but does not identify which individually host Apple's DNS service.
Neither aggregate is converted into Apple point records.

The 14-city result is a **partial, resolver-vantage-dependent observation**.
It is not the global Apple or PCH footprint, and it does not reproduce the
236-location claim. The geofeed contains IP geography hints, not measured server
positions. IPv4/IPv6 aliases are combined by city, and endpoint counts cannot
establish independent installations. An itemized, service-specific PCH export
would support a subsequent layer with its own provenance and deduplication.

Apple's 973 prior ASN observations remain unchanged and unplotted. Their
content-delivery TLS classification is distinct from this DNS service layer.
The prior ASN layer retains the original study's service and ownership limitations.

## Reproduction and checks

```sh
python3 -B scripts/update_cartography_sources.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make csv RETRIEVED_AT=2026-10-19
python3 -B tests/validate_cartography_sources.py
make check
```

All normalization inputs, with factual extracts for the two narrative web pages, are retained under `data/raw/cartography-restoration/`
with SHA-256 provenance. The update script runs offline and never refreshes the
2023 Akamai survey silently. Validation checks raw-to-canonical geometry and
lifecycle conservation, Apple endpoint partitioning, record grain, schema and
CSV parity, all manifest hashes, and byte-identical prior location layers.
