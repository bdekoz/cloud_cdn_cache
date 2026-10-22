#!/usr/bin/env python3
"""Rebuild the reviewed 2026-10-21 Microsoft enrichment from retained sources."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import zipfile
from functools import lru_cache
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator
from location_common import (REPO_ROOT, canonical_record, country_identity, load_validator, apply_history, load_previous_records,
    repo_ref, sha256, slug, write_json, write_layer)
import update_authoritative as authoritative
from update_hyperscalers import azure_country
from update_infrastructure import validate_collection

DATE, TAG = '2026-10-21', '20261021'
RAW = REPO_ROOT / 'data/raw/microsoft-enrichment'
CATALOG = RAW / f'catalog.{TAG}.json'

def read(path): return json.loads(path.read_text())
@lru_cache
def sources():
    entries = read(CATALOG)['sources']
    for s in entries:
        if s.get('result') == 'retrieved':
            assert sha256(REPO_ROOT/s['path']) == s['sha256'], s['source_id']
    assert len({s['source_id'] for s in entries}) == len(entries)
    return {s['source_id']:s for s in entries}

def evidence(key):
    s = sources()[key]
    assert s['result'] == 'retrieved', key
    return dict(source_url=s['source_url'], raw_source_ref=s['path'], source_sha256=s['sha256'],
        source_published_at=s.get('source_published_at'), retrieved_at=s['retrieved_at'])

def soup(key): return BeautifulSoup((REPO_ROOT/evidence(key)['raw_source_ref']).read_bytes(),'html.parser')
def raw_json(key): return read(REPO_ROOT/evidence(key)['raw_source_ref'])
def clean(value): return ' '.join(value.split())
def norm(value): return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower())
def rows(table): return [[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])] for tr in table.find_all('tr')]

def record(key, identifier, name, provider, service, entity_type, country=None, country_code=None,
           lifecycle='unknown', city=None, latitude=None, longitude=None, properties=None, **kw):
    ev = evidence(key)
    return canonical_record(schema_version='1.2.0',record_id=identifier,aliases=[],provider=provider,
        service=service,entity_type=entity_type,parent_record_id=None,access_status=kw.pop('access_status','not_applicable'),
        service_scope=kw.pop('service_scope',[]),source_collection=kw.pop('collection','microsoft_public_directories'),
        source_record_id=kw.pop('source_record_id',None),name=name,site_code=kw.pop('site_code',None),
        lifecycle_status=lifecycle,source_scope='provider_declared',city=city,metro=city,
        subdivision=kw.pop('subdivision',None),country=country,country_code=country_code,latitude=latitude,longitude=longitude,
        location_precision=kw.pop('precision','city' if city else 'region'),
        coordinate_method='provider' if latitude is not None else 'unknown',**ev,
        first_seen=DATE,last_seen=DATE,confidence='high',properties={
            'source_updated_at':sources()[key].get('source_updated_at'), **(properties or {})},**kw)

def save_layer(root, name, data, key, extra=None):
    s = sources()[key]
    apply_history(data,load_previous_records(REPO_ROOT/'data/microsoft',name,TAG))
    report = write_layer(records=data,output_dir=root/'data/microsoft',layer_name=name,retrieved_at=DATE,
        source_url=s['source_url'],raw_path=REPO_ROOT/s['path'],parser_name='update_microsoft.py:'+name,
        schema_version='1.2.0',extra_report=extra)
    # Reports use canonical repository-relative paths even in an offline replay directory.
    report['derived_files']={'csv':{'path':f'data/microsoft/{name}.{TAG}.csv',
        'source':f'data/microsoft/{name}.{TAG}.geojson','generator':f'make data/microsoft/{name}.{TAG}.csv'}}
    report['generated_files']=[f'data/microsoft/{name}.{TAG}.geojson']
    write_json(root/f'data/microsoft/{name}.{TAG}.report.json',report)
    return report

def frontdoor(root):
    for key,source_id in [('azure','frontdoor-locations'),('azure-codes','frontdoor-codes')]:
        s=sources()[source_id]
        authoritative.SOURCES[key]=(s['source_url'],s['path'],'text/html',s.get('source_published_at'))
    result=[]
    for name,func,key in [('front-door',authoritative.parse_azure,'frontdoor-locations'),
                          ('front-door-codes',authoritative.parse_azure_codes,'frontdoor-codes')]:
        data, report=func(DATE)
        for row in data:
            row['properties']['record_unit']='declared_metro_row' if name=='front-door' else 'declared_abbreviation_row'
            row['properties']['not_additive_with_other_front_door_directory']=True
            row['properties']['source_updated_at']=sources()[key].get('source_updated_at')
        if name=='front-door':
            report['page_claims_source_note']='Headline claims and itemized sums are retained independently; they need not reconcile.'
        save_layer(root,name,data,key,report); result.extend(data)
    return result

GEO_COUNTRIES={
 'unitedstates':'US','unitedkingdom':'GB','unitedarabemirates':'AE','korea':'KR','china':'CN',
 'australia':'AU','austria':'AT','argentina':'AR','brazil':'BR','belgium':'BE','canada':'CA',
 'chile':'CL','denmark':'DK','finland':'FI','france':'FR','germany':'DE','greece':'GR','india':'IN',
 'indonesia':'ID','israel':'IL','italy':'IT','japan':'JP','malaysia':'MY','mexico':'MX','newzealand':'NZ',
 'norway':'NO','poland':'PL','qatar':'QA','saudiarabia':'SA','spain':'ES','sweden':'SE','switzerland':'CH',
 'taiwan':'TW','thailand':'TH',
}
POP_COUNTRIES={'Pasig City':'PH','Kayl':'LU','Prior Velho':'PT','Midrand':'ZA','Dublin':'IE','Zagreb':'HR',
 'Sofia':'BG','Singapore':'SG','Rabat':'MA','Prague':'CZ','Nairobi':'KE','Lagos':'NG','Isando':'ZA',
 'Istanbul':'TR','Ho Chi Minh City':'VN','Cape Town':'ZA','Cairo':'EG','Budapest':'HU','Bucharest':'RO',
 'Bogota':'CO','Bangkok':'TH','Amsterdam-Zuidoost':'NL','Amsterdam':'NL','Haarlemmermeer':'NL',
 'Hong Kong':'HK','Chai Wan':'HK'}
BROAD_POP_LABELS={'Bay','Ontario','New Jersey','Maharashtra','Municipio El Marqués'}

def country_from_code(cc):
    from babel import Locale
    return country_identity(str(Locale('en').territories[cc]))[0]

def network_pops(root):
    data=[]
    for r in raw_json('globe-pops'):
        city=clean(r.get('city') or '')
        cc=POP_COUNTRIES.get(city) or GEO_COUNTRIES.get(r.get('geographyId'))
        broad=city in BROAD_POP_LABELS
        assert cc, ('unreviewed POP country',r['id'],city,r.get('geographyId'))
        data.append(record('globe-pops','microsoft:edge_pop:global-network-'+slug(r['id']),r['id']+' — '+city,
            'Microsoft','microsoft_global_network','edge_pop',country=country_from_code(cc),country_code=cc,
            city=None if broad else city,subdivision=city if broad else None,precision='region' if broad else 'city',
            latitude=float(r['latitude']),longitude=float(r['longitude']),source_record_id=r['id'],site_code=r['id'],
            collection='microsoft_globe_network_pops',properties={
                'record_unit':'provider_published_network_pop_identifier','network_pop_type':r.get('popType') or 'unspecified',
                'source_geography_id':r.get('geographyId'),'source_city_label':r.get('city'),
                'coordinate_scope':'provider_map_point_not_verified_facility_location','physical_site_confirmed':False,
                'ownership':'not_disclosed','not_additive_with_front_door':True,
                'country_assignment_basis':'reviewed_locality_jurisdiction' if city in POP_COUNTRIES else 'source_geography',
                'source_city_field_is_broad_label':broad,
                'source_post_modified_at':r.get('post_modified'),'listing_does_not_confirm_current_operation':True}))
    assert len(data)==len({r['record_id'] for r in data})
    save_layer(root,'global-network-pops',data,'globe-pops',{'record_unit':'provider_published_network_pop_identifier',
        'pop_types':dict(Counter(r['properties']['network_pop_type'] for r in data)),
        'coordinate_note':'Provider map points retain city or broad regional precision; neither street addresses nor Microsoft property ownership are established.',
        'overlap_note':'The network map, Front Door metros, and abbreviation directory overlap and are not additive physical sites.'})
    return data

def cloud_regions(root):
    tables=soup('regions-list').find_all('table')
    table=next(t for t in tables if rows(t)[0]==['Region','Availability zones','Paired region','Physical location','Geography','Programmatic name'])
    globe={norm(r['displayName']):r for r in raw_json('globe-regions')}
    data=[]
    for tr in table.find_all('tr')[1:]:
        cells=tr.find_all('td'); assert len(cells)==6
        name,az,paired,physical,geography,code=[clean(c.get_text(' ',strip=True)) for c in cells]
        country,cc=azure_country(code,geography)
        icons=' '.join(i.get('src','') for i in cells[0].find_all('img'))
        az_icons=' '.join(i.get('src','') for i in cells[1].find_all('img'))
        props={'physical_location':physical,'geography':geography,'paired_region':None if paired=='N/A' else paired,
            'availability_zone_count_declared':int(az) if az.isdecimal() else None,
            'availability_zone_support':None if 'coming-soon' in az_icons else az.isdecimal(),
            'availability_zone_support_status':'coming_soon' if 'coming-soon' in az_icons else 'available' if az.isdecimal() else 'not_listed',
            'availability_zone_support_coming_soon':'coming-soon' in az_icons,
            'availability_zone_source_text':az,'synthetic_availability_zones_generated':False}
        if norm(name) in globe:
            g=globe[norm(name)]
            props['globe_directory']={'source':evidence('globe-regions'),'source_id':g['id'],
                'location':g.get('location'),'is_open':g.get('isOpen'),'year_open':g.get('yearOpen'),
                'map_reference_coordinates':[float(g['longitude']),float(g['latitude'])],
                'not_facility_coordinates':True}
        data.append(record('regions-list','azure:cloud_region:'+code,name,'Microsoft Azure','azure_cloud','cloud_region',
            country=country,country_code=cc,lifecycle='planned' if 'coming-soon' in icons else 'operational',
            access_status='restricted' if 'restricted' in icons else 'public',service_scope=['public_cloud'],
            source_record_id=code,site_code=code,collection='azure_public_cloud_regions',properties=props))
    assert len({r['record_id'] for r in data})==len(data)
    save_layer(root,'cloud-regions',data,'regions-list',{'public_cloud_region_count':len(data),
        'availability_zone_records_generated':0,'table_selection':'column-header match; first full table only',
        'restricted_region_count':sum(r['access_status']=='restricted' for r in data)})
    published={norm(r['name']) for r in data}
    announced=[]
    for g in globe.values():
        if norm(g['displayName']) in published or g.get('geographyId')=='china': continue
        assert g.get('isOpen') is False, ('unmatched open region',g['id'])
        cc=GEO_COUNTRIES[g['geographyId']] if g['geographyId']!='asiapacific' else 'MY'
        announced.append(record('globe-regions','azure:cloud_region:announced-'+slug(g['id']),g['displayName'],
            'Microsoft Azure','azure_cloud','cloud_region',country=country_from_code(cc),country_code=cc,lifecycle='planned',
            access_status='unknown',service_scope=['announced_region'],source_record_id=g['id'],
            collection='microsoft_globe_announced_regions',properties={'physical_location':g.get('location'),
                'globe_is_open':False,'programmatic_name_not_declared':True,'announcement_url':g.get('announcementLink'),
                'map_reference_coordinates':[float(g['longitude']),float(g['latitude'])],
                'not_facility_coordinates':True,'synthetic_availability_zones_generated':False}))
    save_layer(root,'announced-cloud-regions',announced,'globe-regions',{'record_unit':'announced_region',
        'not_additive_with_public_directory':True,'unit_note':'Only unmatched named planned globe regions; internal globe IDs are not asserted Azure API names.'})
    return data+announced

def sovereign_regions(root):
    data=[]
    table=soup('government-regions').find('table')
    for tr in table.find_all('tr')[1:]:
        cells=tr.find_all('td'); vals=[clean(c.get_text(' ',strip=True)) for c in cells]
        assert len(vals)==5
        name,az,paired,geo,code=vals
        data.append(record('government-regions','azuregov:cloud_region:'+code,name,'Microsoft Azure','azure_government',
            'cloud_region',country='United States',country_code='US',lifecycle='operational',access_status='restricted',
            source_record_id=code,site_code=code,service_scope=['government_cloud'],collection='azure_government_regions',
            properties={'partition':'AzureUSGovernment','paired_region':paired,'availability_zone_support':bool(cells[1].find('img')),
                'synthetic_availability_zones_generated':False}))
    dod=soup('government-dod').get_text(' ',strip=True)
    for name in ['US DoD Central','US DoD East']:
        assert name in dod
        data.append(record('government-dod','azuregov:cloud_region:'+slug(name),name,'Microsoft Azure','azure_government',
            'cloud_region',country='United States',country_code='US',lifecycle='operational',access_status='restricted',
            service_scope=['government_cloud','dod_only'],collection='azure_government_dod_regions',
            properties={'partition':'AzureUSGovernment','programmatic_name_not_declared_in_selected_source':True,
                'physical_location_not_disclosed':True,'synthetic_availability_zones_generated':False}))
    save_layer(root,'government-cloud-regions',data,'government-regions',{'government_regions':3,'dod_regions':2,
        'availability_zone_records_generated':0})
    china=[]
    for tr in soup('china-regions').find('table').find_all('tr')[1:]:
        cells=tr.find_all('td'); vals=[clean(c.get_text(' ',strip=True)) for c in cells]; assert len(vals)==6
        name,az,paired,physical,geo,code=vals
        china.append(record('china-regions','azurechina:cloud_region:'+code,name.rstrip('*'),'Microsoft Azure operated by 21Vianet',
            'azure_china','cloud_region',country='China',country_code='CN',lifecycle='operational',access_status='public',
            source_record_id=code,site_code=code,service_scope=['azure_china'],collection='azurechina_azure_china_directory',
            properties={'partition':'AzureChinaCloud','operator':'Shanghai Blue Cloud Technology Co., Ltd. (21Vianet)',
                'operator_evidence':evidence('china-operator'),'brand':'Microsoft Azure',
                'source_physical_location':physical,'geography':geo,'paired_region_id':paired,
                'availability_zone_support':bool(cells[1].find('img')),'synthetic_availability_zones_generated':False,
                'microsoft_ownership_not_asserted':True}))
    save_layer(root,'china-cloud-regions',china,'china-regions',{'operator_evidence':evidence('china-operator')})
    return data+china

# Each item is a disclosed locality/phase, never one inferred physical building.
# Region-only claims remain unplotted; community-benefit towns are not admitted.
COMMUNITIES={
 'australia':('AU',[('ACT','region','in_development'),('New South Wales','region','in_development'),('Victoria','region','in_development')]),
 'austria':('AT',[('Greater Vienna','city','in_development')]),
 'brazil-greater-campinas':('BR',[('São Paulo','region','operational'),('Hortolândia','city','in_development'),('Sumaré','city','in_development')]),
 'california':('US',[('Santa Clara County','region','in_development')]),
 'canada':('CA',[('Greater Québec Region','region','in_development'),('Ontario','region','in_development')]),
 'cheyenne':('US',[('Cheyenne','city','operational')]),
 'danmark':('DK',[('capital area','region','in_development'),('Zealand','region','in_development')]),
 'dublin':('IE',[('Dublin','city','operational'),('County Kildare','region','planned')]),
 'germany':('DE',[('Nordrhein-Westfalen','region','planned')]),
 'greater-atlanta':('US',[('Douglasville','city','in_development'),('Palmetto','city','in_development'),('East Point','city','in_development')]),
 'greater-des-moines':('US',[('West Des Moines','city','operational')]),
 'greater-phoenix':('US',[('El Mirage','city','operational'),('Goodyear','city','operational')]),
 'greater-san-antonio':('US',[('Bexar','region','operational'),('Medina','region','operational')]),
 'greece':('GR',[('Attica','region','in_development')]),
 'illinois':('US',[('Chicagoland','region','operational'),('Illinois','region','planned')]),
 'india-hyderabad-and-pune':('IN',[('Hyderabad','city','in_development'),('Pune','city','in_development')]),
 'indiana':('US',[('northern Indiana','region','in_development')]),
 'indonesia':('ID',[('greater Jakarta','city','in_development')]),
 'italy':('IT',[('Lombardy','region','partially_operational')]),
 'japan':('JP',[]),
 'korea':('KR',[('Greater Busan','city','in_development')]),
 'malaysia':('MY',[('Kuala Lumpur','city','in_development')]),
 'mexico':('MX',[('Querétaro','city','operational'),('Ciudad Juárez','city','operational')]),
 'michigan':('US',[('West Michigan','region','in_development')]),
 'nevada':('US',[('Nevada','region','in_development')]),
 'new-zealand':('NZ',[('Auckland','city','in_development')]),
 'north-carolina':('US',[('Catawba County','region','planned'),('Person County','region','planned')]),
 'north-holland':('NL',[('Middenmeer','city','operational')]),
 'northern-virginia':('US',[('Fairfax','region','operational'),('Prince William','region','operational'),('Loudoun','region','operational')]),
 'ohio':('US',[('New Albany','city','in_development'),('Heath','city','in_development'),('Hebron','city','in_development')]),
 'quincy':('US',[('Quincy','city','operational'),('Malaga','city','in_development'),('East Wenatchee','city','in_development')]),
 'singapore':('SG',[('Singapore','city','operational')]),
 'south-africa':('ZA',[('City of Tshwane','region','in_development')]),
 'southern-virginia':('US',[('Boydton','city','operational')]),
 'spain':('ES',[('Greater Madrid','city','in_development')]),
 'suomidc':('FI',[('Southern Finland','region','in_development'),('Vaasa','city','in_development'),('Mustasaari','city','in_development')]),
 'sweden':('SE',[('Gävle','city','operational'),('Sandviken','city','operational'),('Staffanstorp','city','operational')]),
 'taiwan':('TW',[('broader Taipei','city','in_development')]),
 'united-kingdom':('GB',[('London','city','operational'),('South East','region','operational'),('Wales','region','operational')]),
 'warsaw-metropolitan-area-poland':('PL',[('greater Warsaw','city','operational')]),
 'wisconsin':('US',[('Racine County','region','in_development')]),
}

def claim(key, identifier, category, unit, name, cc, lifecycle='unknown', parties=None, properties=None):
    ev=evidence(key)
    return dict(record_id='microsoft:'+category+':'+slug(identifier),category=category,unit=unit,name=name,provider='Microsoft',
        parties=parties or [{'name':'Microsoft','role':'declaring_operator'}],country_codes=[cc] if cc else [],
        country_scope='source_named_country' if cc else 'not_assessed',lifecycle_status=lifecycle,
        source_scope='provider_declared',**ev,source_updated_at=sources()[key].get('source_updated_at'),confidence='high',
        geometry=None,spatial_representation='none',relationships=[],properties=properties or {})

def infrastructure(root):
    data=[]; coverage=[]
    for page,(cc,selections) in COMMUNITIES.items():
        key='community-'+page
        main=soup(key).find('main'); paragraphs=main.find_all('p')
        intro=clean(paragraphs[0].get_text(' ',strip=True))
        if selections:
            for label,precision,status in selections:
                assert norm(label) in norm(intro), (page,label,intro)
                data.append(claim(key,page+'-'+label+'-'+status,'datacenter_locality_presence',
                    'provider_locality_phase_assertion',label,cc,status,properties={
                        'locality':label,'location_precision':precision,'service':'microsoft_datacenters',
                        'community_directory_slug':page,'ownership':'not_disclosed',
                        'source_locator':'main first paragraph','source_paragraph_sha256':hashlib.sha256(intro.encode()).hexdigest(),
                        'physical_building_count':None,'not_a_unique_facility_inventory':True,
                        'lifecycle_is_source_statement_not_fresh_site_inspection':True}))
        coverage.append({'source_id':key,'locality_phase_assertions':len(selections),
            'disposition':'admitted_at_stated_precision' if selections else 'no_local_datacenter_assertion_in_intro'})
    m365_table=next(t for t in soup('m365-locations').find_all('table') if rows(t)[0]==['Geography','Datacenter locations (City)'])
    for geo,locations in rows(m365_table)[1:]:
        country,cc=country_identity(geo); assert cc
        for city in locations.split(', '):
            data.append(claim('m365-locations',cc+'-'+city,'m365_data_residency_locality',
                'service_country_city_declaration',city,cc,properties={'locality':city,'location_precision':'city',
                    'service':'microsoft_365_data_residency','residency_geography':geo,'ownership':'not_disclosed',
                    'physical_building_count':None,'not_a_unique_facility_inventory':True,
                    'macro_region_table_not_duplicated':True}))
    # Inspect every macro table city, admitting only country/city pairs absent
    # from the country table. Standalone country/SAR names have no city join.
    m365_pairs={(r['country_codes'][0],r['name']) for r in data if r['category']=='m365_data_residency_locality'}
    for _,locations in rows(soup('m365-locations').find_all('table')[0])[1:]:
        for country,cities in re.findall(r'(?:^|,\s*)([^(),]+)\s*\(([^()]+)\)',locations):
            _,cc=country_identity(country.strip());assert cc
            for city in cities.split(', '):
                if (cc,city) in m365_pairs:continue
                m365_pairs.add((cc,city))
                data.append(claim('m365-locations',cc+'-'+city,'m365_data_residency_locality',
                    'service_country_city_declaration',city,cc,properties={'locality':city,'location_precision':'city',
                        'service':'microsoft_365_data_residency','residency_geography':'macro_region_table',
                        'ownership':'not_disclosed','physical_building_count':None,'not_a_unique_facility_inventory':True,
                        'macro_region_memberships_deduplicated':True}))
    for table in soup('expressroute').find_all('table'):
        header=rows(table)[0]
        if not header[:2]==['Location','Address']:continue
        preceding=table.find_previous(['h2','h3'])
        section=preceding.get_text(' ',strip=True) if preceding else ''
        for tr in table.find_all('tr')[1:]:
            cells=tr.find_all('td'); values=[c.get_text(' | ',strip=True) for c in cells]
            assert len(values)==len(header)
            fields=dict(zip(header,values));location=fields['Location']
            data.append(claim('expressroute',section+'-'+location,'expressroute_interconnect',
                'directory_location_group',location,None,'operational',properties={
                    'locality_label':location,'directory_section':section,'source_fields':fields,
                    'service':'azure_expressroute','ownership':'host_facility_not_microsoft_ownership',
                    'cloud_compute_hosting_not_established':True,'country_not_geocoded':True,
                    'multiple_addresses_may_share_one_directory_row':True}))
    partners=[
        ('iren-childress','Childress','US',['IREN'],'in_development',True),
        ('nebius-vineland','Vineland','US',['Nebius'],'planned',True),
        ('nscale-narvik','Narvik','NO',['Nscale'],'planned',True),
        ('microsoft-sines','Sines','PT',['Nscale','Start Campus'],'planned',True),
        ('nscale-global','Texas','US',['Nscale','Ionic Digital'],'planned',False),
        ('microsoft-khazna','United Arab Emirates','AE',['G42','Khazna Data Centers'],'planned',False),
        ('microsoft-loughton','Loughton','GB',['Nscale'],'unknown',False),
    ]
    for key,locality,cc,names,status,plot in partners:
        props={'locality':locality,'location_precision':'city' if plot else 'region',
            'service':'microsoft_partner_capacity','ownership':'third_party_capacity_not_microsoft_owned',
            'map_eligible':plot,'delivery_since_announcement_not_independently_confirmed':True}
        if key=='microsoft-loughton':
            props.update(conflicting_recent_reporting=evidence('loughton-conflict'),
                current_affiliation_not_confirmed=True,map_excluded_reason='Recent reporting conflicts with earlier primary announcement; retain as unresolved history.')
        data.append(claim(key,key,'partner_compute_capacity','dated_capacity_agreement',locality,cc,status,
            parties=[{'name':'Microsoft','role':'capacity_customer'}]+[{'name':n,'role':'capacity_partner'} for n in names],properties=props))
    assert len(data)==len({r['record_id'] for r in data})
    definitions={
        'datacenter_locality_presence':'Microsoft community statement at locality and lifecycle scope; not a physical building or property title.',
        'm365_data_residency_locality':'Published service data-residency city; does not reveal a building, tenant assignment or property ownership.',
        'expressroute_interconnect':'Published interconnection directory row, sometimes grouping several host addresses; not a Microsoft-owned compute campus.',
        'partner_compute_capacity':'Dated third-party capacity agreement; no assumption that expected deployment has completed.',
    }
    collection={'type':'InfrastructureEvidenceCollection','schema_version':'1.0.0','retrieved_at':DATE,
        'scope_note':'Microsoft locality, residency, interconnection and partner assertions are separate units and cannot be summed as datacenters.',
        'categories':definitions,'records':sorted(data,key=lambda r:r['record_id'])}
    validate_collection(collection)
    relative=f'data/infrastructure/microsoft-evidence.{TAG}.json';write_json(root/relative,collection)
    write_json(root/relative.replace('.json','.report.json'),{'record_count':len(data),
        'category_counts':dict(Counter(r['category'] for r in data)), 'community_directory_coverage':coverage,
        'physical_datacenter_count':None,'all_geometry_null':True})
    return data

def footprints(root, claims):
    selections=read(RAW/f'locality-selections.{TAG}.json')
    gazetteer={r[0]:r for r in csv.reader((RAW/f'geonames-selected.{TAG}.tsv').read_text().splitlines(),delimiter='\t')}
    gazsrc=evidence('geonames-selected'); groups={};held=[]
    for r in claims:
        p=r['properties']
        if r['category']=='expressroute_interconnect':continue
        if p.get('location_precision')!='city' or p.get('map_eligible') is False:
            held.append({'record_id':r['record_id'],'reason':'region_only_or_conflicting_affiliation'});continue
        cc=r['country_codes'][0];label=p['locality']; lookup=cc+':'+label
        if lookup not in selections:
            held.append({'record_id':r['record_id'],'reason':'no_reviewed_gazetteer_match','locality':label});continue
        gn=selections[lookup]; g=gazetteer[gn]; assert g[8]==cc
        key=(p['service'],cc,gn)
        if key not in groups:
            groups[key]={'type':'Feature','geometry':{'type':'Point','coordinates':[float(g[5]),float(g[4])]},
                'properties':{'footprint_id':'microsoft:'+p['service']+':'+gn,'provider':'Microsoft','vendor_id':'microsoft',
                    'service':p['service'],'locality':g[1],'country_code':cc,'location_precision':'city',
                    'coordinate_method':'gazetteer_reference_point','coordinate_crs':'EPSG:4326',
                    'record_unit':'provider_service_locality','physical_site_confirmed':False,'lifecycle_status':'not_assessed',
                    'source_record_ids':[],'source_claim_ids':[],'source_locality_labels':[],'evidence':[],
                    'gazetteer':{'geonames_id':gn,'feature_code':g[7],'admin1':g[10],'name':g[1],
                        'evidence':gazsrc,'license_url':'https://creativecommons.org/licenses/by/4.0/'},
                    'excluded_from_canonical_totals':True}}
        pp=groups[key]['properties'];pp['source_claim_ids'].append(r['record_id'])
        pp['source_locality_labels']=sorted(set(pp['source_locality_labels']+[label]))
        ev={k:r[k] for k in ['source_url','raw_source_ref','source_sha256','retrieved_at']}
        if ev not in pp['evidence']:pp['evidence'].append(ev)
    features=sorted(groups.values(),key=lambda f:f['properties']['footprint_id'])
    payload={'type':'FeatureCollection','schema_version':'1.0.0','built_at':DATE,
        'excluded_from_canonical_totals':True,'features':features}
    load_validator(REPO_ROOT/'schema/geographic-footprint.schema.json').validate(payload)
    relative=f'data/microsoft/provider-localities.{TAG}.geojson';write_json(root/relative,payload)
    write_json(root/relative.replace('.geojson','.report.json'),{'record_count':len(features),
        'record_unit':'provider_service_locality','input_layers':[f'infrastructure/microsoft-evidence.{TAG}'],
        'held_claims':held,'canonical_members':0,'claim_members':sum(len(f['properties']['source_claim_ids']) for f in features),
        'excluded_from_canonical_totals':True,'physical_sites':False,
        'derived_files':{'csv':{'path':relative.replace('.geojson','.csv'),'source':relative,
            'generator':'make '+relative.replace('.geojson','.csv')}}})
    return payload,held

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-root',type=Path,default=REPO_ROOT)
    args=parser.parse_args();root=args.output_root
    locations=frontdoor(root)+network_pops(root)+cloud_regions(root)+sovereign_regions(root)
    assertions=infrastructure(root);footprint,held=footprints(root,assertions)
    review={'retrieved_at':DATE,'scope':'Public Microsoft/Azure infrastructure; inventory completeness is not asserted.',
        'location_records_by_service':dict(Counter(r['service'] for r in locations)),
        'assertions_by_category':dict(Counter(r['category'] for r in assertions)),
        'locality_references':len(footprint['features']),'held_claims':held,
        'unique_physical_datacenter_count':None,'ownership_inventory_complete':False,
        'source_catalog':repo_ref(CATALOG),'source_catalog_sha256':sha256(CATALOG),
        'quality_findings':[
            {'severity':'high','finding':'Front Door metro, abbreviation and global-network directories overlap; counts are distinct evidence units.'},
            {'severity':'high','finding':'Regions and service cities cannot establish individual campus boundaries or ownership.'},
            {'severity':'high','finding':'Three globe POPs grouped under China retain reviewed Hong Kong jurisdiction; six broad source City labels retain regional precision.'},
            {'severity':'medium','finding':'Some community introductions retain construction wording after a cloud region opened; preserve scope and date instead of promoting lifecycle.'},
            {'severity':'high','finding':'Loughton current Microsoft affiliation is unresolved after October 2026 withdrawal reporting; no locality marker admitted.'},
            {'severity':'medium','finding':'Expected partner delivery dates do not demonstrate completed deployment.'}],
        'remaining_gaps':['Non-public Microsoft leased/owned facility inventory and street addresses.',
            'No generic mapping from CoreWeave sites or Microsoft investments to Microsoft-occupied campuses.',
            'No synthetic Azure availability-zone IDs or inferred AZ coordinates.',
            'No service availability, tenancy, latency or ownership guarantee from a map point.']}
    write_json(root/f'data/microsoft/enrichment-review.{TAG}.json',review)
    print(json.dumps({k:v for k,v in review.items() if k not in ['held_claims','quality_findings','remaining_gaps']},indent=2))

if __name__=='__main__':main()
