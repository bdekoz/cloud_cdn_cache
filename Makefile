RETRIEVED_AT ?= 2026-08-05
RETRIEVED_TAG ?= $(subst -,,$(RETRIEVED_AT))
MANIFEST := data/manifest.$(RETRIEVED_TAG).json
CSV_GEOJSON := $(shell jq -r '(.layers + .views)[] | .files.geojson.path' $(MANIFEST) 2>/dev/null)
CSV_NETWORK_JSON := $(shell jq -r '.network_evidence_layers[]?.files.json.path' $(MANIFEST) 2>/dev/null)
CSV_TARGETS := $(CSV_GEOJSON:.geojson=.csv) $(CSV_NETWORK_JSON:.json=.csv)

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
	python3 -B tests/validate_network.py
	python3 -B tests/validate_russia.py
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
