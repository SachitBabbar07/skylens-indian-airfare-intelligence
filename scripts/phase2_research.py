"""Save public source evidence for phase two; never overwrite original datasets."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,urllib.request,urllib.parse
R=Path(__file__).resolve().parents[1];OUT=R/'data/metadata/phase2'
QUERIES=['India flight INR','Indian airfare currency','India flight price 2024','India flight price 2025','India flight round trip','flight price per passenger','flight price prediction']
def get(job):
 name,url=job
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'SkyLens academic source audit/0.2'})
  with urllib.request.urlopen(req,timeout=45) as resp:raw=resp.read();ctype=resp.headers.get('Content-Type','')
  path=OUT/(name+('.json' if 'json' in ctype else '.txt'));path.write_bytes(raw)
  data=json.loads(raw) if 'json' in ctype else None
  e={'name':name,'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'path':str(path.relative_to(R)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'content_type':ctype}
  if name.startswith('kaggle_search'):e['results']=[{k:x.get(k) for k in ['ref','title','licenseName','totalBytes']} for x in data]
  elif name.startswith('hf_search'):e['results']=[{k:x.get(k) for k in ['id','tags']} for x in data]
  elif name.startswith('card_'):e['summary']={k:data.get(k) for k in ['ref','licenseName','currentVersionNumber','description']}
  elif name.startswith('filelist_'):e['top_keys']=list(data) if isinstance(data,dict) else 'list';e['file_preview']=str(data)[:1500]
  elif name.startswith('gh_'):e['summary']=[{k:x.get(k) for k in ['name','path','type','size']} for x in data] if isinstance(data,list) else {k:data.get(k) for k in ['full_name','license','default_branch','description']}
  return e
 except Exception as exc:return {'name':name,'url':url,'error':str(exc)}
refs=['yashdharme36/airfare-ml-predicting-flight-fares','promptcloud/easemytrip-flight-fare-details-2020','promptcloud/easemytrip-flight-fare-travel-listings','shubhambathwal/flight-price-prediction','andrewgeorgeissac/flight-price-data-of-indian-cities-makemytrip']
jobs=[('kaggle_search_'+str(i),'https://www.kaggle.com/api/v1/datasets/list?'+urllib.parse.urlencode({'search':q,'pageSize':25})) for i,q in enumerate(QUERIES)]
jobs += [('card_'+ref.replace('/','__'),'https://www.kaggle.com/api/v1/datasets/view/'+ref) for ref in refs]
jobs += [('filelist_'+ref.replace('/','__'),'https://www.kaggle.com/api/v1/datasets/list/'+ref) for ref in refs]
jobs += [('hf_search_'+str(i),'https://huggingface.co/api/datasets?'+urllib.parse.urlencode({'search':q,'limit':30,'full':'true'})) for i,q in enumerate(['Indian flight','flight fare','flight price','round trip'])]
jobs += [('gh_index','https://api.github.com/repos/keyholder1/sih-india-airfare-price-index'),('gh_index_tree','https://api.github.com/repos/keyholder1/sih-india-airfare-price-index/git/trees/main?recursive=1'),('gh_observatory','https://api.github.com/repos/notlega/flight-price-observatory'),('gh_observatory_root','https://api.github.com/repos/notlega/flight-price-observatory/contents')]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(get,jobs))
(OUT/'retrieval_log.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
for r in results:
 out={k:r[k] for k in ['name','error','results','top_keys','file_preview','summary'] if k in r}
 if out.get('name','').startswith('card_'):out['summary'].pop('description',None)
 if out.get('name')=='gh_index_tree':out['summary']='Full tree snapshot saved'
 print(json.dumps(out,ensure_ascii=True))
