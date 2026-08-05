RETRIEVED_TAG ?= 20260804
MANIFEST := data/manifest.$(RETRIEVED_TAG).json
CSV_GEOJSON := $(shell jq -r '(.layers + .views)[] | .files.geojson.path' $(MANIFEST) 2>/dev/null)
CSV_TARGETS := $(CSV_GEOJSON:.geojson=.csv)

.PHONY: all check check-csv-tools clean-csv csv help

all: csv

csv: check-csv-tools $(CSV_TARGETS)

check-csv-tools:
	@command -v jq >/dev/null
	@test -f "$(MANIFEST)"

data/%.csv: data/%.geojson schema/location.schema.json scripts/geojson-to-csv.jq
	@jq -r --slurpfile schema schema/location.schema.json \
		-f scripts/geojson-to-csv.jq "$<" > "$@.tmp"
	@mv "$@.tmp" "$@"

clean-csv:
	$(RM) $(CSV_TARGETS)

check:
	python3 -B tests/validate_recovery.py
	python3 -B tests/validate_google.py
	python3 -B tests/validate_authoritative.py
	git diff --check

help:
	@echo "make csv                            Generate all normalized CSV views"
	@echo "make data/google/edge.20260804.csv  Generate one CSV from GeoJSON"
	@echo "make clean-csv                      Remove normalized CSV views"
	@echo "make check                          Run the validation suite"
