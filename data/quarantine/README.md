# Quarantined layers

Files here are retained byte-for-byte for auditability but are excluded from current provider-declared views.

- `baidu_cloud_data_centers_2.geojson` claims 35 global regions without source metadata. Baidu's official service matrix captured on 2026-08-04 exposes eight service-region columns, all in mainland China or Hong Kong. This conflict cannot be resolved by treating the old file as merely stale.
- `alibaba_cloud_data_centers_3.geojson` contains uncited estimates for node counts, network overlays, power capacity, and facility details. Those estimates are not present in the official region-and-zone directory and are not mixed into the authoritative rebuild.

`audit.20260804.json` records exact hashes, counts, the Baidu source labels, and the exclusion decision. Regenerate it with:

```sh
python3 -B scripts/audit_quarantine.py
```

Quarantine is reversible: neither source file was edited or deleted.
