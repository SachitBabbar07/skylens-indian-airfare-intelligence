from pathlib import Path
import datetime,hashlib,json,urllib.request,zipfile
import pandas as pd
R=Path.cwd();O=R/'data/metadata/phase2';registry=[];profiles=[]
refs=['viveksharmar/flight-price-data','sshriya08/flight-price-prediction-dataset','ankushsonar/flight-price-dataset-india-2019','prithvirajshukla/flight-fare-prediction']
for ref in refs:
 card=O/('candidate_'+ref.replace('/','__')+'.json');meta=json.loads(card.read_text());folder=R/'data/raw/phase2'/ref.replace('/','__');folder.mkdir(parents=True,exist_ok=True);p=folder/'original.zip';url='https://www.kaggle.com/api/v1/datasets/download/'+ref+'?datasetVersionNumber='+str(meta['currentVersionNumber'])
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=60).read())
 with zipfile.ZipFile(p) as archive:
  for info in archive.infolist():
   target=(folder/info.filename).resolve()
   if folder.resolve() not in target.parents:raise ValueError('Unsafe archive path')
   if not target.exists():archive.extract(info,folder)
 registry.append({'source':ref,'source_url':'https://www.kaggle.com/datasets/'+ref,'download_url':url,'retrieved_at_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'license':meta['licenseName'],'version':meta['currentVersionNumber'],'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'role':'audit_only_not_training','training_eligible':False})
 for f in folder.rglob('*'):
  if f.suffix not in ['.csv','.xlsx']:continue
  d=pd.read_csv(f,low_memory=False) if f.suffix=='.csv' else pd.read_excel(f)
  e={'source':ref,'path':str(f.relative_to(R)),'rows':len(d),'columns':list(d),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'duplicates':int(d.duplicated().sum()),'missing':d.isna().sum().to_dict(),'sample':d.head(2).fillna('').to_dict('records')};profiles.append(e)
  print(json.dumps({k:e[k] for k in ['source','path','rows','columns','sample']},default=str,ensure_ascii=True))
url='https://indiacheapflights.com/fare-index.json';folder=R/'data/raw/phase2/india_cheap_flights_index';folder.mkdir(parents=True,exist_ok=True);p=folder/'fare-index.json'
try:
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=40).read())
 data=json.loads(p.read_bytes());print('INDEX_SCHEMA',str(data)[:1000])
 registry.append({'source':'India Cheap Flights Fare Index November 2026','source_url':'https://indiacheapflights.com/press/','download_url':url,'retrieved_at_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'license':'CC BY 4.0 (publisher)','path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'role':'aggregate_audit_only_not_training','training_eligible':False})
except Exception as e:print('INDEX_ERROR',str(e))
for name,url in [('index_generator','https://raw.githubusercontent.com/keyholder1/sih-india-airfare-price-index/main/examples/generate_sample_fares.py'),('index_fares_readme','https://raw.githubusercontent.com/keyholder1/sih-india-airfare-price-index/main/data/raw/fares/README.md')]:
 try:
  b=urllib.request.urlopen(url,timeout=30).read();(O/(name+'.txt')).write_bytes(b);print(name,b[:300].decode(errors='replace'))
 except Exception as e:print(name,str(e))
(O/'new_source_registry.json').write_text(json.dumps(registry,indent=2),encoding='utf-8');(O/'new_file_profiles.json').write_text(json.dumps(profiles,indent=2,default=str),encoding='utf-8')
