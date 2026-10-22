#!/usr/bin/env python3
"""Validate Microsoft scope, retained provenance, temporal boundaries and offline replay."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from location_common import load_validator,sha256
from update_microsoft import sources,DATE,TAG
from update_infrastructure import validate_collection

def read(path):return json.loads(path.read_text())

def main():
 old=read(ROOT/'data/manifest.20261019.json');new=read(ROOT/f'data/manifest.{TAG}.json')
 assert old['record_count']==28024
 assert new['record_count']==sum(x['record_count'] for x in new['layers'])
 old_layers={x['layer']:x for x in old['layers']};new_layers={x['layer']:x for x in new['layers']}
 changed={'microsoft/front-door','microsoft/front-door-codes','microsoft/cloud-regions','microsoft/china-cloud-regions'}
 assert set(new_layers)-set(old_layers)=={'microsoft/global-network-pops','microsoft/announced-cloud-regions','microsoft/government-cloud-regions'}
 for key in old_layers.keys()-changed:assert old_layers[key]==new_layers[key],key
 for key in ['views','network_evidence_layers','application_endpoint_layers']:
  assert old[key]==new[key],key
 assert new['geographic_footprint_views'][:-1]==old['geographic_footprint_views']
 assert new['infrastructure_evidence_layers'][:-1]==old['infrastructure_evidence_layers']
 for section in ['layers','views','network_evidence_layers','infrastructure_evidence_layers','geographic_footprint_views']:
  for layer in new[section]:
   for f in layer['files'].values():assert sha256(ROOT/f['path'])==f['sha256'],f['path']
 records=[]
 for name,entry in new_layers.items():
  if not name.startswith('microsoft/'):continue
  features=read(ROOT/entry['files']['geojson']['path'])['features']
  for f in features:
   row=f['properties'];row=dict(row,latitude=f['geometry']['coordinates'][1] if f['geometry'] else None,
    longitude=f['geometry']['coordinates'][0] if f['geometry'] else None)
   load_validator(ROOT/'schema/location.schema.json').validate(row)
   assert sha256(ROOT/row['raw_source_ref'])==row['source_sha256']
   if row['entity_type']=='cloud_region':assert f['geometry'] is None
   records.append(row)
 assert len({r['record_id'] for r in records})==len(records)
 assert not any(r['entity_type']=='availability_zone' for r in records)
 cloud={r['site_code']:r for r in records if r['source_collection']=='azure_public_cloud_regions'}
 assert len(cloud)==58 and 'indiasouthcentral' in cloud
 assert cloud['taiwannorth']['lifecycle_status']=='planned'
 assert cloud['eastus2']['properties']['availability_zone_support_coming_soon']
 assert cloud['eastus2']['properties']['availability_zone_count_declared']==4
 assert cloud['eastus2']['properties']['availability_zone_support'] is None
 assert cloud['northcentralus']['properties']['availability_zone_support_status']=='coming_soon'
 assert cloud['australiaeast']['properties']['availability_zone_support']
 before=read(ROOT/'data/microsoft/cloud-regions.20260805.geojson')['features']
 for f in before:assert next(r for r in records if r['record_id']==f['properties']['record_id'])['first_seen']==f['properties']['first_seen']
 pops=[r for r in records if r['service']=='microsoft_global_network']
 assert len(pops)==206 and Counter(r['properties']['network_pop_type'] for r in pops)=={'unspecified':201,'ai':5}
 assert all(r['location_precision'] in {'city','region'} and not r['properties']['physical_site_confirmed'] for r in pops)
 assert sum(r['location_precision']=='region' for r in pops)==6
 assert all(r['city'] is None for r in pops if r['location_precision']=='region')
 hk=[r for r in pops if r['site_code'] in {'HKG33','HKG30','HKB'}]
 assert len(hk)==3 and all(r['country_code']=='HK' and r['jurisdiction_scope']=='hong_kong' and r['properties']['source_geography_id']=='china' for r in hk)
 infra=read(ROOT/f'data/infrastructure/microsoft-evidence.{TAG}.json');validate_collection(infra)
 assertions={r['record_id']:r for r in infra['records']}
 assert len(assertions)==254 and all(r['geometry'] is None for r in assertions.values())
 assert len([r for r in assertions.values() if r['category']=='m365_data_residency_locality'])==56
 assert any(r['name']=='Helsinki' and r['category']=='m365_data_residency_locality' for r in assertions.values())
 loughton=next(r for r in assertions.values() if r['name']=='Loughton')
 assert loughton['lifecycle_status']=='unknown' and loughton['properties']['map_eligible'] is False
 footprint=read(ROOT/f'data/microsoft/provider-localities.{TAG}.geojson')
 load_validator(ROOT/'schema/geographic-footprint.schema.json').validate(footprint)
 assert len(footprint['features'])==96
 members=[]
 for f in footprint['features']:
  p=f['properties'];assert p['source_record_ids']==[] and not p['physical_site_confirmed']
  assert sha256(ROOT/p['gazetteer']['evidence']['raw_source_ref'])==p['gazetteer']['evidence']['source_sha256']
  for cid in p['source_claim_ids']:
   assert cid in assertions and cid!=loughton['record_id'];members.append(cid)
  if p['locality']=='Quincy':assert p['gazetteer']['admin1']=='WA'
  if p['locality'] in ['New Albany','Heath','Hebron']:assert p['gazetteer']['admin1']=='OH'
 assert len(members)==len(set(members))
 assert len(sources())==70
 redacted=[s for s in sources().values() if s.get('content_redactions')]
 assert len(redacted)==43
 import re
 for s in sources().values():
  if s['path'].endswith('.html'):
   values=re.findall(rb'"mapbox_key"\s*:\s*"([^"]+)"',(ROOT/s['path']).read_bytes())
   assert all(v==b'REDACTED_MAPBOX_TOKEN' for v in values),s['source_id']
 for s in redacted:
  assert s['content_redactions'][0]['original_response_sha256']!=s['sha256']
 for s in sources().values():assert read(ROOT/(s['path']+'.provenance.json'))==s
 bib=read(ROOT/'data/references/bibliography.20261021.json');earlier=read(ROOT/'data/references/bibliography.20261019.json')
 assert bib['references'][:len(earlier['references'])]==earlier['references']
 assert bib['reference_count']==365==len({r['reference_id'] for r in bib['references']})
 with tempfile.TemporaryDirectory(prefix='microsoft-replay-') as temp:
  subprocess.run([sys.executable,'-B','scripts/update_microsoft.py','--output-root',temp],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
  for path in Path(temp).rglob('*'):
   if path.is_file():assert path.read_bytes()==(ROOT/path.relative_to(temp)).read_bytes(),path
  baseline=Path(temp)/'manifest.20261019.json'
  subprocess.run([sys.executable,'-B','scripts/build_manifest.py','--retrieved-at','2026-10-19','--output',str(baseline)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
  assert baseline.read_bytes()==(ROOT/'data/manifest.20261019.json').read_bytes()
 print('Microsoft checks passed: scope and schema, source hashes, old snapshots, region lifecycle/AZ semantics, country/state joins, conflict exclusion, reference counts and byte-identical offline replay.')

if __name__=='__main__':main()
