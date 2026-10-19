# Apple TV delivery infrastructure

Built 2026-10-19. Public `tv.apple.com` pages and free-preview playlists establish three video delivery providers in this sample: Apple, Akamai and Fastly. The new layers contain 18 service/host assertions, four routing observations and two city reference points. The related [Apple cache-hosting review](apple-edge-cache.20261019.md) maps AEC candidates separately.

## Observed delivery paths

The public [Ted Lasso show page](https://tv.apple.com/us/show/ted-lasso/umc.cmc.vtoh0mn0xn7t3c643xqonfzy) embeds two sampled `Preview` objects with `Free` entitlement metadata: “Together: Season 4” and “Return: Season 3”. Each master playlist advertises all three video hostnames below. The repeated URLs describe renditions, audio and captions; they are not distinct sites.

| Role | Provider evidence | Geographic meaning |
| --- | --- | --- |
| Public web page and JavaScript | Akamai response-cache headers on the sampled `tv.apple.com` and application resources | No PoP locality admitted. |
| Artwork | Apple cache headers on the sampled `is1-ssl.mzstatic.com` resource | Artwork delivery is distinct from video delivery; no locality admitted. |
| Preview video playlist: `vod-ap-aoc.tv.apple.com` | `cdn-server: aapl`, Apple cache labels and actual HTTP peer `149.112.115.176` | RIPEstat reports `149.112.115.0/24`, AS40271 (SFMIX). The response includes an SFMIX cache label; a physical-site join is unresolved. |
| Preview video playlist: `vod-ak-aoc.tv.apple.com` | `cdn-server: akam`, Akamai cache headers, actual HTTP peer `23.192.228.8` | RIPEstat reports `23.192.228.0/24`, AS20940. The returned `ZZZ` locality code is unmapped. |
| Preview video playlist: `vod-fa-aoc.tv.apple.com` | `cdn-server: fsly`, `x-cdn: fsly`, `x-served-by: cache-pao-kpao1770067-PAO`, actual HTTP peer `151.101.3.6` | RIPEstat reports `151.101.0.0/22`, AS54113. Fastly's official PoP directory identifies PAO as Palo Alto. |

The three sampled video playlists returned HTTP 200 and identical bodies. This confirms retrieval of the advertised manifest variants; browser path selection and video playback were not tested. No media segments, keys, licenses or authenticated endpoints were requested. Application metadata also identifies `uts-api.itunes.apple.com` as a catalog API, `play-edge.itunes.apple.com` as a playback-manifest service, and `mediaservices.cdn-apple.com` for player telemetry configuration. Those endpoint roles do not establish media origin locations.

The [source catalog](../data/raw/apple-tv/catalog.20261019.json) retains exact request URLs, response bytes, peer addresses where captured, UTC timestamps, headers and SHA-256 hashes. HTTP assertions cite the metadata sidecar so the headers and peer are inspectable, and separately reference the response body. Cached HTTP `Date` values are not used as observation times.

## Mappable localities

The [TV delivery view](../data/apple/tv-delivery-localities.20261019.geojson) contains:

- **Palo Alto, US:** a sampled Fastly delivery locality, joined through the official [PoP directory](https://www.fastly.com/documentation/guides/getting-started/concepts/using-fastlys-global-pop-network/). Fastly documents [X-Served-By](https://www.fastly.com/documentation/reference/http/http-headers/X-Served-By/) and [shielding](https://www.fastly.com/documentation/guides/concepts/shielding/); node labels and a single response do not establish a permanent facility identity or global TV coverage.
- **Santa Clara, US:** [SFMIX](https://ip.sfmix.org/) explicitly declares AEC with Apple TV+ at SCL02. Its [site directory](https://sfmix.org/locations/) locates that code in Santa Clara. The [participant table](https://portal.sfmix.org/participants/) separately marks Apple Cache AS31128 inactive. That membership state does not establish inactivity of the observed AS40271 cache path, and the declaration does not place the sampled peer at SCL02.

Both points use GeoNames city coordinates, not facility coordinates. They are excluded from canonical location totals and have unassessed lifecycle. The AEC map repeats Santa Clara and adds the qualified Lyon declaration; Fastly Palo Alto is not an AEC point.

## DNS, routing and inference limits

DNS lookups here help trace the video hostnames. They do not add Apple DNS-service endpoints. Sixteen retained A/AAAA queries use Google Public DNS with ECS `0.0.0.0/0`; its vantage is separate from the HTTP client's unverified physical vantage. The Apple resolver answer `17.253.27.156` matches the Apple geofeed's Chicago entry and routes through `17.253.26.0/23`, AS6185. The actual Apple HTTP peer `149.112.115.176` has no match in that feed. Chicago is therefore retained only as a resolver-answer enrichment, not a location of the sampled connection or an AEC map point.

CDN attribution combines discovered manifest roles, HTTP headers, retained DNS chains and sampled routing. An `akadns.net` name alone would establish DNS handling, not Akamai video delivery. S3-style `x-amz` headers coexist with Apple object-store headers and do not prove an AWS origin. Apple cache-name fragments are not decoded into undocumented city or building coordinates.

The sample covers two US-storefront previews for one show from one execution environment. It does not establish subscriber, live-sport, regional failover or global delivery coverage. General Apple enterprise network requirements and retrieved job-application shells did not provide additional TV geography. All-ASN facility lists and complete third-party CDN directories remain outside the admitted TV footprint.

## Files and reproduction

- [Infrastructure assertions](../data/infrastructure/apple-tv-delivery.20261019.json), [routing evidence](../data/network/apple-tv-routing.20261019.json), and [assessment](../data/apple/tv-delivery-review.20261019.json).
- [TV city map](../data/apple/tv-delivery-localities.20261019.geojson) and [map report](../data/apple/tv-delivery-localities.20261019.report.json).
- [Full bibliography](bibliography.20261019.md); the shared Apple catalog includes AEC host research and unsuccessful retrievals as well as admitted delivery evidence.

The offline build and validation commands are in the [AEC review](apple-edge-cache.20261019.md#artifacts-and-reproduction). `capture_apple_tv.py` is the separate network capture utility; its dated specification files document the requests already made. Ordinary regeneration does not refresh or overwrite those sources. A later capture should use a new snapshot date and review the observed URLs and source scope before incorporation.
