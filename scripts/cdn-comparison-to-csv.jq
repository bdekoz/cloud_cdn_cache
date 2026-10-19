# A missing reference is not a negative measurement. Keep source IDs inspectable.
.provider_columns as $columns
| .schema_version as $version
| (["asn", "as_names"] + (if $version == "1.0.0"
     then ["apnic_registration_country", "apnic_delegated_at"]
     else ["rir_registration_country", "rir_delegated_at", "rir_registry"] end)
   + [$columns[].dataset] + ["source_record_ids"]),
  (.records[]
   | . as $row
   | [.asn, (.as_names | tojson)] + (if $version == "1.0.0"
      then [(.apnic_registration.country_code // ""), (.apnic_registration.delegated_at // "")]
      else [(.rir_registration.country_code // ""), (.rir_registration.delegated_at // ""),
            (.rir_registration.registry // "")] end)
     + [$columns[] | if $row.provider_record_ids[.key] == null
                     then "not_observed_in_this_snapshot" else "observed" end]
     + [(.provider_record_ids | tojson)])
| @csv
