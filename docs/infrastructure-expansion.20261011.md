# Expanded connectivity infrastructure review

Date: 2026-10-11

The expanded search covers global connectivity infrastructure and calls out Russian Federation assertions separately. It follows new source-defined categories rather than restricting discovery to the existing data-center, cloud, ground-station, or fiber classifications.

The findings are serialized in [`data/infrastructure/connectivity.20261011.json`](../data/infrastructure/connectivity.20261011.json): **84 source-backed assertions across 17 categories**. The categories and record units are explicit and extensible. This is a bounded reviewed inventory, not a worldwide census or a total of equivalent physical sites. The [`Russia view`](../data/infrastructure/russia-connectivity.20261011.json) contains three repeated assertions and is excluded from canonical infrastructure counts.

## Source discovery and current evidence

The search used provider directories, current regulator listings, operator announcements, and ESA project/commissioning reports. Fifteen retained sources support the serialized collection. Publication dates, source update dates, first licence issue dates, and October retrieval dates are different fields; a page retrieved today does not automatically establish a new operational observation.

| Source-defined category | Records | Unit and principal boundary |
|---|---:|---|
| Starlink private interconnect presence | 49 | Directory entry, sometimes grouping multiple host facilities; not a Starlink-owned building or satellite gateway |
| NGSO network authorizations | 9 | Existing UK licence; not a constellation inventory or service-coverage map |
| Satellite gateway authorizations | 7 | Existing UK licence; five associated with Starlink, plus Amazon and AST SpaceMobile-related entries |
| LEO communications constellation | 1 | Starlink system-level declaration, not one row per satellite |
| Orbital compute constellation | 1 | Starmind plan; no launched computing-site count inferred |
| Space situational awareness | 1 | Stargaze system; sensors are aboard satellites, not ground stations |
| Optical ground stations | 2 | Individually described SSC Space facilities in Chile and Western Australia |
| Quantum optical ground station | 1 | Windhof experimental/commissioned optical station, not a commercial global QKD network |
| Optical/quantum network testbed | 1 | ONEST project, including real and simulated infrastructure |
| Direct-to-device satellite plan | 1 | Amazon Leo D2D plan; future deployment and acquisition conditions remain explicit |
| Submarine cable systems | 5 | Petal, three new Google systems, and the Russian Petropavlovsk-Kamchatsky–Anadyr link |
| Submarine cable branch | 1 | Newly announced Firmina branch to the Dominican Republic |
| Terrestrial fiber link | 1 | TEA NEXT system, not a surveyed alignment or live-capacity measurement |
| Terrestrial backbone network | 1 | Rostelecom aggregate declaration; unitemized access points are not fabricated records |
| Interconnection corridor | 1 | DE-CIX/CVTelecom letter of intent, not proof of a new physical cable |
| Subsea connectivity programme | 1 | Americas Connect grouping, not an additional cable asset |
| Distributed internet exchange | 1 | ACIX service and its expansion, not a separate building per member or port |

## Starlink: interconnect, gateways, and new categories

