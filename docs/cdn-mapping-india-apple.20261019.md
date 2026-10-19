# Global CDN mapping: India and Apple evaluation

Reviewed: 2026-10-19. Study published: 2026-06-06. Repository downloads retained: 2026-08-04 (ASN lists) and 2026-08-05 (map).

Anurag Bhatia's [Mapping major CDNs across the globe](https://anuragbhatia.com/post/2026/06/cdn-mapping-across-the-globe/) is useful for enriching observed network presence and identifying follow-up candidates. Its observations and the derived India/Apple comparisons below are incorporated in this repository. Indian vendors' own deployment directories require separate evidence. The study exports do not establish cache ownership or individual installations.

## Existing incorporation and source checks

| Retained evidence | Verified contents | Use |
|---|---|---|
| [Provider/ASN layer](../data/observations/cdn-mapping.20260804.geojson) and [report](../data/observations/cdn-mapping.20260804.report.json) | 13,631 accepted provider/ASN pairs across seven providers; each raw list has one rejected AS0 row | Compare positive observations across networks; geometry and country remain null |
| [City layer](../data/observations/cdn-mapping-cities.20260805.geojson) and [report](../data/observations/cdn-mapping-cities.20260805.report.json) | 11,659 accepted observations for Google, Meta and Netflix | Explore partial MaxMind city evidence; preserve the provider/ASN/city grain |
| [Combined ASN matrix](../data/raw/observations/asn-wise-cdn-mapping.202606.csv) | 6,466 unique valid ASNs, six provider columns, no Apple column | Corroboration; its six positive sets exactly match the corresponding accepted provider lists |
| [Apple CSV](../data/raw/observations/apple.202606.csv) | 974 raw rows; 973 valid unique ASNs after rejecting AS0 | Required Apple input; already present in the canonical ASN layer |

