"""Canonical source-specific research cohorts. Unknowns are never filled with claims."""
from pathlib import Path
import hashlib, json, re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]

def digest_frame(df):
    return pd.util.hash_pandas_object(df.fillna('<missing>').astype(str),index=False).astype(str)

def duration_minutes(value):
    text=str(value).strip().lower()
    h=re.search(r'(\d+)\s*h',text);m=re.search(r'(\d+)\s*m',text)
    if not h and not m:return np.nan
    return (int(h[1]) if h else 0)*60+(int(m[1]) if m else 0)

# Explicit, reviewed historical city-to-airport mapping. No nearest-airport guesses.
CITY_CODES={
'Delhi':'DEL','New Delhi':'DEL','Mumbai':'BOM','Bangalore':'BLR','Bengaluru':'BLR','Hyderabad':'HYD','Kolkata':'CCU','Chennai':'MAA','Ahmedabad':'AMD',
'Bhubaneswar':'BBI','Kochi':'COK','Cochin':'COK','Goa':'GOI','Guwahati':'GAU','Amritsar':'ATQ','Coimbatore':'CJB','Bhopal':'BHO','Indore':'IDR','Dehra Dun':'DED','Jaipur':'JAI','Vadodara':'BDQ','Lucknow':'LKO','Chandigarh':'IXC','Kozhikode':'CCJ','Patna':'PAT','Mangalore':'IXE','Jammu':'IXJ','Pune':'PNQ','Port Blair':'IXZ','Agartala':'IXA','Bagdogra':'IXB','Ranchi':'IXR','Aizawl':'AJL','Madurai':'IXM','Hubli':'HBX','Imphal':'IMF','Raipur':'RPR','Jodhpur':'JDH','Nagpur':'NAG','Trivandrum':'TRV','Tirupati':'TIR','Udaipur':'UDR','Kannur':'CNN','Surat':'STV','Gorakhpur':'GOP','Vijayawada':'VGA','Allahabad':'IXD','Srinagar':'SXR','Dibrugarh':'DIB','Rajkot':'RAJ','Aurangabad':'IXU','Belgaum':'IXG','Gaya':'GAY','Silchar':'IXS','Bhuj':'BHJ','Dharamsala':'DHM','Agatti Island':'AGX','Rajahmundry':'RJA','Leh':'IXL','Dimapur':'DMU','Jorhat':'JRH','Kadapa':'CDP','Jaisalmer':'JSA','Pondicherry':'PNY','Puducherry':'PNY','Agra':'AGR','Lilabari':'IXI','Varanasi':'VNS','Visakhapatnam':'VTZ','Tiruchirapally':'TRZ','Jabalpur':'JLR','Shirdi':'SAG','Durgapur':'RDP','Nanded':'NDC','Kanpur':'KNU','Jharsuguda':'JRG','Gwalior':'GWL','Mysore':'MYQ','Kullu':'KUU','Jamnagar':'JGA','Bhavnagar':'BHU','Khajuraho':'HJR','Diu':'DIU','Kolhapur':'KLH','Tuticorin':'TCR','Tezpur':'TEZ','Pantnagar':'PGH','Ajmer':'KQH','Porbandar':'PBD','Simla':'SLV','Nasik':'ISK','Pathankot':'IXP'}

def airport_master():
    a=pd.read_csv(ROOT/'data/raw/ourairports/airports.csv',keep_default_na=False)
    a=a[a.iso_country.eq('IN')].copy()
    regions=pd.read_csv(ROOT/'data/raw/ourairports/regions.csv',keep_default_na=False)
    a['state']=a.iso_region.map(regions.set_index('code')['name'])
    a['source']='OurAirports';a['source_url']='https://ourairports.com/data/'
    reg=json.loads((ROOT/'data/metadata/dataset_registry.json').read_text())
    entry=next(x for x in reg if x.get('source')=='OurAirports' and x.get('path','').endswith('airports.csv'))
    a['source_date']=entry['retrieved_at_utc'];a['source_commit']=entry['commit']
    a['operational_status']=np.where(a.type.eq('closed'),'reported closed','not independently verified')
    a['schedule_evidence']=np.where(a.scheduled_service.eq('yes'),'crowd-sourced scheduled-service flag','none in selected sources')
    assert not a.loc[a.iata_code.ne(''),'iata_code'].duplicated().any(), 'Conflicting Indian IATA mappings'
    a.to_csv(ROOT/'reports/india_airport_master.csv',index=False)
    mapping=pd.DataFrame([{'source_city':city,'iata_code':code} for city,code in CITY_CODES.items()])
    mapping=mapping.merge(a.loc[a.iata_code.ne(''),['iata_code','name','municipality','type']],on='iata_code',how='left',validate='many_to_one')
    assert mapping.name.notna().all()
    mapping['decision']='Explicit historical city mapping; see airport_coverage_analysis.md'
    mapping.to_csv(ROOT/'data/metadata/city_airport_mapping.csv',index=False)
    return a

