"""Freeze source versions and enrich comparison with measured file statistics."""
from pathlib import Path
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'data/metadata';R=ROOT/'reports'
reg=json.loads((M/'dataset_registry.json').read_text());manifest={'fare_sources':{},'ourairports':{}}
for e in reg:
    if e.get('role') == 'audit_only_not_training':continue
    if 'error' in e:continue
    if e['source']!='OurAirports':
        folder=e['source'].replace('/','__') if e['source'].startswith('promptcloud/') else e['source'].split('/')[0]
        e['file_profiles']=[p for p in json.loads((M/'file_profiles.json').read_text()) if p.get('path','').replace('\\','/').startswith('data/raw/'+folder+'/')]
    if e['source']=='OurAirports':
        manifest['ourairports']['commit']=e['commit'];manifest['ourairports'].setdefault('files',{})[Path(e['path']).name]=e['sha256']
        profile=next((p for p in json.loads((M/'file_profiles.json').read_text()) if p.get('path')==e.get('path')),None)
        if profile:e['file_profile']=profile
    else:
        manifest['fare_sources'][e['source']]={'version':e['version'],'source_updated':e['source_updated'],'archive_sha256':e['archive_sha256'],'files':[{'filename':Path(p['path']).name,'sha256':p['sha256']} for p in e.get('file_profiles',[])]}
write=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
write(ROOT/'config/sources.json',manifest);write(M/'dataset_registry.json',reg)
from sys import path
path.insert(0,str(ROOT/'src'))
from skylens.prepare import CITY_CODES
comparison=pd.read_csv(R/'dataset_comparison.csv')
for idx,row in comparison.iterrows():
    ref=row.source;e=next((e for e in reg if e.get('source')==ref),None)
    if not e or ref=='OurAirports':continue
    owner=ref.split('/')[0];folder=ROOT/'data/raw'/(ref.replace('/','__') if owner=='promptcloud' else owner)
    files=list(folder.glob('*.csv'));frames=[pd.read_csv(p,low_memory=False) for p in files]
    if owner=='yashdharme36':df=pd.read_csv(folder/'Cleaned_dataset.csv');origin,dest,carrier,cabin='Source','Destination','Airline','Class';dates=pd.to_datetime(df.Date_of_journey);booking=1
    elif owner=='shubhambathwal':df=pd.concat([pd.read_csv(folder/'economy.csv').assign(cabin='Economy'),pd.read_csv(folder/'business.csv').assign(cabin='Business')]);origin,dest,carrier,cabin='from','to','airline','cabin';dates=pd.to_datetime(df.date,dayfirst=True);booking=None
    elif owner=='promptcloud':df=frames[0];origin,dest,carrier,cabin='Source','Destination','Flight Operator',None;dates=pd.to_datetime(df['Departure Date'],format='%d%b%Y');booking=pd.to_datetime(df['Crawl Timestamp'],utc=True).dt.tz_convert('Asia/Kolkata').dt.date.nunique()
    elif owner=='iamavyukt':df=frames[0];origin,dest,carrier,cabin='from','to','airline','class';dates=pd.to_datetime(df['flight date'],dayfirst=True);booking=None
    elif owner=='shraddha4ever20':df=frames[0];origin,dest,carrier,cabin='Source','destination','airline',None;dates=pd.to_datetime(df.date_of_journey);booking=None
    elif owner=='andrewgeorgeissac':df=pd.concat(frames);origin,dest,carrier,cabin='DepartingCity','ArrivingCity','FlightName',None;dates=None;booking=None
    elif owner=='sumitjaiswar':df=frames[0];origin,dest,carrier,cabin='Origin_airport','Destination_airport',None,None;dates=pd.to_datetime(df.Fly_date,dayfirst=True);booking=None
    else:continue
    endpoints=set(df[origin].dropna())|set(df[dest].dropna());mapped={CITY_CODES[x] for x in endpoints if x in CITY_CODES} if owner!='sumitjaiswar' else endpoints
    fields={'format':'CSV','inspected_csv_bytes':sum(p.stat().st_size for p in files),'assessment_rows':len(df),'assessment_representation':'one representative cleaned or raw union; never sum raw+cleaned','unique_source_labels':df[origin].nunique(),'unique_destination_labels':df[dest].nunique(),'unique_endpoint_labels':len(endpoints),'mapped_indian_airports':len(mapped),'directional_label_routes':len(df[[origin,dest]].drop_duplicates()),'airline_labels':df[carrier].nunique() if carrier else None,'cabin_labels':', '.join(sorted(df[cabin].unique())) if cabin else 'not recorded','missing_percent_assessment':100*df.isna().sum().sum()/df.size,'exact_duplicates_assessment':int(df.duplicated().sum()),'travel_start':str(dates.min().date()) if dates is not None else None,'travel_end':str(dates.max().date()) if dates is not None else None,'collection_days':booking,'confirmed_one_way_booking':False,'confirmed_round_trip':False,'confirmed_multi_city':False,'currency_explicit':'not recorded','passenger_basis':'not recorded','price_scope':'base fare excluding taxes (publisher)' if owner=='andrewgeorgeissac' else 'not verified','booking_lead_time_available':owner in ['yashdharme36','promptcloud'],'return_date_available':False,'departure_clock_available':owner!='sumitjaiswar','duration_available':owner!='sumitjaiswar','stops_available':owner in ['yashdharme36','shubhambathwal','promptcloud','iamavyukt','shraddha4ever20'],'airport_code_quality':'explicit reviewed city mapping' if owner!='sumitjaiswar' else 'source IATA labels; authenticity unverified'}
    for k,v in fields.items():comparison.loc[idx,k]=v
comparison.to_csv(R/'dataset_comparison.csv',index=False)
# Verify every frozen byte hash; extraction cannot silently replace original contents.
verified=0
for ref,e in manifest['fare_sources'].items():
    folder=ROOT/'data/raw'/(ref.replace('/','__') if ref.startswith('promptcloud/') else ref.split('/')[0])
    assert hashlib.sha256((folder/'original.zip').read_bytes()).hexdigest()==e['archive_sha256'];verified+=1
    for f in e['files']:assert hashlib.sha256((folder/f['filename']).read_bytes()).hexdigest()==f['sha256'];verified+=1
for name,sha in manifest['ourairports']['files'].items():assert hashlib.sha256((ROOT/'data/raw/ourairports'/name).read_bytes()).hexdigest()==sha;verified+=1
write(R/'raw_integrity_results.json',{'verified_original_files':verified,'all_hashes_match':True})
print('Enriched comparison; froze source versions; verified',verified,'original files.')

# Make observation coverage and fitting/serving evidence separately inspectable in CSV.
a=pd.read_csv(R/'airport_fare_coverage.csv',keep_default_na=False)
eligible=set()
for cohort in ['network_2020','cabin_2023']:
    support=pd.read_csv(ROOT/f'models/{cohort}/support.csv')
    endpoint_counts=pd.concat([support.groupby('origin')['n'].sum(),support.groupby('destination')['n'].sum()]).groupby(level=0).sum()
    a[cohort+'_fitting_endpoint_observations']=a.iata_code.map(endpoint_counts).fillna(0).astype(int)
    cells=support[support.eligible]
    codes=set(cells.origin)|set(cells.destination)
    a[cohort+'_research_eligible']=a.iata_code.isin(codes)
    eligible.update(codes)
a['any_research_eligible']=a.iata_code.isin(eligible)
a['insufficient_training_evidence']=a.has_fare_observations & ~a.any_research_eligible
a.to_csv(R/'airport_fare_coverage.csv',index=False)
