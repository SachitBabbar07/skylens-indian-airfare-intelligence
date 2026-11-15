"""Snapshot public repository search results; no credentials or scraping."""
from pathlib import Path
import json, urllib.request, urllib.parse, concurrent.futures, datetime, shutil, os
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'metadata'; OUT.mkdir(parents=True, exist_ok=True)
def fetch(item):
    name,url=item
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'SkyLens-college-research/1.0'})
        with urllib.request.urlopen(req,timeout=45) as r: data=json.load(r)
        (OUT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
        if name.startswith('kaggle_search'):
            return name,[{k:d.get(k) for k in ['ref','title','lastUpdated','totalBytes','licenseName','description']} for d in data][:35]
        if name.startswith('hf_search'):
            return name,[{k:d.get(k) for k in ['id','lastModified','downloads','tags']} for d in data][:40]
        return name, data
    except Exception as e:
        (OUT/(name+'.error.txt')).write_text(str(e),encoding='utf-8')
        return name, str(e)
if __name__=='__main__':
    queries=['indian flight price','india airfare','flight fare','flight price round trip','Indian domestic flights']
    jobs=[('kaggle_search_'+str(i),'https://www.kaggle.com/api/v1/datasets/list?'+urllib.parse.urlencode({'search':q,'pageSize':30})) for i,q in enumerate(queries)]
    jobs += [('hf_search_'+str(i),'https://huggingface.co/api/datasets?'+urllib.parse.urlencode({'search':q,'limit':30,'full':'true'})) for i,q in enumerate(['flight price','Indian','airfare'])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for name,data in pool.map(fetch,jobs): print(json.dumps({'name':name,'results':data},ensure_ascii=True))
    print(json.dumps({'environment':{'python':os.sys.version,'cpu_count':os.cpu_count(),'disk_free_bytes':shutil.disk_usage(ROOT).free,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}}))
