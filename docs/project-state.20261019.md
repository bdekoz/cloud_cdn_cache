# Project state and handoff

Saved 2026-10-19. The approved enrichment implementations and Apple cache follow-up are committed through [`5b90a8e`](https://github.com/bdekoz/cloud_cdn_cache/commit/5b90a8e) and pushed to `origin/main`. Implementation and validation for these passes are complete. Further coverage depends on the source evidence and measurement inputs listed below.

## Published state

| Checkpoint | Completed work |
| --- | --- |
| [`286265d`](https://github.com/bdekoz/cloud_cdn_cache/commit/286265d) | [Completion review](enrichment-completion.20261019.md) covering China, Indian vendors, Gulf identity/routing, Russia and hosted monitoring |
| [`93b74f7`](https://github.com/bdekoz/cloud_cdn_cache/commit/93b74f7) | [Apple TV delivery](apple-tv-delivery.20261019.md) and [Apple cache locality review](apple-edge-cache.20261019.md) |
| [`5b90a8e`](https://github.com/bdekoz/cloud_cdn_cache/commit/5b90a8e) | [Apple candidate follow-up](apple-aec-followup.20261019.md): 40 unlocated classifications, ten routing observations and three host/policy assertions |

The [October 19 manifest](../data/manifest.20261019.json) is the consolidated index. Its build date does not replace the observation and retrieval dates of individual sources.

| Collection | Retained count | Interpretation |
| --- | ---: | --- |
| Canonical location layers | 39 layers; 28,024 records | Mixed infrastructure and observation units; not a physical-site total |
| Derived location views | 10 | Repeat canonical records |
| Geographic footprint views | 5 | China 147, Gulf 9, completion 13, Apple TV 2 and Apple cache 2 reference points; overlapping views |
| ASN comparison views | 3 | Repeat underlying observations |
| Network evidence | 10 layers; 3,989 records | Prefixes, routing, registrations and endpoint checks |
| Infrastructure evidence | 9 layers; 429 assertions | Source-specific units and dates |
| Application endpoints | 15 DNS observations; 5 entities | Separate from location and network totals |
| Vendor registry | 47 references | Separately counted metadata |
| [Bibliography](bibliography.20261019.md) | 295 references | Includes retained failed-retrieval receipts and held leads |

The Apple cache map contains Santa Clara, with an explicit AEC host/site declaration, and Lyon, with an Apple-cache declaration whose AEC program identity is unconfirmed. Both retain unresolved current lifecycle. The Apple TV view also contains Santa Clara and a Fastly Palo Alto reference point; the views overlap and cannot be added as deployments. The follow-up's 40 classifications have null geometry and unverified AEC/Apple TV status. Its ten routing samples are third-party candidate addresses, not observed Apple TV HTTP peers.

## Remaining evidence dependencies

| Area | Evidence needed before expanding or revising coverage |
| --- | --- |
| Apple caches | Explicit cache-to-city/site joins for the seven held host/exchange leads and new candidates. Giganet Hungary's 2024 installation has no unique city assignment; its reported AS42864 host association and observed AS31128 origin remain separate. |
| Chindata | Explicit aliases joining nine public H/W codes to named campuses or disclosed properties, with phase-specific lifecycle evidence. |
| Other China vendors | Consolidated China Mobile/Unicom ECS directories, fuller GDS/VNET identities, and locality evidence for the remaining held records. Existing product, portfolio and phase assertions keep their own scope. |
| AWS and Oracle Gulf coverage | Address evidence for eight unresolved interconnect endpoints; explicit launch/status evidence for Saudi AWS core regions, Muscat Local Zone and Fujairah CloudFront. Routing and registry presence alone cannot establish operation or placement. |
| Russia and exchanges | Dated evidence of Yandex recovery beyond the retained October 11 update, Cloud.ru parent-region identifiers, and supportable application-origin evidence. The Grinex HTTP 403 receipt does not locate infrastructure. |
| Additional measurements | Public-preview observations from known observer networks, retaining actual HTTP peers, timestamps and cache-host labels. RIPE Atlas remains dependent on the target list, credentials/credits and measurement specification described in [network evidence](network-evidence.20260805.md). |

The [completion ledger](../data/enrichment/completion-review.20261019.json) accounts for every previously held China record and Gulf endpoint. The [Apple follow-up assessment](../data/apple/aec-followup.20261019.json) records candidate dispositions and next steps. These gaps are explicit evidence dependencies, not omitted implementation tasks. Existing Gulf source monitoring remains weekly and also runs on relevant input changes.

## Validation and resumption

All 18 suites in `make check` passed for the published data, including schema checks, source hashes, unchanged historical layers, CSV parity and deterministic offline reproduction. The complete October 19 CSV export passed. No data edits remain pending at the saved implementation checkpoint.

To reproduce the latest Apple outputs and consolidated indexes from retained inputs:

```sh
python3 -B scripts/update_apple_tv.py
python3 -B scripts/update_apple_aec.py
python3 -B scripts/update_apple_aec_followup.py
python3 -B scripts/build_bibliography.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
make check
make RETRIEVED_AT=2026-10-19 csv
```

For further enrichment, start from the relevant disposition ledger, retain new evidence separately with its actual retrieval date, then rebuild and validate the affected layers. Keep hosting, routing, program identity, service delivery, location and lifecycle as separate claims. [Make usage](make.md) and [methods](methods.md) describe the existing workflow.

## Local dyad status

At 2026-10-19 21:18:36 UTC, the local marker store contained no window or ledger for `cloud_cdn_cache.bkoz`; no open dyad was recorded for this repository. This is a local status check at the saved time, not a claim about other machines or projects.
