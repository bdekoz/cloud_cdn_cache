# Russian Federation infrastructure reassessment

Date: 2026-10-11

This review reassesses `country_code=RU` coverage, creates a bounded Yandex certification-derived layer, and reviews eight domestic provider families across nine product/operator surfaces. It is not an exhaustive market census or a ranking by capacity. Cloud hierarchies, owned data centers, colocation, edge metros, and independent geolocation observations remain separate units.

## Serialized findings

| File | Meaning |
|---|---|
| [`data/yandex/data-centers.20261011.geojson`](../data/yandex/data-centers.20261011.geojson) | Five provider-documented data-center localities; null geometry and unknown lifecycle |
| [`data/yandex/image-claim-review.20261011.json`](../data/yandex/image-claim-review.20261011.json) | Review of all nine cards in the supplied image; five named identities corroborated, four unnamed entries not normalized |
| [`data/russia/provider-assessment.20261011.json`](../data/russia/provider-assessment.20261011.json) | Source-backed provider assessment, edge rechecks, source age, coverage limits and access gaps |
| [`data/russia/locations-and-observations.20261011.geojson`](../data/russia/locations-and-observations.20261011.geojson) | A derived RU view with 91 retained records: seven edge declarations, 79 observations, five Yandex localities |
| [`data/manifest.20261011.json`](../data/manifest.20261011.json) | Updated index: 27,395 canonical records across 29 layers; the Russia view is excluded from canonical counts |

The pre-review RU coverage was seven edge records and 79 Google city-geolocation observations, with no normalized domestic cloud hierarchy or owned data-center layer. The 79 observations are not owned facilities. Historical Russian labels in the 2023 Google, Netflix, Akamai, and Cloudflare CSVs remain separate, rather than being promoted to current locations.

## Yandex and the supplied image

