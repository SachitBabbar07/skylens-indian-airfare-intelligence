"""Download openly offered public archives without authentication; preserve originals."""
from pathlib import Path
import urllib.request, json, hashlib, datetime, zipfile, concurrent.futures
ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'data/metadata'
MANIFEST=json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SkyLens-research/1.0'}),timeout=90) as r:return r.read()
def acquire(ref):
    sid=ref.split('/')[0] if not ref.startswith('promptcloud/') else ref.replace('/','__')
    fixed=MANIFEST['fare_sources'][ref]
    try:
        meta=json.loads(get('https://www.kaggle.com/api/v1/datasets/view/'+ref))
        (META/('kaggle_'+ref.replace('/','__')+'.json')).write_text(json.dumps(meta,indent=2),encoding='utf-8')
        folder=ROOT/'data/raw'/sid;folder.mkdir(parents=True,exist_ok=True)
        path=folder/'original.zip'; url='https://www.kaggle.com/api/v1/datasets/download/'+ref+'?datasetVersionNumber='+str(fixed['version'])
        if not path.exists():path.write_bytes(get(url))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=fixed['archive_sha256']:raise ValueError('Archive differs from frozen source hash; preserve and investigate, never silently reuse')
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            for name in names:
                target=(folder/name).resolve()
                if folder.resolve() not in target.parents:raise ValueError('Unsafe archive member')
                if not target.exists():z.extract(name,folder)
        for spec in fixed['files']:
            if hashlib.sha256((folder/spec['filename']).read_bytes()).hexdigest()!=spec['sha256']:raise ValueError('Extracted source hash mismatch')
        entry={'source':ref,'source_url':'https://www.kaggle.com/datasets/'+ref,'download_url':url,'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'license':meta.get('licenseName'),'source_updated':fixed['source_updated'],'version':fixed['version'],'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archive_bytes':path.stat().st_size,'files':names}
        print(json.dumps({'source':ref,'license':entry['license'],'files':names,'version':fixed['version']},ensure_ascii=True),flush=True)
        return entry
    except Exception as e:
        print(json.dumps({'source':ref,'error':str(e)}),flush=True);return {'source':ref,'error':str(e)}
refs=['shubhambathwal/flight-price-prediction','yashdharme36/airfare-ml-predicting-flight-fares','iamavyukt/goibibo-flight-data','shraddha4ever20/indian-domestic-flights-dataset-20192025','andrewgeorgeissac/flight-price-data-of-indian-cities-makemytrip','sumitjaiswar/indian-domestic-flights-data','promptcloud/easemytrip-flight-fare-details-2020','promptcloud/easemytrip-flight-fare-travel-listings']
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: registry=list(pool.map(acquire,refs))
    if any('error' in entry for entry in registry):
        (META/'acquisition_failures.json').write_text(json.dumps(registry,indent=2),encoding='utf-8')
        raise RuntimeError('One or more frozen sources failed acquisition; preserve prior registry and investigate.')
    # Pin metadata downloads to the actual Git commit rather than moving main.
    commit=MANIFEST['ourairports']['commit']; folder=ROOT/'data/raw/ourairports';folder.mkdir(parents=True,exist_ok=True)
    for name in ['airports.csv','regions.csv','LICENSE']:
        url=f'https://raw.githubusercontent.com/davidmegginson/ourairports-data/{commit}/{name}'
        p=folder/name
        if not p.exists():p.write_bytes(get(url))
        if hashlib.sha256(p.read_bytes()).hexdigest()!=MANIFEST['ourairports']['files'][name]:raise ValueError('Airport source hash mismatch')
        registry.append({'source':'OurAirports','source_url':'https://ourairports.com/data/','download_url':url,'retrieved_at_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'license':'Public domain (data); Unlicense (repository)','commit':commit,'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    prior_registry = META/'dataset_registry.json'
    if prior_registry.exists():
        previous = json.loads(prior_registry.read_text(encoding='utf-8'))
        for fresh in registry:
            old = next((entry for entry in previous
                        if entry.get('source') == fresh.get('source')
                        and entry.get('archive_sha256') == fresh.get('archive_sha256')), {})
            if old.get('semantic_verification'):
                fresh['semantic_verification'] = old['semantic_verification']
        # Audit-only discoveries must survive a replay of the original sources;
        # they are never added to the frozen training-source manifest.
        registry.extend(entry for entry in previous
                        if entry.get('role') == 'audit_only_not_training')
    (META/'dataset_registry.json').write_text(json.dumps(registry,indent=2),encoding='utf-8')
    import pandas as pd
    profiles=[]
    for p in (ROOT/'data/raw').rglob('*'):
        if p.suffix.lower() not in ['.csv','.xlsx','.xls']:continue
        try:
            df=pd.read_csv(p,low_memory=False) if p.suffix.lower()=='.csv' else pd.read_excel(p)
            profile={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'rows':len(df),'columns':list(df),'dtypes':{c:str(t) for c,t in df.dtypes.items()},'missing':df.isna().sum().to_dict(),'duplicates':int(df.duplicated().sum()),'sample':df.head(2).fillna('').to_dict('records')}
            profiles.append(profile)
            print(json.dumps({k:profile[k] for k in ['path','rows','columns']},default=str,ensure_ascii=True),flush=True)
        except Exception as e:profiles.append({'path':str(p.relative_to(ROOT)),'error':str(e)})
    (META/'file_profiles.json').write_text(json.dumps(profiles,indent=2,default=str),encoding='utf-8')
