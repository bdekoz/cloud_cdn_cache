["footprint_id", "provider", "vendor_id", "service", "locality", "country_code",
 "location_precision", "coordinate_method", "coordinate_crs", "longitude", "latitude",
 "record_unit", "physical_site_confirmed", "lifecycle_status", "source_record_ids",
 "source_claim_ids", "source_locality_labels", "evidence", "gazetteer",
 "excluded_from_canonical_totals"] as $columns
| ($columns | @csv),
  (.features[]
   | (.properties + {longitude: .geometry.coordinates[0], latitude: .geometry.coordinates[1]}) as $row
   | [$columns[] | $row[.] | if type == "array" or type == "object" then tojson else . end]
   | @csv)