Starlink's JavaScript-only [PoP help page](https://starlink.com/support/article/45d1d256-171e-0f67-4895-5d248fa63b66) was resolved through the site's public help client to its [public topic API](https://starlink.com/api/support/v2/topics/45d1d256-171e-0f67-4895-5d248fa63b66). The retained response contains 49 private interconnect directory entries in 28 countries. Its modification timestamp is **2026-04-02**, retained alongside the October retrieval date.

The source establishes eligible host facilities in the customer's home-PoP geography. Grouped labels such as Equinix's Ashburn facilities remain one source directory entry, without expansion into guessed individual installations. Addresses are preserved as published, without geocoding or ownership inference. The article's audience metadata excludes India even though its table includes a Mumbai entry; those audience settings are preserved separately and are not used to infer facility retirement or national service authorization.

The [Ofcom register](https://www.ofcom.org.uk/spectrum/space-and-satellites/non-geo-fss), updated **2026-07-31**, supplies nine existing network licences and seven gateway licences. Five gateway licences are associated with Starlink's network licence 1239247: Morn Hill, Wherstead, Woodwalton, Chalfont, and Goonhilly. Amazon's Bude licence and the July 2026 Satco/AST SpaceMobile Goonhilly licence add other providers. Seven authorizations describe six distinct locality labels; they are not seven unique campuses. Exact legal holders and associated network-licence links are preserved, and authorization does not establish current operation or Starlink ownership.

Starlink's [October 6 update](https://starlink.com/updates) is preserved from the public page module used by its current website. It reports more than 11,000 Starlink satellites in orbit and the first 26 V3 deployments in September. Those remain provider claims, not an independently counted orbital inventory. The same announcement describes plans for up to 100,000 Starlink satellites and up to one million Starmind AI satellites. Starmind becomes the emergent `orbital_compute_constellation` category with **planned** lifecycle; none of that planning quantity becomes deployed capacity.

[Stargaze documentation](https://docs.space-safety.starlink.com/docs/tutorial-basics/stargaze/) establishes a space-situational-awareness system using onboard star trackers. It is represented at system level. The source's daily-processing claim is not expanded into ground-sensor sites or observed orbit objects.

## Optical, quantum, direct-to-device, and exchanges

ESA's [March 2026 optical-station announcement](https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Ground_station_in_Chile_ready_to_connect_to_space_via_laser) describes SSC Space's Chilean station passing acceptance testing and a second facility in Western Australia beginning tests in 2025. The former remains commissioning/ready for operations; the latter's current commercial status remains unknown. Neither has a manufactured exact coordinate.

The [July 2026 Windhof announcement](https://resilience.esa.int/archives/news/first-of-its-kind-optical-ground-station-commissioned-in-luxembourg-to-demonstrate-international-quantum-secure-communications) supplies a quantum optical ground station developed for QKD/PQC network tests. Builders, consortium leadership, and programme partners are separate roles. The [ONEST status page](https://resilience.esa.int/archives/projects/onest) records an ongoing design/testbed project with a February 2026 status date. Simulated stations are not physical records.

Amazon's [April 2026 announcement](https://press.aboutamazon.com/2026/4/amazon-to-acquire-globalstar-and-expand-amazon-leo-satellite-network) describes a Globalstar acquisition agreement expected to close in 2027 subject to conditions and a new D2D deployment beginning in 2028. The record preserves an announced agreement and future deployment; it does not report a completed acquisition or already launched D2D system.

The [ACIX expansion announcement](https://www.de-cix.net/en/about-de-cix/media/press-releases/africa-congo-internet-exchange-acix-becomes-first-distributed-ix-in-drc-with-support-from-de-cix), dated May 19, reports a distributed internet exchange in Kinshasa with an additional OADC Texaf FIH1 host presence. This is an exchange-service assertion, with partners and the host relationship distinguished from facility ownership.

## Fiber systems and emerging connectivity programmes

[Petal's September 21 announcement](https://about.fb.com/news/2026/09/announcing-petal-meta-petabit-transoceanic-cable/) describes a planned France–US system targeting service in 2029, approximately 7,000 km and one petabit/s design capacity using multi-core fiber. Partners and supplier roles are preserved. Design capacity is not lit capacity, and no surveyed route is generated.

[Google's August 11 announcement](https://cloud.google.com/blog/products/infrastructure/introducing-americas-connect/) identifies three new systems: Alisios (Dominican Republic/Panama/Chile), Canoa (Dominican Republic/Bermuda), and OlaLuz (Dominican Republic/Florida), plus a new Dominican Republic branch of Firmina. The named Americas Connect programme is represented separately, with explicit child relationships. Existing Curie, Nuvem, Sol, and Firmina references do not silently become new cable records.

[DE-CIX and CVTelecom's September 29 announcement](https://www.de-cix.net/en/about-de-cix/media/press-releases/de-cix-and-cabo-verde-telecom-plan-new-south-atlantic-interconnection-corridor) describes a letter of intent for a South Atlantic corridor linking Lisbon and São Paulo. A planned connectivity collaboration is not evidence of a newly surveyed cable or a new landing station.

For Russia, [Rostelecom's October 6 statement](https://www.company.rt.ru/press/news/d480081/) reports completion and launch of TEA NEXT. Its 96 dark fibers, DWDM-dependent capacity scenarios, and stated Moscow–Kyakhta round-trip delay remain operator/design claims, not measured capacity or route geometry. China and Mongolia are named border connections, not inferred countries traversed by the physical cable.

The [July 16 restoration statement](https://www.company.rt.ru/press/news_fill/far_east/d479069/) establishes a dated operating-status assertion for the Petropavlovsk-Kamchatsky–Anadyr submarine link. The undated [backbone page](https://www.company.rt.ru/en/about/net/magistr/) separately declares over 350 access points in Russia and abroad and participation in 17 international cable systems. Neither aggregate is expanded into invented sites or systems. These two named systems and the aggregate network form the three-record derived Russia connectivity view.

## Coverage limits and schema

The new [`infrastructure-evidence.schema.json`](../schema/infrastructure-evidence.schema.json) uses an open category vocabulary with mandatory definitions and units. New source-defined categories can be registered without altering the older location or network contracts. It validates provenance, chronology fields, party roles, relationship identities, null spatial assertions, and source-backed Point/LineString/MultiLineString geometry when applicable.

All 84 current records have null geometry. No route is drawn simply by connecting two cities. TeleGeography's [FAQ](https://www2.telegeography.com/submarine-cable-faqs-frequently-asked-questions) states that its public map paths are stylized; its [geocoded data](https://www2.telegeography.com/license-geocoded-map-data) has a source-specific licensing path. This update imports no bulk route geometry. Russian Satellite Communications Company directory/site capture failed, so a complete Russian teleport inventory remains an explicit source gap rather than guessed ground-station rows.

## Reproduction and validation

Fifteen retained primary inputs and provenance sidecars are under `data/raw/infrastructure/`. Ofcom's `.web.json` explicitly records a web-reader transcript because direct HTML retrieval returned HTTP 403. Starlink's `.js` input is the public website content module, and the `.json` PoP input is its public help API. These capture methods are explicit rather than disguised as ordinary HTML snapshots.

```sh
python3 -B scripts/update_infrastructure.py
python3 -B scripts/build_manifest.py --retrieved-at 2026-10-11
python3 -B tests/validate_infrastructure.py
make check
make RETRIEVED_AT=2026-10-11 csv
```

[`connectivity.20261011.report.json`](../data/infrastructure/connectivity.20261011.report.json) records category/unit counts, source dates, digests, article metadata, bounds and gaps. The consolidated manifest counts the 84 infrastructure assertions separately from 27,395 location records and 3,125 network-evidence records. The three-record infrastructure view is excluded from those totals. CSV uses its own lossless projection.

Validation covers source hashes, publication/update chronology, exact directory and licence joins, grouped facility boundaries, planned-versus-operating semantics, open categories, rejected undefined categories/duplicate identities/broken relationships/invalid geometry, CSV parity, view membership, manifest counts, and deterministic offline reproduction.