def enrich(df,airports):
    ref=airports[airports.iata_code.ne('')].set_index('iata_code')
    for end in ['origin','destination']:
        for short,col in [('lat','latitude_deg'),('lon','longitude_deg')]:df[end+'_'+short]=pd.to_numeric(df[end].map(ref[col]),errors='coerce')
    lat1,lat2=np.radians(df.origin_lat),np.radians(df.destination_lat)
    dl=np.radians(df.destination_lon-df.origin_lon);da=lat2-lat1
    df['distance_km']=6371*2*np.arcsin(np.sqrt(np.clip(np.sin(da/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dl/2)**2,0,1)))
    df['route']=df.origin+'-'+df.destination
    df['currency']=None;df['normalized_price_inr']=np.nan
    df['price_scope']='unknown';df['passenger_basis']='unknown'
    df['journey_type']='single_direction_record';df['return_date']=None
    return df

def finish(df,name,a,initial_rows,earlier_exclusions=None):
    df=enrich(df,a)
    checks={
      'unmapped_or_international_endpoint':df.origin.isna()|df.destination.isna(),
      'same_origin_destination':df.origin.eq(df.destination),
      'invalid_price':df.price.isna()|~np.isfinite(df.price)|(df.price<=0),
      'invalid_duration':df.duration_minutes.isna()|(df.duration_minutes<=0)|(df.duration_minutes>72*60),
      'invalid_dates_or_lead_time':df.travel_date.isna()|df.collection_date.isna()|df.days_left.isna()|(df.days_left<0),
      'invalid_stops':df.stops.isna()|(df.stops<0)|(df.stops>4),
      'invalid_departure_hour':df.departure_hour.isna()|(df.departure_hour<0)|(df.departure_hour>=24),
      'missing_geo_or_airline':df.origin_lat.isna()|df.destination_lat.isna()|df.airline.isna(),
    }
    reasons=pd.Series('',index=df.index)
    for label,mask in checks.items():reasons.loc[mask & reasons.eq('')]=label
    bad=df[reasons.ne('')][['source_record_id']].copy();bad['reason']=reasons[reasons.ne('')]
    clean=df[reasons.eq('')].copy()
    fingerprint_cols=['origin','destination','airline','flight','cabin_class','travel_date','collection_date','departure_hour','duration_minutes','stops','price']
    clean['fingerprint']=digest_frame(clean[fingerprint_cols])
    dup=clean.fingerprint.duplicated();dup_rows=clean.loc[dup,['source_record_id']].copy();dup_rows['reason']='exact_canonical_duplicate'
    clean=clean[~dup].copy()
    quote_cols=['origin','destination','airline','flight','cabin_class','travel_date','departure_hour','duration_minutes','stops']
    clean['quote_group']=digest_frame(clean[quote_cols])
    excluded=pd.concat([x for x in [earlier_exclusions,bad,dup_rows] if x is not None],ignore_index=True)
    excluded.to_csv(ROOT/f'data/interim/{name}_exclusions.csv',index=False)
    clean.to_parquet(ROOT/f'data/processed/{name}.parquet',index=False)
    profile={'input_rows':initial_rows,'retained_rows':len(clean),'excluded_rows':len(excluded),'exclusion_reasons':excluded.reason.value_counts().to_dict(),'airports':sorted(set(clean.origin)|set(clean.destination)),'origins':int(clean.origin.nunique()),'destinations':int(clean.destination.nunique()),'routes':int(clean.route.nunique()),'airlines':clean.airline.value_counts().to_dict(),'cabins':clean.cabin_class.value_counts().to_dict(),'date_min':str(clean.travel_date.min().date()),'date_max':str(clean.travel_date.max().date()),'collection_min':str(clean.collection_date.min().date()),'collection_max':str(clean.collection_date.max().date()),'lead_min':int(clean.days_left.min()),'lead_max':int(clean.days_left.max()),'price_summary':clean.price.describe(percentiles=[.01,.5,.95,.99]).to_dict(),'missing':{k:int(v) for k,v in clean.isna().sum().items()}}
    assert initial_rows==len(clean)+len(excluded)
    return clean,profile

