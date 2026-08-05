# Meta FNA and Netflix OCA Data Recovery

Date: 2026-08-04

This recovery restores fields that can be derived from public or repository-local evidence without overwriting the legacy datasets. It does not claim to recover the unknown Netflix records beyond the original passive-DNS result cap.

## Recovery outputs

| Artifact | Purpose |
|---|---|
| [`data/raw/meta/fna.20240524.retrieved-20260804.csv`](../data/raw/meta/fna.20240524.retrieved-20260804.csv) | Exact public Meta source snapshot retrieved on 2026-08-04 |
| [`data/raw/meta/fna.20240524.retrieved-20260804.provenance.json`](../data/raw/meta/fna.20240524.retrieved-20260804.provenance.json) | Source URL, retrieval date, checksum, counts, mutability, and licensing warning |
| [`data/recovered/meta_fna.20240524.csv`](../data/recovered/meta_fna.20240524.csv) | Meta observations with restored hostname, IP, ASN, and AS-name fields |
| [`data/recovered/meta_fna.20240524.recovery.json`](../data/recovered/meta_fna.20240524.recovery.json) | Meta alignment audit, output checksum, and seven source-only records |
| [`data/recovered/netflix_oca.20230802.csv`](../data/recovered/netflix_oca.20230802.csv) | Netflix legacy rows with reconstructed hostname or partial hostname pattern |
| [`data/recovered/netflix_oca.20230802.recovery.json`](../data/recovered/netflix_oca.20230802.recovery.json) | Netflix confidence counts, checksum, partial records, and unresolved-tail status |

## Meta FNA recovery

The source is the public Google Sheet linked from Anurag Bhatia's [2024 FNA report](https://anuragbhatia.com/post/2024/05/facebook-fna-update-2024-and-backbone-analysis/). The retrieved snapshot contains:

- 8,360 source observations
- 8,008 unique FNA hostnames
- 1,795 distinct IPv4 ASNs
- 1,748 distinct IPv6 ASNs
- Hostname, IPv4, IPv6, IPv4/IPv6 ASN, IPv4/IPv6 AS name, city, country, and airport code

Ordered airport-code alignment matches all 8,353 legacy rows and identifies seven additional rows in the retrieved source: one BNU, one TFL, three REC, and two LIM records. Repeated airport codes prevent the link between an individual legacy jittered point and an individual source record from being stronger than medium-confidence. The recovered hostname and network fields come directly from the source and do not depend on that row-level link.

The source contains 332 hostnames with multiple observations. Those observations carry different IP addresses in every duplicate group, so the recovery preserves all 8,360 observations and supplies both a stable `source_record_id` and an observation ordinal. It does not collapse changing addresses into one lossy row.

The public article reported 8,014 unique strings, while the sheet retrieved on 2026-08-04 contains 8,008. The sheet is therefore treated as mutable. The provenance manifest identifies the retrieved bytes with a SHA-256 checksum rather than claiming they are an immutable copy of the sheet as it existed in May 2024.

Coordinates are the median of the legacy coordinate cluster for each airport code. They are labeled `airport_or_city` with `coordinate_method=median_of_legacy_airport_code_cluster`. The matching legacy jittered point, when available, remains in separate `legacy_point_latitude` and `legacy_point_longitude` fields.

## Netflix OCA recovery

The legacy Netflix CSV retained enough parsed hostname components to reconstruct:

- 9,501 complete hostnames from 9,507 rows
- 9,044 unique reconstructed hostnames
- 8,546 high-confidence rows
- 955 medium-confidence rows in which spaces in the parsed ISP name were restored as hyphens
- 6 partial rows whose ISP slug was not retained

The templates are:

```text
ipv4-cNNN-aaaNNN-ix.1.oca.nflxvideo.net
ipv6-cNNN-aaaNNN-<isp-slug>-isp.1.oca.nflxvideo.net
```

The output preserves every legacy column and adds the reconstructed hostname, partial pattern, method, confidence, source row, snapshot date, and logical-hostname observation count. Duplicate observations are retained rather than silently discarded.

The six incomplete rows use an explicit `<isp-slug>` placeholder. No hosting-provider name was guessed into the DNS label.

### Unresolved historical tail

The repository README records that the original SecurityTrails subdomain result was capped at 10,000. Records omitted before the local file was produced cannot be recovered from repository-local evidence. Exact recovery requires the original export or authorized access to a passive-DNS source with historical first-seen/last-seen data. Current ASN- or TLS-based observations can enrich coverage, but must be stored as a separate measurement rather than represented as recovered 2023 hostnames.

## Regeneration and validation

The checked-in raw snapshot is the deterministic input. Rebuild and validate with:

```sh
python3 -B scripts/recover_meta_fna.py
python3 -B scripts/reconstruct_netflix_oca.py
python3 -B tests/validate_recovery.py
```

To deliberately take a new snapshot of the mutable Meta sheet, first replace the raw input and update its retrieval date in the filename and script arguments:

```sh
curl -sS -L --fail \
  'https://docs.google.com/spreadsheets/d/e/2PACX-1vTD0zNZAdQOrmUB-vcp1gsWNGbfOk-t53Hfib-ftIWcHbs-4GhCBjzw4J8ZwYjqZpYARe6TvkzF6aMV/pub?output=csv&gid=1062418616&single=true' \
  -o data/raw/meta/fna.20240524.retrieved-20260804.csv
```

The validation checks exact record counts, unique identities, ASN counts, source-only Meta rows, reconstruction-confidence totals, hostname syntax, and all recorded SHA-256 values.

## Licensing note

The public sheet does not state an upstream redistribution license in the retrieved file. Its provenance manifest records that uncertainty. Confirm the source author's terms before publishing the raw or recovered Meta artifacts under the repository's ODC-By license. Passive-DNS results used for any later Netflix tail recovery require the same source-specific licensing review.
