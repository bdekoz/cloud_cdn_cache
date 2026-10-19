#!/usr/bin/env python3
"""Check restored locations, evidence conservation, schema and frozen layers."""
import csv
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from location_common import validate_records
from update_cartography_sources import AKAMAI, RAW, endpoint_evidence


def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def records(layer):
    path = ROOT / f'data/{layer}.20261019.geojson'
    features = read(path)['features']
    result = []
    for f in features:
        p = dict(f['properties'])
        p['longitude'], p['latitude'] = f['geometry']['coordinates']
        result.append(p)
    validate_records(result)
    output = subprocess.check_output(['jq', '-r', '--slurpfile', 'schema',
        str(ROOT/'schema/location.schema.json'), '-f', str(ROOT/'scripts/geojson-to-csv.jq'), str(path)], text=True)
    rows = list(csv.DictReader(io.StringIO(output)))
    assert len(rows) == len(result)
    assert [r['record_id'] for r in rows] == [r['record_id'] for r in result]
    assert [json.loads(r['properties']) for r in rows] == [r['properties'] for r in result]
    assert [(float(r['longitude']), float(r['latitude'])) for r in rows] == [(r['longitude'],r['latitude']) for r in result]
    return result


def main():
    old = ROOT/'data/manifest.20261011.json'
    assert digest(old) == 'f408815674b2e195bc98a9b911b70154ec1b33847b3501147da102fcae964730'
    old_manifest = read(old)
    current = read(ROOT/'data/manifest.20261019.json')
    baseline = read(ROOT/'data/raw/repository/manifest-before-russia.20261019.json')
    assert baseline['record_count'] == 27930 and baseline['layer_count'] == 33
    assert current['layers'][:33] == baseline['layers']
    assert current['record_count'] == sum(layer['record_count'] for layer in current['layers'])
    assert current['layer_count'] == len(current['layers'])
    assert current['layers'][:len(old_manifest['layers'])] == old_manifest['layers']
    for layer in current['layers']:
        for file in layer['files'].values():
            assert digest(ROOT/file['path']) == file['sha256']

    original = read(ROOT/'data/akamai_13-07-2023.geojson')['features']
    assert digest(AKAMAI) == digest(ROOT/'data/akamai_13-07-2023.geojson')
    akamai = records('akamai/legacy-locations')
    assert len(akamai) == len(original) == 416
    assert Counter(r['lifecycle_status'] for r in akamai) == {'operational':355, 'planned':61}
    for row, feature in zip(akamai, original):
        assert row['properties']['legacy_properties'] == feature['properties']
        assert [row['longitude'],row['latitude']] == feature['geometry']['coordinates']
        assert row['source_published_at'] == '2023-07-12'
        assert row['coordinate_method'] == 'legacy' and row['location_precision'] == 'city'
        assert row['country_code'] and not row['properties']['revalidated_current_deployment']

    apple = records('apple/dns-cities')
    audit = read(ROOT/'data/apple/dns-endpoint-audit.20261019.json')
    assert len(apple) == 14
    assert Counter(r['country_code'] for r in apple) == {'US':13,'CA':1}
    observed = endpoint_evidence()
    located = [e['ip'] for r in apple for e in r['properties']['endpoint_evidence']]
    held = {e['ip'] for e in audit['held_endpoints']}
    assert len(located) == len(set(located)) == 104
    assert held == {'64.78.200.1','64.78.201.1','2620:171:80c::1','2620:171:80d::1'}
    assert set(located).isdisjoint(held)
    assert set(located) | held == set(observed)
    assert audit['observed_endpoint_count'] == 108
    assert len({(r['country_code'],r['subdivision'],r['city']) for r in apple}) == 14
    for row in apple:
        assert row['service_scope'] == ['dns_over_https']
        assert row['coordinate_method'] == 'geocoded' and row['location_precision'] == 'city'
        assert row['source_scope'] == 'observed' and row['lifecycle_status'] == 'unknown'
        assert row['properties']['endpoint_count'] == len(row['properties']['endpoint_evidence'])
        assert not row['properties']['physical_site_confirmed']
        assert row['properties']['grain'] == 'distinct_observed_dns_city'
    for sidecar in RAW.glob('*.provenance.json'):
        p = read(sidecar)
        assert digest(ROOT/p['raw_source_ref']) == p['sha256']
    print('Cartography sources passed: 416 retained Akamai rows; 14 Apple DNS cities; 104 located and 4 held addresses; all 31 prior layers unchanged.')


if __name__ == '__main__': main()
