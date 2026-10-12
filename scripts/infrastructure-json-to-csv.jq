def csv_value:
  if . == null then ""
  elif type == "array" or type == "object" then tojson
  else .
  end;

$schema[0].properties.records.items.required as $fields
| ($fields | @csv),
  (.records[] | . as $row | [$fields[] as $field | $row[$field] | csv_value] | @csv)