The [supplied X post](https://x.com/CrimeanVoyager/status/2109158415402479630) has one original image containing nine cards. Its five named identities are Kaluga, Vladimir, Sasovo, Mytishchi, and Ivanteevka. The four additional cards lack specific identities or localities and could overlap those named sites. They generate no records.

The [provider-hosted 2023 PCI attestation](https://storage.yandexcloud.net/yc-compliance/certificates/20230921_Yandex_DC_AOC.pdf), dated 2023-09-28, lists all five localities in its facility scope. The [2025 ISO certificate](https://storage.yandexcloud.net/yc-compliance/certificates-2025/ISO/INT/ISO-27001-01-2025-EN.pdf), dated 2025-10-23, corroborates Kaluga, Vladimir, Sasovo, and Mytishchi. Ivanteevka remains explicitly a historical identity with 2023 evidence; its omission from a different certification scope does not prove closure. Certification coverage is not an exhaustive current fleet directory.

All five records use medium confidence, null coordinates, unknown lifecycle, and source-specific certification dates. Stable IDs derive from the corroborated locality name, not from image order or a fabricated provider site code. No exact building positions are inferred from the pictures.

The image repeats Kaluga's “Grabtsevo” subtitle and 63 MW figure under Vladimir. Similar building illustrations recur across cards, and their provenance is unverified. None of its MW figures is promoted to canonical capacity. All nine cards and their accepted or rejected identity matches remain inspectable in the image-review JSON, with raw post metadata and the original JPEG preserved.

The [provider's own statement](https://yandex.ru/company/news/09-10-2026-01), published October 9 and updated October 11, reports stopped operations at Sasovo and Vladimir and partial disruption at Kaluga. These are dated operational reports inside properties. They do not imply permanent retirement, and the image's red crosses do not establish complete destruction. Current operating status for Mytishchi and Ivanteevka is not inferred.

Yandex Cloud's [availability-zone documentation](https://yandex.cloud/en/docs/overview/concepts/geo-scope) separately lists `ru-central1-a`, `-b`, `-d`, `-e`, and the BareMetal zone `-m`. This review does not infer a one-to-one relationship between those zones and the five named data-center localities.

## Existing international edge providers

Google's October peering snapshot still lists Moscow and Saint Petersburg as edge metros. CacheFly's captured [network map](https://www.cachefly.com/network-map/) also lists those two metros. Neither source identifies one building per point.

The returned [Cloudflare component feed](https://www.cloudflarestatus.com/api/v2/components.json) lists DME and LED with operational service status, while the retained August layer has DME, LED, and KJA. KJA is absent from the returned feed; this is a listing difference, not proof of facility closure. Page metadata is dated **2026-08-27**; the returned DME and LED component update timestamps are September 17 and September 10 respectively. Those timestamps and the October retrieval date remain separate, and no independent health measurement was performed. The derived RU view preserves the seven retained edge records and their original retrieval dates; the assessment records the recheck separately.

## Domestic provider review

| Provider or platform | Verified evidence | Result and boundary |
|---|---|---|
| Yandex | Two certification scopes and a current provider statement | Five named localities normalized; lifecycle remains separate from dated disruption reports |
| Selectel | [Location hierarchy](https://docs.selectel.ru/infrastructure/locations/), updated October 5 | Three Russian regions and seven zones: Saint Petersburg 2, Moscow 4, Novosibirsk 1. Globally the source lists 4 countries, 6 regions, 11 zones and 26 pools. Groups, partners, pools and segments are not individual owned buildings |
| Cloud.ru Advanced | [Region/zone and endpoint directory](https://cloud.ru/docs/advanced/overview/az-and-endpoints) | `ru-moscow-1` with four explicit zone IDs: a, b, c and e; ready for a scoped connector |
| Cloud.ru Evolution | [VM documentation](https://cloud.ru/docs/virtual-machines/ug/topics/concepts__virtual-machines) | Three zones with published UUIDs; preserve these independently of Advanced |
| IXcellerate | [Scalability directory](https://ixcellerate.ru/why-ixcellerate/scalability/) | MOS1–MOS5 explicitly operating. MOS6, MOS7, MOS8, MOS11 and MOS12 have design, launch-preparation or future-plan language and must retain those distinctions |
| MTS Web Services / MWS | [Cloud platform](https://mws.ru/cloud-platform-for-business/) | Provider/product presence established; complete site IDs and owned-versus-partner relationships remain unresolved |
| VK Cloud | [Provider's public documentation repository](https://github.com/vk-cs/docs-public) | Documentation source found; exact Russian membership remains to be extracted. Kazakhstan must remain a separate country scope |
| Rostelecom-DC / DataLine | [Provider website](https://rt-dc.ru/) | Web reader returned HTTP 403; no guessed inventory or subsidiary/site double counting |
| 3data | [Colocation page](https://3data.ru/services/colocation) | Web reader succeeded but raw capture returned HTTP 403. Facility directory identities remain an explicit gap |

The strongest next normalization candidates are Selectel's hierarchy, the two separate Cloud.ru surfaces, and IXcellerate's itemized lifecycle directory. The assessment serializes their reviewed facts and gates; this change does not claim those future connectors or a complete Russian facility inventory have already been implemented.

## Reproduction and validation

Raw inputs and hash sidecars live under `data/raw/yandex/` and `data/raw/russia/`. The updater uses retained snapshots, including `pdftotext -layout` extraction from the certification PDFs. Requirements are the Python dependencies in `requirements.txt`, jq, and Poppler's `pdftotext`.

```sh
python3 -B scripts/update_russia.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-11
python3 -B tests/validate_russia.py
make check
make RETRIEVED_AT=2026-10-11 csv
```

Validation checks certification dates, identity uniqueness, null geometry, unknown lifecycle, dated provider reports, rejected image claims, source hashes, CSV parity, exact RU-view membership, global ID uniqueness, manifest counts, view exclusion, and byte-for-byte offline regeneration.
