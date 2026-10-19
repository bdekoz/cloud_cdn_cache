# Preserve nested DNS, address and provenance evidence as JSON cells.
($schema[0]["$defs"].record.required) as $fields
| $fields,
  (.records[] | . as $row | [$fields[] | $row[.] |
    if type == "array" or type == "object" then tojson
    elif . == null then "" else . end])
| @csv
