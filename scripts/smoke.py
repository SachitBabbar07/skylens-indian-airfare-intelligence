"""Read-only HTTP integration: every exposed profile and compiled frontend assets."""
from pathlib import Path
import argparse
import httpx,json,re
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=ROOT/'reports/http_integration_results.json')
output=parser.parse_args().output
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
    health=client.get('/health');health.raise_for_status()
    page=client.get('/');page.raise_for_status();assert 'SkyLens' in page.text
    assets=re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"',page.text)
    for asset in assets:assert client.get(asset).status_code==200
    opts=client.get('/supported-options',params={'model_id':'cabin_2023'}).json();failures=[]
    for c in opts['combinations']:
        body={k:c[k] for k in ['origin','destination','airline','cabin_class','stops']}
        body.update(model_id='cabin_2023',days_left=int(c['lead_min']),duration_minutes=float(c['duration_min']),departure_hour=float(c['hour_min']),research_acknowledged=True)
        r=client.post('/predict',json=body)
        if r.status_code!=200:failures.append({'profile':body,'status':r.status_code,'detail':r.text})
    result={'health_status':health.status_code,'frontend_status':page.status_code,'compiled_assets_checked':len(assets),'profiles_checked':len(opts['combinations']),'failures':failures,'browser_visual_qa':'Not performed: browser permission declined'}
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    assert not failures
