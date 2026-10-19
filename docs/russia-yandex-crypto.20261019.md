# Russia enrichment review: Yandex and crypto exchanges

Reviewed October 19, 2026. This extends the [October 11 Russia assessment](russia-reassessment.20261011.md) with a focused Yandex review and five exchange examples. It is a bounded source assessment, not a census of exchanges or a current facility inventory.

**Yandex offers substantial usable enrichment:** cloud-zone identities, city-level CDN declarations and service-specific prefixes. **Exchange evidence belongs in a separate application/network layer:** the reviewed sources do not establish current Russian origin hosting for any of the five exchanges. Russian business operations, IP registration, visible network endpoints and physical hosting require separate fields.

The [machine-readable assessment](../data/russia/enrichment-assessment.20261019.json) retains the counts, source hashes, candidates, DNS results and admission criteria. This is the pre-implementation review. Its approved sequence is now [implemented](russia-enrichment.20261019.md), with new location, network, application and comparison layers. The review itself remains an assessment excluded from canonical totals.

## Existing coverage and quality findings

Filtering the [frozen pre-implementation manifest](../data/raw/repository/manifest-before-russia.20261019.json) on `country_code=RU` produces **100 records with 100 distinct IDs**, including eight null geometries:

| Layer | RU records | What they represent |
| --- | ---: | --- |
| Google edge | 2 | Provider-declared edge cities |
| Cloudflare edge | 3 | Retained August declarations; October 11 recheck returned only two of these codes |
| CacheFly locations | 2 | Provider-declared edge cities |
| CDN city observations | 79 | Google-associated ASN/city geolocations from the June study |
| Yandex data centers | 5 | Certification-documented localities with unknown lifecycle |
| Akamai legacy locations | 9 | Historical 2023 city declarations restored on October 19 |

The retained [91-record RU view](../data/russia/locations-and-observations.20261011.geojson) predates the Akamai restoration. The difference is nine historical records, not nine newly opened facilities. At this baseline there was no normalized Yandex cloud/CDN layer or crypto-exchange layer. The separate Russia connectivity view also has a different unit and is excluded here.

The main risks are **high-confidence, high-impact interpretation errors**: treating 100 mixed records as operating facilities, treating old lifecycle declarations as current health, or joining an exchange's business country to its hosting country. No duplicate RU identifiers were found. Five missing geometries belong to Yandex certification localities; three belong to retained edge records. The review preserves these unknown coordinates.

## Yandex candidates

