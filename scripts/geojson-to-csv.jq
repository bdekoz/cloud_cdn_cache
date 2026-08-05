def csv_escape:
  if . == null then
    ""
  elif type == "number" or type == "boolean" then
    tostring
  else
    tostring as $value
    | if (($value | contains(","))
          or ($value | contains("\""))
          or ($value | contains("\n"))
          or ($value | contains("\r"))) then
        "\"" + ($value | gsub("\""; "\"\"")) + "\""
      else
        $value
      end
  end;

def sort_keys_recursive:
  if type == "object" then
    to_entries
    | sort_by(.key)
    | map(.value |= sort_keys_recursive)
    | from_entries
  elif type == "array" then
    map(sort_keys_recursive)
  else
    .
  end;

def csv_value:
  if type == "array" or type == "object" then
    sort_keys_recursive | tojson
  else
    .
  end
  | csv_escape;

$schema[0].required as $fields
| ($fields | map(csv_escape) | join(",")),
  (.features[]
   | . as $feature
   | ($feature.properties
      + if $feature.geometry == null then
          {latitude: null, longitude: null}
        else
          {
            latitude: $feature.geometry.coordinates[1],
            longitude: $feature.geometry.coordinates[0]
          }
        end) as $record
   | [$fields[] as $field | $record[$field] | csv_value]
   | join(","))