The provider CSVs contain only `asn` and `asname`; none has duplicate ASN keys. On the review date, the live [Apple CSV](https://cdn.anuragbhatia.com/web/post/2026/06/cdn-mapping-across-the-globe/apple.csv) and [combined matrix](https://cdn.anuragbhatia.com/web/post/2026/06/cdn-mapping-across-the-globe/ASN-wise-CDN-mapping.csv) matched the retained bytes. The linked [Apple JSON](https://cdn.anuragbhatia.com/web/post/2026/06/cdn-mapping-across-the-globe/apple.json) contained the same 974 ASN/name pairs, in a different order, with no additional location or endpoint fields. This check does not constitute a new measurement or a refresh of the other downloads.

Apple contributes **98 valid ASNs absent from the combined matrix**. A full union produces **6,564 distinct ASNs** across all seven providers. A left join onto the published matrix would lose those Apple-only networks. These are ASN counts, distinct from the 13,631 provider/ASN observations, and are not additional canonical records.

## Implemented comparison outputs

| Output | Records | Selection and semantics |
|---|---:|---|
| [Global ASN comparison](../data/observations/cdn-asn-comparison.20261019.json) | 6,564 | Full union of all seven providers, including the 98 Apple-only ASNs |
| [APNIC India ASN comparison](../data/india/cdn-asn-comparison.20261019.json) | 279 | Observed ASNs with an allocated/assigned APNIC entry whose recorded country is `IN` |
| [Apple ASN view](../data/observations/apple-asn.20261019.geojson) | 973 | Exact source features with null geometry and country |
| [India city view](../data/india/cdn-cities.20261019.geojson) | 515 | Exact source features with `country_code=IN` |

The [October 19 manifest](../data/manifest.20261019.json) includes the two GeoJSON views under `views` and the matrices under `observation_comparison_views`. All four outputs are excluded from canonical location, network and infrastructure totals. The matrices keep every positive source record ID, all distinct source AS names and explicit null provider references. Generated CSVs render null references as `not_observed_in_this_snapshot`. The [comparison schema](../schema/cdn-comparison.schema.json) separates ASN registration metadata from location fields.

## Indian networks

Two country definitions must remain separate: an ASN registered to an Indian organization and an observation geolocated inside India. The ASN CSVs supply neither registration country nor endpoint country. Organization-name matching is useful for candidate discovery, but cannot produce a complete Indian inventory; multinational operators also have networks outside India.

The implemented registration join uses the [APNIC extended snapshot dated June 6](https://ftp.apnic.net/stats/apnic/2026/delegated-apnic-extended-20260606.gz), retained with [provenance](../data/raw/apnic/delegated-apnic-extended.20260606.gz.provenance.json). Its header covers records through June 5 in timezone `+1000`; October 19 is the download/derivation date. As specified by the [RIR statistics format](https://www.apnic.net/about-apnic/corporate-documents/documents/resource-guidelines/rir-statistics-exchange-format/), an ASN row can represent a range, so the join checks the entire allocated/assigned interval. Reserved and available ranges are excluded. The raw header warns that allocation/assignment country does not establish where resources are used.

| Provider | Observed ASNs with APNIC country `IN` |
|---|---:|
| Google GGC | 249 |
| Netflix OCA | 115 |
| Meta FNA | 198 |
| Akamai | 65 |
| Microsoft | 20 |
| Apple | 10 |
| CloudFront | 1 |
| Distinct ASN union | 279 |

These are 658 provider/ASN pairs across 279 networks. The study's Indian headline totals of 252 GGC, 199 FNA and 74 Akamai ASNs differ from this reproducible selection by 3, 1 and 9 respectively. The available exports do not resolve the difference in classification or timing; no synthetic rows are added to match the headlines. Globally, 5,190 of the 6,564 observed ASNs have no allocated/assigned match in this APNIC-only source. Their registration remains null, not a claim that they are unregistered or outside India. A complete cross-registry country classification would require the other RIR sources.

Filtering the retained city layer on `country_code == "IN"` gives:

| Provider | India-geolocated observation rows | Distinct ASNs within those rows |
|---|---:|---:|
| Google GGC | 211 | 149 |
| Meta FNA | 146 | 106 |
| Netflix OCA | 158 | 116 |
| Combined | 515 | 203 |

The combined ASN count is a union, not the sum of provider counts. The study separately reports 252 Indian GGC ASNs, 199 FNA ASNs and 74 Akamai ASNs. Those headline counts cannot be reproduced by filtering this partial map: its coverage differs, and it has no Akamai, Microsoft, Apple or CloudFront layer. Retain the headline figures as attributed aggregates, not inferred missing rows. See the [map coverage assessment](network-evidence.20260805.md#partial-city-map).

The following selected network candidates illustrate the enrichment available from the retained ASN lists. Names are shortened for readability; the raw files retain the source strings. **Yes** means listed in that provider's June snapshot; **—** means not listed, not confirmed absence. This is a lookup by explicit ASN, not a complete country classification or a claim about the location of the observed service.

| Network candidate | ASN | GGC | Netflix | Meta | Akamai | Microsoft | Apple | CloudFront |
|---|---|---|---|---|---|---|---|---|
| Bharti Airtel | AS9498 | Yes | Yes | Yes | Yes | Yes | Yes | — |
| Reliance Jio | AS55836 | Yes | Yes | Yes | Yes | Yes | Yes | — |
| National Internet Backbone (BSNL) | AS9829 | Yes | Yes | Yes | Yes | Yes | Yes | — |
| Atria Convergence Technologies | AS24309 | Yes | Yes | Yes | Yes | Yes | Yes | — |
| Atria Convergence Technologies | AS18209 | Yes | Yes | Yes | Yes | — | — | — |
| Vodafone Idea | AS38266 | Yes | — | Yes | Yes | Yes | Yes | — |
| Vodafone Idea | AS55410 | Yes | — | Yes | Yes | Yes | Yes | — |
| Sify | AS9583 | Yes | Yes | — | Yes | — | — | — |
| Hathway | AS17488 | Yes | Yes | Yes | Yes | — | — | — |
| CtrlS | AS18229 | Yes | Yes | Yes | Yes | — | — | — |
| Tata Teleservices | AS45820 | — | — | Yes | Yes | — | — | — |
| Yotta Network Services | AS140641 | — | — | — | — | Yes | — | — |

The two Atria ASNs demonstrate why joining by company name would erase meaningful differences. Tata Teleservices must also remain distinct from Tata Communications. These observations describe other providers' TLS labels associated with the host network; they do not enumerate Sify, CtrlS, Yotta, Tata or Jio's own cloud regions, facilities or CDN products.

For Indian vendors' own CDN coverage, follow separate primary sources:

| Vendor/source | What it can add | Remaining evidence needed |
|---|---|---|
| [Tata Communications CDN resources](https://www.tatacommunications.com/resourcehub/cdn) | Provider documents and a CDN PoP map listed with a 2022 publication date | Inspect the map and confirm current, explicitly named locations before creating records; backbone PoPs and CDN PoPs require separate scopes |
| [Jio enterprise CDN](https://www.jio.com/enterprisecloud/services/ai-cloud/network/content-delivery-network/) | A provider-declared CDN service candidate | The reviewed page does not supply an itemized deployment directory; obtain site identities or a dated list before adding locations |

These links establish research paths for vendor coverage. Their product statements cannot be inferred from the ASN observations or converted from marketing coverage into point locations.

## Apple interpretation

All 973 accepted Apple observations have null geometry and country. They identify networks associated with the study's Apple TLS classification, not 973 Apple-owned caches. The retained list includes Apple AS714 and Akamai AS16625, AS20940 and AS63949, alongside access and hosting networks. The CSV lacks IP addresses, certificate names and endpoint roles, so it cannot separate native Apple delivery from third-party delivery or other Apple services.

The APNIC India subset identifies Apple observations for AS9498 (Bharti Airtel), AS9829 (National Internet Backbone), AS17813 (MTNL), AS24309 (Atria), AS38266 and AS55410 (Vodafone Idea), AS55836 (Reliance Jio), AS133619 (DESIVPS), AS152586 (Kuroit) and AS153914 (Netranex). The hosting-network examples reinforce the attribution limit: country registration plus an Apple TLS label is insufficient to classify an Apple Edge Cache installation.

The author's [December 2022 Indian study](https://anuragbhatia.com/post/2022/12/mapping_cdn_across_india/) explicitly classified its Apple observations as delivery via Akamai. That is a useful attribution caveat, not proof that every 2026 Apple observation is Akamai. Its Indian-ASN selection and older scan are also insufficient for a like-for-like trend comparison.

[Apple Edge Cache](https://cache.edge.apple.com/) provides a primary reference for Apple's managed equipment deployed in ISP partner networks and identifies AS714 as its peering network. The public program page does not identify deployed partner sites. An ASN in the study must therefore remain an investigation candidate until endpoint-specific or provider/host evidence establishes an AEC deployment.

The article also mentions more than 236 PCH/Woodynet locations for `doh.dns.apple.com`. Apple's [enterprise network documentation](https://support.apple.com/en-us/101555) identifies that hostname as DNS over HTTPS. Keep this aggregate separate from content-cache evidence: the examined exports contain no corresponding itemized Apple location list, and the map has no Apple layer. There is no basis to manufacture 236 Apple cache points or copy another provider's city coordinates onto Apple ASN rows.

The separately sourced [Apple DNS city layer](cartography-restoration.20261019.md#apple-a-bounded-dns-observation-layer) uses endpoint and geofeed evidence. It is independent of these ASN comparisons and does not resolve their content-cache attribution or geolocate their rows.

## Incorporation and remaining work

1. **Seven-provider comparison implemented.** Numeric ASN keys preserve the source record IDs and June publication date. Missing matches retain not-observed-in-this-snapshot semantics. The full union keeps all 6,564 ASNs, including Apple's 98 additions to the published matrix.
2. **Separate country views implemented.** The 515-row city view and 279-ASN APNIC country view use distinct selection rules. Each matched ASN retains the exact registry source line, range, status and allocation/assignment date. Registration country never populates endpoint geometry or location country; views are excluded from canonical totals.
3. **Keep service, host and location joins separate.** Join the ASN and city layers by both provider/dataset and ASN where the provider exists in the map, preserving one-to-many city observations. An ASN-only join across providers cannot geolocate Apple. PeeringDB facilities or IX memberships can add network context, but cannot establish cache installations.
4. **Research vendor deployments independently.** Use the Tata/Jio and Apple primary references above for service classification, then require named, dated deployment evidence for physical locations. Preserve existing provider-declared layers rather than replacing their membership with scan results.

High-impact limitations are service attribution and partial geographic coverage; the counts and join results above are reproducible, while ownership and site identity remain unestablished. The study's routed-IPv4/TLS method does not measure IPv6-only coverage, and certificate behavior or unmatched domains can cause omissions. Raw ASN lists do not permit independent replay of endpoint classification. Keep June evidence dated to June rather than treating an October review as current deployment confirmation. The retained provenance records no explicit source data license; the repository's ODC-By license does not establish redistribution terms for these downloads.

The updater runs offline from retained observations and the dated APNIC archive. New vendor deployment layers remain separate follow-up work requiring named, service-specific evidence.

## Regenerate the implemented views

```sh
python3 -B scripts/update_cdn_comparisons.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-19
python3 -B tests/validate_cdn_comparisons.py
make data/india/cdn-asn-comparison.20261019.csv
make data/observations/cdn-asn-comparison.20261019.csv
make data/observations/apple-asn.20261019.csv
make data/india/cdn-cities.20261019.csv
```

The validation covers full source-ID conservation, Apple-only ASNs, APNIC range boundaries and overlaps, reserved-range exclusion, duplicate provider/ASN rejection, registration/location separation, source hashes, CSV parity and byte-identical offline regeneration. `make RETRIEVED_AT=2026-10-19 csv` also includes all four projections; generated CSVs are ignored by Git.

## Reproduce the local comparisons

Run from the repository root. This reads retained files without downloading or rewriting data and prints the counts and network matrix used above:

```sh
python3 - <<'PY'
import csv
import json
from collections import defaultdict
from pathlib import Path

def records(name):
    path = Path('data/observations') / name
    return [f['properties'] for f in json.loads(path.read_text())['features']]

asn_rows = records('cdn-mapping.20260804.geojson')
by_provider = defaultdict(set)
names = {}
for row in asn_rows:
    asn = row['properties']['asn']
    by_provider[row['provider']].add(asn)
    names[asn] = row['properties']['as_name']

path = Path('data/raw/observations/asn-wise-cdn-mapping.202606.csv')
with path.open(newline='') as handle:
    matrix = list(csv.DictReader(handle))
matrix_asns = {int(row['ASN']) for row in matrix}
columns = {
    'Google': 'Google GGC', 'Netflix': 'Netflix OCA',
    'Meta': 'Facebook FNA', 'Akamai': 'Akamai',
    'Microsoft': 'Microsoft CDN', 'Amazon Web Services': 'AWS Cloudfront',
}
for provider, column in columns.items():
    positive = {int(row['ASN']) for row in matrix if row[column] == 'yes'}
    assert positive == by_provider[provider], provider
print('Matrix ASNs:', len(matrix_asns))
print('Apple ASNs:', len(by_provider['Apple']))
print('Apple missing from matrix:', len(by_provider['Apple'] - matrix_asns))
print('Seven-provider ASN union:', len(set.union(*by_provider.values())))

india = [r for r in records('cdn-mapping-cities.20260805.geojson')
         if r['country_code'] == 'IN']
for provider in ['Google', 'Meta', 'Netflix']:
    subset = [r for r in india if r['provider'] == provider]
    print(provider, len(subset), len({r['properties']['asn'] for r in subset}))
print('India total:', len(india), len({r['properties']['asn'] for r in india}))

providers = ['Google', 'Netflix', 'Meta', 'Akamai', 'Microsoft',
             'Apple', 'Amazon Web Services']
print('ASN / source name /', ' / '.join(providers))
for asn in [9498, 55836, 9829, 24309, 18209, 38266, 55410,
            9583, 17488, 18229, 45820, 140641]:
    flags = ['Yes' if asn in by_provider[p] else '—' for p in providers]
    print(asn, names[asn], *flags, sep=' / ')
PY
```

Existing schema, provenance and regeneration checks are documented in [network evidence](network-evidence.20260805.md#reproduction). No new scan is required for these comparisons.