def prepare():
    a=airport_master();cohorts={};profiles={}
    raw=pd.read_csv(ROOT/'data/raw/yashdharme36/Scraped_dataset.csv')
    curated=pd.read_csv(ROOT/'data/raw/yashdharme36/Cleaned_dataset.csv')
    price=pd.to_numeric(raw.Price.str.replace(',',''),errors='coerce')
    travel=pd.to_datetime(raw['Date of Journey'],format='%d/%m/%Y',errors='coerce')
    booked=pd.to_datetime(raw['Date of Booking'],format='%d/%m/%Y',errors='coerce')
    assert len(raw)==len(curated) and np.array_equal(price,curated.Fare)
    assert (travel==pd.to_datetime(curated.Date_of_journey)).all()
    assert ((travel-booked).dt.days==curated.Days_left).all()
    parts=raw['Airline-Class'].str.split('\n')
    df=pd.DataFrame({'source_dataset':'yashdharme36/airfare-ml-predicting-flight-fares','source_record_id':raw.index.astype(str),'origin_city':curated.Source,'destination_city':curated.Destination,'origin':curated.Source.map(CITY_CODES),'destination':curated.Destination.map(CITY_CODES),'airline':curated.Airline,'flight':curated.Flight_code,'cabin_class':curated.Class,'travel_date':travel,'collection_date':booked,'days_left':curated.Days_left,'departure_hour':pd.to_timedelta(raw['Departure Time'].str.split('\n').str[0]+':00',errors='coerce').dt.total_seconds()/3600,'duration_minutes':raw.Duration.map(duration_minutes),'stops':curated.Total_stops.map({'non-stop':0,'1-stop':1,'2+-stop':2}),'price':price})
    cohorts['cabin_2023'],profiles['cabin_2023']=finish(df,'cabin_2023',a,len(raw))
    for cohort,slug in [('network_2020','easemytrip-flight-fare-details-2020'),('network_external_2020','easemytrip-flight-fare-travel-listings')]:
        folder=ROOT/'data/raw'/('promptcloud__'+slug);p=next(folder.glob('*.csv'));r=pd.read_csv(p)
        travel=pd.to_datetime(r['Departure Date'],format='%d%b%Y',errors='coerce');booked=pd.to_datetime(r['Crawl Timestamp'],utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None).dt.normalize()
        df=pd.DataFrame({'source_dataset':'promptcloud/'+slug,'source_record_id':r['Uniq Id'],'origin_city':r.Source,'destination_city':r.Destination,'origin':r.Source.map(CITY_CODES),'destination':r.Destination.map(CITY_CODES),'airline':r['Flight Operator'],'flight':r['Flight Number'],'cabin_class':'Unspecified','travel_date':travel,'collection_date':booked,'days_left':(travel-booked).dt.days,'departure_hour':pd.to_timedelta(r['Departure Time']+':00',errors='coerce').dt.total_seconds()/3600,'duration_minutes':r['Total Time'].map(duration_minutes),'stops':pd.to_numeric(r['Number Of Stops'],errors='coerce'),'price':pd.to_numeric(r.Fare,errors='coerce')})
        foreign_layover=r[['Layover1','Layover2','Layover3']].apply(lambda col:col.notna()&~col.isin(CITY_CODES)).any(axis=1)
        early=df.loc[foreign_layover,['source_record_id']].copy();early['reason']='unmapped_or_international_layover'
        cohorts[cohort],profiles[cohort]=finish(df[~foreign_layover].copy(),cohort,a,len(r),early)
    (ROOT/'data/metadata/cohort_profiles.json').write_text(json.dumps(profiles,indent=2),encoding='utf-8')
    all_fares=pd.concat(list(cohorts.values()),ignore_index=True)
    counts=pd.concat([all_fares.origin,all_fares.destination]).value_counts()
    a['fare_endpoint_observations']=a.iata_code.map(counts).fillna(0).astype(int)
    a['has_fare_observations']=a.fare_endpoint_observations.gt(0)
    a['production_eligible']=False;a['coverage_status']=np.where(a.has_fare_observations,'research observations only','no selected fare observations')
    a.to_csv(ROOT/'reports/airport_fare_coverage.csv',index=False)
    coverage=all_fares.groupby(['source_dataset','origin','destination','cabin_class'],dropna=False).agg(observations=('price','size'),median_recorded_fare=('price','median')).reset_index()
    coverage.to_csv(ROOT/'reports/route_fare_coverage.csv',index=False)
    (ROOT/'data/metadata/coverage_counts.json').write_text(json.dumps({'indian_airfield_records':len(a),'with_iata':int(a.iata_code.ne('').sum()),'scheduled_flag':int(a.scheduled_service.eq('yes').sum()),'fare_airports':int(a.has_fare_observations.sum()),'fare_origins':int(all_fares.origin.nunique()),'fare_destinations':int(all_fares.destination.nunique()),'fare_routes':int(all_fares.route.nunique()),'production_eligible_airports':0,'without_fare_evidence':int((~a.has_fare_observations).sum())},indent=2))
    print(json.dumps({name:{k:v for k,v in p.items() if k not in ['missing','airlines','price_summary']} for name,p in profiles.items()},indent=2))
    print('coverage',json.loads((ROOT/'data/metadata/coverage_counts.json').read_text()))

if __name__=='__main__':prepare()