| Evidence | Reviewed result | Appropriate enrichment |
| --- | --- | --- |
| [Availability zones](https://yandex.cloud/en/docs/overview/concepts/geo-scope), updated July 13 | `ru-central1-a`, `-b`, `-d`, `-e`; separate BareMetal `-m` | Five zone identities with distinct service scope; no inferred facility join |
| [Regions](https://yandex.cloud/en/docs/overview/concepts/region) | Russia and Kazakhstan have separate regional resources; `kz1-a` belongs to Kazakhstan | Region/zone hierarchy with country boundaries |
| [CDN city directory](https://yandex.cloud/en/docs/cdn/concepts/points-of-presence), updated September 14 | 35 cities across eight source country labels; 27 appear under the source's Russia label; separately, a global claim of 78 PoPs | City-level declarations, with totals retained separately |
| [Cloud public IP documentation](https://yandex.cloud/en/docs/overview/concepts/public-ips), updated August 21 | 33 VPC and seven BareMetal IPv4 prefixes, plus separately identified supporting-service addresses | Service-specific `provider_prefix` evidence; physical geography remains unknown |
| [CDN prefix feed](https://tech.cdn.yandex.net/prefixes/yc.json) | 115 distinct prefixes: 107 IPv4 and eight IPv6 | CDN network evidence; no prefix-to-city mapping is supplied |
| [Cloud Interconnect documentation](https://yandex.cloud/en/docs/interconnect/concepts/pub-con) and [RIPEstat](https://stat.ripe.net/data/as-overview/data.json?resource=AS200350) | Yandex Cloud ASN 200350, corroborated by the current holder response | A stable network join key, independently of physical location |

One CDN city needs country review: the provider places **Simferopol** under Russia. The assessment preserves that source label and leaves normalized country unset. A connector must resolve the territorial attribution before including this row in a normalized RU view. It must also avoid interpreting 35 cities, 78 PoPs and 115 prefixes as interchangeable counts.

The CDN feed contains one overlapping pair, `188.72.105.0/24` and its `/27` subprefix. Preserve both declarations and their provenance; do not double-count address coverage. The public IP page distinguishes customer pools from service-support addresses. A match identifies a documented service range, not a particular tenant or building.

The [provider's incident statement](https://yandex.ru/company/news/09-10-2026-01), retrieved again on October 19, still carries its October 11 update. It reports stopped operations in Sasovo and Vladimir and partial disruption in Kaluga. No later recovery confirmation was established in this bounded review. Preserve these dated reports separately from lifecycle and current health; the older cloud-zone list does not resolve that question. Certification scope remains a partial identity source, including only historical evidence for Ivanteevka.

There is also a direct link to the [India/Apple comparison work](cdn-mapping-india-apple.20261019.md): the existing June study records **Akamai, Apple and Microsoft TLS associations on AS200350**, named Yandex.Cloud LLC in the source. The assessment preserves the three original record IDs. These observations do not identify a city, prove Apple-owned caches in Russia, establish current service, or identify an exchange customer.

## Crypto exchanges

The cohort covers ABCEX, Bybit, EXMO.me, Garantex and Grinex. Bybit is a useful comparison with explicitly declared hosting outside Russia; membership in this review is not a claim that each exchange is Russian.

| Exchange | Evidence reviewed | Decision |
| --- | --- | --- |
| ABCEX | Provider documents [Russian cash offices](https://abcex.io/documentation/en/cash.html) and links its [API reference](https://abcex.readme.io/reference/intro), including `hub.abcex.io`. Website and WebSocket DNS answers route through AS201706; RIPE identifies SERVICEPIPE and an RU-registered address block | Retain endpoint, routing and registry assertions. Cash offices are not compute facilities; origin hosting remains unknown |
| Bybit | [Operator API FAQ](https://bybit-exchange.github.io/docs/faq) declares AWS Singapore, AZ IDs `apse1-az2` and `apse1-az3`. Both sampled production API names returned `cloudfront.net` CNAMEs | Retain the provider-declared hosting relationship and observed CDN path separately; do not add a Russian location |
| EXMO.me | [Operator announcement](https://exmo.me/blog/uvedomleniya/termination-and-liquidation), July 24, 2026, says it is terminating operations and entering liquidation. The website still resolves into AS57724, identified as DDOS-GUARD, with an RU-registered address block | Retain dated status and website-network evidence. DNS availability does not establish active trading; the notice applies to EXMO.me |
| Garantex | [DOJ's March 7, 2025 account](https://www.justice.gov/opa/pr/garantex-cryptocurrency-exchange-disrupted-international-operation) reports domain seizures and server seizures by German and Finnish authorities. [Treasury's August 14 account](https://home.treasury.gov/news/press-releases/sb0225) describes operations from Moscow and Saint Petersburg | Historical events and attributed entity context only. Neither business location nor the nationality of the seizing authority is sufficient to populate current server geography |
| Grinex | The same Treasury release describes a successor relationship to Garantex. A current domain-to-operator binding was not established | Re-verify identity before endpoint ingestion; inherit neither Garantex's status nor infrastructure |

The two registry-country findings above are supported by the retained RIPE responses: [ABCEX-address RDAP](https://rdap.db.ripe.net/ip/109.238.90.238), [EXMO.me-address RDAP](https://rdap.db.ripe.net/ip/185.178.208.182), [AS201706 overview](https://stat.ripe.net/data/as-overview/data.json?resource=AS201706) and [AS57724 overview](https://stat.ripe.net/data/as-overview/data.json?resource=AS57724). **`registry_country_code=RU` is not `origin_country_code=RU`.** An exchange can use a protection/CDN network while its application runs elsewhere.

## Bounded DNS pilot and limits

The [retained DNS responses](../data/raw/crypto/endpoint-dns.20261019.json) contain 15 queries: A, AAAA and CNAME for `abcex.io`, `hub.abcex.io`, `api.bybit.com`, `stream.bybit.com` and `exmo.me`. They include query URLs, UTC timestamps, response codes, answer TTLs and authority sections when returned. The pilot used Google's public DNS HTTPS resolver without a specified client subnet or located probe. All 15 returned NOERROR; an empty AAAA or CNAME answer is not NXDOMAIN.

The sampled addresses matched **none of the reviewed Yandex public-IP and CDN prefixes**. This is a narrow negative result: it does not rule out Yandex origin services, other Yandex ranges, private dependencies or a different resolver/time returning different answers. All origin-country and facility fields remain null. No trading/account API requests or origin discovery were performed.

Two access problems are explicit in the assessment. Fetching `grinex.io` returned HTTP 403, while the public reader returned a journal title; this is insufficient to establish a current exchange identity. The EXMO.com historical split article returned a soft 404 to the raw fetch while the reader exposed an older article. Its captured error page is excluded from structured identity and hosting assertions.

## Enrichment sequence

1. **Yandex hierarchy and edge declarations:** implement separate cloud-zone and CDN-city connectors from the retained explicit lists. Resolve the country exception and preserve service scope, source age and unknown facility joins.
2. **Yandex network evidence:** use the existing prefix/routing contract for VPC, BareMetal and CDN sources; preserve service-support roles and overlaps. Join ASN 200350 to the existing CDN observations without inventing country or customer relationships.
3. **Exchange evidence:** establish a dedicated application-endpoint contract before normalizing the pilot. Its grain should be one entity/hostname/role/observation, with source and observation timestamps, resolver, RR type, CNAME chain, address, routing ASN, registry country, attributed hosting claim, confidence and independently nullable origin geography. The current network schema lacks an explicit hostname/tenant-hosting relationship and should not be stretched into a facility record.
4. **Russian ASN comparison:** evaluate a RIPE delegated-ASN snapshot matched to the June study, following the APNIC interval-join approach. Keep registration-filtered results separate from geographic observations.
5. **Broader domestic providers:** the earlier Selectel, Cloud.ru and IXcellerate candidates remain relevant. Re-fetch them before implementation; this focused review does not refresh their inventories.

Canonical admission requires explicit location membership or defensible independent geographic evidence. Endpoint resolution alone admits only an observation. This review established the source decisions and reproducible pilot; the [implementation record](russia-enrichment.20261019.md) documents the completed connectors and Simferopol normalization to Ukraine while preserving the original source label.

## Reproduction

Run from the repository root with the existing Python requirements installed:

```sh
python3 -B scripts/review_russia_enrichment.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
python3 -B tests/validate_russia.py
```

The assessment generator reads retained inputs only. Its counts exclude the table's header row, validate prefix syntax and uniqueness, identify overlaps, reconcile canonical layer hashes and RU IDs, and retain the older country-view denominator. `--output-root /tmp/russia-review` writes a separate copy for byte comparison. It does not refresh DNS or imply new observation times.

Raw Yandex and exchange evidence lives under `data/raw/yandex/` and `data/raw/crypto/`, with SHA-256 provenance sidecars. Some documentation update dates are visible in the web reader but absent from the raw HTML's rendered text; those receipts state that date basis. Retrieval dates, provider update dates, historical incident dates and DNS query times remain distinct. Source-specific redistribution terms still apply.
