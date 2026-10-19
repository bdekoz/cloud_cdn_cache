# A missing reference is not a negative measurement. Keep source IDs inspectable.
.provider_columns as $columns
| (["asn", "as_names", "apnic_registration_country", "apnic_delegated_at"]
   + [$columns[].dataset] + ["source_record_ids"]),
  (.records[]
   | . as $row
   | [.asn, (.as_names | tojson), (.apnic_registration.country_code // ""),
      (.apnic_registration.delegated_at // "")]
     + [$columns[] | if $row.provider_record_ids[.key] == null
                     then "not_observed_in_this_snapshot" else "observed" end]
     + [(.provider_record_ids | tojson)])
| @csv
