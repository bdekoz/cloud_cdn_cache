# Apple cache host and routing follow-up

Built 2026-10-19. This follow-up adds three host/policy assertions, ten sampled routing observations and 40 unlocated Apple CDN candidates. It adds no cache map points: the [existing map](apple-edge-cache.20261019.md) still contains Santa Clara and Lyon, with their original program and lifecycle qualifications. The new evidence does not establish additional Apple TV delivery locations.

## Host declarations and identity

[Giganet Hungary's history](https://www.giganet.hu/rolunk/) reports installation of Netflix and Apple caches in 2024. Its [infrastructure description](https://www.giganet.hu/rolunk/infrastrukturank/) names Budapest and Nyíregyháza without assigning the Apple cache to either city. The installation is retained, but cache placement, current operation, AEC program identity and the relationship to the BIX pilot remain unresolved. The Hungarian and Ukrainian operators sharing the Giganet name are not merged.

[IX Australia's content-network page](https://ix.asn.au/services/content-network/) explicitly includes Apple among locally hosted caches. It does not identify individual cache sites. A separate Netify Brisbane classification and the earlier QLD-IX access policy help identify a research target; they do not supply a primary cache-to-city assignment. [LU-CIX's route-server policy](https://www.lu-cix.lu/solutions/route-servers/) explicitly documents 31128 as a special `peer-as` value for Apple Edge Cache. That is a policy identifier, not a location.

[RIPE's AS31128 registration](https://rdap.db.ripe.net/autnum/31128) names SHAZAM-AS and Apple Distribution International Ltd. as registrant. This resolves the registration question left open by the earlier PeeringDB retrieval failure. Registration status, the registry name, operator AEC labels and observed routing are separate claims; the registrant's address cannot locate a cache.

## Candidate coverage

[Netify's Apple CDN directory](https://www.netify.ai/resources/cdn/apple-cdn) combines Apple networks, ISP partners and hosting classifications. Its captured overview reports 194 cities, 69 countries, 97 networks, 304 ASNs and 8,957 IPs. These publisher aggregates are not cache or appliance counts. Its [methodology](https://www.netify.ai/documentation/data-feeds/v2/objects/geolocation) describes city inference from collectors and analysis, with IPinfo as a country fallback. Row observation dates are unavailable; retrieval on October 19 does not establish a deployment date or current service operation.

| Captured country page | Candidate rows | Useful leads and limits |
| --- | ---: | --- |
| [India](https://www.netify.ai/resources/cdn/apple-cdn/country/in) | 8 | Netplus Broadband AS133661; four Apple-network rows and three hosting classifications. No cache locality admitted. |
| [Russia](https://www.netify.ai/resources/cdn/apple-cdn/country/ru) | 3 | Vimpelcom AS3216, Inetcom Carrier AS35598 and Kvant-Telekom AS43727. All city labels are absent. |
| [UAE](https://www.netify.ai/resources/cdn/apple-cdn/country/ae) | 2 | Gcore and Melbicom hosting classifications only. Neither establishes an embedded Apple cache. |
| [Hungary](https://www.netify.ai/resources/cdn/apple-cdn/country/hu) | 3 | Giganet AS42864, Omonia AS44306 and a Gcore hosting classification. |
| [Australia](https://www.netify.ai/resources/cdn/apple-cdn/country/au) | 21 | ISP candidates include Aussie Broadband, Internet Association of Australia, Superloop and Vocus; other ASN rows include CEnet, Wireline and Queensland Government Business (IT). City labels remain unverified for cache placement. |
| [Ukraine](https://www.netify.ai/resources/cdn/apple-cdn/country/ua) | 3 | Ukrainian Backbone Networks AS61159 plus two hosting classifications. No cross-country Giganet identity join. |

All 40 rows retain null geometry and unverified AEC/Apple TV status. The categories are seven Apple-network rows, eleven ISP-partner candidates, ten other-ASN candidates and twelve hosting classifications explicitly excluded as AEC evidence. Eight rows lack an individual sample IP or prefix. China and Saudi Arabia are absent from the captured country directory; that is a source-coverage gap, not evidence of absent infrastructure.

## Routing findings

RIPEstat network-info queries checked the sample IP in each of the ten other-ASN rows. Nine reported ASNs match the sampled prefix origin. For Giganet, Netify associates `88.209.219.16` with AS42864, while the [routing response](https://stat.ripe.net/data/network-info/data.json?resource=88.209.219.16) reports `88.209.219.0/27` originating from Apple-registered AS31128. Both labels are preserved: a publisher's host association and the observed route origin need not identify the same party.

These are routing observations for third-party sample addresses, not actual Apple TV HTTP peers. They do not prove cache software, location, service health or that every address in a prefix serves Apple content. Only Inetcom AS35598 matches an Apple observation in the earlier June TLS comparison; the other nine missing matches do not establish new installations because the methods and dates differ.

## Remaining evidence gaps

All seven previously unlocated host/exchange leads remain held. [CEnet's general service page](https://cenet.catholic.edu.au/infrastructure-services) names Apple peering and Google/Akamai caches; its omission of AEC does not establish retirement of the earlier declared installation. The direct 1-IX looking-glass capture is a JavaScript shell, so indexed peer snippets are not admitted as current observations. A historical SFMIX slide URL returned HTTP 404; its retained response is a failed-retrieval receipt. No additional TENET or PIT-IX locality evidence was established.

The next useful measurement is a public-preview response from a known observer network, retaining the actual HTTP peer, cache-host label and time. A map addition still requires an explicit host-to-city or host-to-site join. This pass used public documents and routing APIs; it launched no target-host probes, subscriber sessions or distributed measurements.

## Artifacts and reproduction

- [Candidate assessment and routing joins](../data/apple/aec-followup.20261019.json).
- [Three host/policy assertions](../data/infrastructure/apple-aec-followup.20261019.json) and [ten routing records](../data/network/apple-aec-candidate-routing.20261019.json).
- [27-source catalog](../data/raw/apple-aec-followup/catalog.20261019.json), retaining 26 successful captures and one HTTP error, with original bytes, hashes and timestamps.
- [Bibliography](bibliography.20261019.md), expanded from 268 to 295 references while preserving all earlier entries.

Rebuild the follow-up from retained inputs without network access:

```sh
python3 -B scripts/update_apple_aec_followup.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make check
make RETRIEVED_AT=2026-10-19 csv
```

Validation checks source hashes, null candidate geometry, host/origin distinctions, historical bibliography preservation, unchanged location layers and cache maps, CSV parity and deterministic offline reproduction. The consolidated manifest now contains 3,989 network records and 429 infrastructure assertions; the 40 assessment candidates are excluded from those record totals.
