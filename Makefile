RETRIEVED_AT ?= 2026-08-05
RETRIEVED_TAG ?= $(subst -,,$(RETRIEVED_AT))
MANIFEST := data/manifest.$(RETRIEVED_TAG).json
CSV_GEOJSON := $(shell jq -r '(.layers + .views)[] | .files.geojson.path' $(MANIFEST) 2>/dev/null)
CSV_NETWORK_JSON := $(shell jq -r '.network_evidence_layers[]?.files.json.path' $(MANIFEST) 2>/dev/null)
CSV_INFRASTRUCTURE_JSON := $(shell jq -r '(.infrastructure_evidence_layers[]?, .infrastructure_evidence_views[]?) | .files.json.path' $(MANIFEST) 2>/dev/null)
CSV_VENDOR_JSON := $(shell jq -r '.vendor_registry? | .files.json.path // empty' $(MANIFEST) 2>/dev/null)
CSV_COMPARISON_JSON := $(shell jq -r '.observation_comparison_views[]? | .files.json.path' $(MANIFEST) 2>/dev/null)
CSV_APPLICATION_JSON := $(shell jq -r '.application_endpoint_layers[]? | .files.json.path' $(MANIFEST) 2>/dev/null)
CSV_TARGETS := $(CSV_GEOJSON:.geojson=.csv) $(CSV_NETWORK_JSON:.json=.csv) $(CSV_INFRASTRUCTURE_JSON:.json=.csv) $(CSV_VENDOR_JSON:.json=.csv) $(CSV_COMPARISON_JSON:.json=.csv) $(CSV_APPLICATION_JSON:.json=.csv)

.PHONY: all check check-csv-tools clean-csv csv help refresh-network refresh-network-offline

all: csv

csv: check-csv-tools $(CSV_TARGETS)

check-csv-tools:
	@command -v jq >/dev/null
	@test -f "$(MANIFEST)"

data/%.csv: data/%.geojson schema/location.schema.json scripts/geojson-to-csv.jq
	@jq -r --slurpfile schema schema/location.schema.json \
		-f scripts/geojson-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/network/%.csv: data/network/%.json schema/network-evidence.schema.json scripts/network-json-to-csv.jq
	@jq -r --slurpfile schema schema/network-evidence.schema.json \
		-f scripts/network-json-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/infrastructure/%.csv: data/infrastructure/%.json schema/infrastructure-evidence.schema.json scripts/infrastructure-json-to-csv.jq
	@jq -r --slurpfile schema schema/infrastructure-evidence.schema.json \
		-f scripts/infrastructure-json-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/vendors/%.csv: data/vendors/%.json schema/infrastructure-evidence.schema.json scripts/infrastructure-json-to-csv.jq
	@jq -r --slurpfile schema schema/infrastructure-evidence.schema.json \
		-f scripts/infrastructure-json-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/observations/cdn-asn-comparison.%.csv: data/observations/cdn-asn-comparison.%.json schema/cdn-comparison.schema.json scripts/cdn-comparison-to-csv.jq
	@jq -r -f scripts/cdn-comparison-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/india/cdn-asn-comparison.%.csv: data/india/cdn-asn-comparison.%.json schema/cdn-comparison.schema.json scripts/cdn-comparison-to-csv.jq
	@jq -r -f scripts/cdn-comparison-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/russia/cdn-asn-comparison.%.csv: data/russia/cdn-asn-comparison.%.json schema/cdn-comparison.schema.json scripts/cdn-comparison-to-csv.jq
	@jq -r -f scripts/cdn-comparison-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

data/applications/%.csv: data/applications/%.json schema/application-endpoint.schema.json scripts/application-endpoint-to-csv.jq
	@jq -r --slurpfile schema schema/application-endpoint.schema.json \
		-f scripts/application-endpoint-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

refresh-network:
	python3 -B scripts/update_network.py --retrieved-at $(RETRIEVED_AT) --fetch
	python3 -B scripts/update_peeringdb.py --retrieved-at $(RETRIEVED_AT) --fetch
	python3 -B scripts/build_manifest.py --retrieved-at $(RETRIEVED_AT)

refresh-network-offline:
	python3 -B scripts/update_network.py --retrieved-at $(RETRIEVED_AT)
	python3 -B scripts/update_peeringdb.py --retrieved-at $(RETRIEVED_AT)
	python3 -B scripts/build_manifest.py --retrieved-at $(RETRIEVED_AT)

clean-csv:
	$(RM) $(CSV_TARGETS)

check:
	python3 -B tests/validate_recovery.py
	python3 -B tests/validate_google.py
	python3 -B tests/validate_authoritative.py
	python3 -B tests/validate_hyperscalers.py
	python3 -B tests/validate_observation_cities.py
	python3 -B tests/validate_cdn_comparisons.py
	python3 -B tests/validate_network.py
	python3 -B tests/validate_russia.py
	python3 -B tests/validate_russia_enrichment.py
	python3 -B tests/validate_infrastructure.py
	python3 -B tests/validate_china_review.py
	python3 -B tests/validate_china_enrichment.py
	python3 -B tests/validate_cartography_sources.py
	git diff --check

help:
	@echo "make csv                            Generate all normalized CSV views"
	@echo "make data/google/cloud-regions-and-zones.20260805.csv"
	@echo "make data/network/provider-prefixes.20260805.csv"
	@echo "                                    Generate one CSV from canonical JSON/GeoJSON"
	@echo "make clean-csv                      Remove normalized CSV views"
	@echo "make refresh-network                Fetch prefix feeds/RIPEstat and rebuild the manifest"
	@echo "make refresh-network-offline        Rebuild network layers from retained raw snapshots"
	@echo "make check                          Run the validation suite"
