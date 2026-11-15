"""Tests use real downloaded observations except isolated malformed-input fixtures."""
import json,hashlib,shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from skylens.prepare import ROOT,duration_minutes
from backend.app.main import app
from backend.app.services import ModelStore

@pytest.fixture(scope='module')
def client():
    with TestClient(app,raise_server_exceptions=False) as c:yield c

def payload(client,model='cabin_2023'):
    opts=client.get('/supported-options',params={'model_id':model}).json()
    c=opts['combinations'][0]
    return {'model_id':model,'origin':c['origin'],'destination':c['destination'],'airline':c['airline'],'cabin_class':c['cabin_class'],'stops':int(c['stops']),'duration_minutes':float(c['duration_min']),'days_left':int(c['lead_min']),'departure_hour':float(c['hour_min']),'research_acknowledged':True}

@pytest.mark.parametrize('model',['network_2020','cabin_2023'])
def test_real_prediction_and_additive_explanation(client,model):
    if model=='network_2020':
        opts=client.get('/supported-options',params={'model_id':model}).json()
        assert opts['combinations']==[]  # no exact profile reaches the unchanged support threshold
        from skylens.features import feature_frame,CATEGORICAL
        from catboost import Pool
        d=pd.read_parquet(ROOT/'data/processed/network_2020.parquet').head(1)
        bundle=app.state.store.get(model);x=feature_frame(d)
        pred=bundle['model'].predict(x);shap=bundle['model'].get_feature_importance(Pool(x,cat_features=CATEGORICAL),type='ShapValues')
        assert pred[0]>0 and shap[0].sum()==pytest.approx(pred[0])
        body=d.iloc[0].to_dict()
        req={k:body[k] for k in ['origin','destination','airline','cabin_class','stops','duration_minutes','days_left','departure_hour']}
        req.update(model_id=model,research_acknowledged=True)
        assert client.post('/predict',json=req).status_code==422
        return
    body=payload(client,model);r=client.post('/predict',json=body);assert r.status_code==200,r.text
    result=r.json();assert result['estimate']>0 and result['research_only'] and result['currency'] is None
    e=client.post('/explain',json=body);assert e.status_code==200,e.text
    explanation=e.json();assert explanation['estimate']==pytest.approx(result['estimate']);assert explanation['additive_error']<1e-6
    assert explanation['baseline']+sum(v['contribution'] for v in explanation['contributions'])==pytest.approx(result['estimate'])
    assert len(explanation['contributions'])==13

@pytest.mark.parametrize('field,value',[('origin','ZZZ'),('origin','VABB'),('origin','PNQ'),('airline','Unknown Airline'),('cabin_class','First'),('journey_type','round_trip'),('journey_type','multi_city'),('days_left',-1),('days_left',3.5),('duration_minutes',0),('stops',-1),('stops',8),('departure_hour',24),('research_acknowledged',False),('return_date','2026-12-01'),('passenger_count',2),('travel_date','invalid'),('unknown',True)])
def test_reject_invalid_or_unsupported(client,field,value):
    body=payload(client);body[field]=value
    r=client.post('/predict',json=body);assert r.status_code==422,r.text

@pytest.mark.parametrize('field',['origin','destination','duration_minutes','research_acknowledged'])
def test_missing_required(client,field):
    body=payload(client);del body[field];assert client.post('/predict',json=body).status_code==422

def test_same_airport(client):
    body=payload(client);body['destination']=body['origin'];assert client.post('/predict',json=body).status_code==422

def test_out_of_support_bounds(client):
    body=payload(client);body['duration_minutes']=4000;assert client.post('/predict',json=body).status_code==422

def test_malformed_json(client):assert client.post('/predict',content='{bad',headers={'Content-Type':'application/json'}).status_code==422

def test_api_metadata_and_search(client):
    assert client.get('/health').status_code==200
    for endpoint in ['/model-info','/coverage','/route-coverage','/airlines','/feature-importance']:assert client.get(endpoint).status_code==200
    all_records=client.get('/airports',params={'supported_only':False}).json()['airports'];assert len(all_records)==len(pd.read_csv(ROOT/'reports/india_airport_master.csv'))
    assert client.get('/airports',params={'query':'DEL'}).json()['total']>=1
    assert client.get('/airports',params={'query':'no such airport'}).json()['total']==0
    assert client.get('/supported-options',params={'model_id':'made_up'}).status_code==503

def test_network_unknown_class_stays_unspecified(client):
    meta=next(m for m in client.get('/model-info').json()['models'] if m['id']=='network_2020')
    assert meta['vocabulary']['cabin_class']==['Unspecified']
    assert client.get('/supported-options',params={'model_id':'network_2020'}).json()['classes']==[]

def test_model_unavailable(client):
    body=payload(client);s=app.state.store;old=s.models;s.models={}
    try:assert client.get('/health').status_code==503;assert client.post('/predict',json=body).status_code==503
    finally:s.models=old

def test_missing_and_corrupted_model(tmp_path):
    store=ModelStore(tmp_path);assert not store.models
    folder=tmp_path/'models/cabin_2023';folder.mkdir(parents=True);shutil.copy(ROOT/'models/cabin_2023/metadata.json',folder/'metadata.json');(folder/'model.cbm').write_bytes(b'corrupt fixture')
    assert 'cabin_2023' in ModelStore(tmp_path).errors

def test_internal_error_is_not_exposed(client,monkeypatch):
    body=payload(client)
    def fail(*args):raise RuntimeError('private-test-stack-details')
    monkeypatch.setattr(app.state.store,'predict',fail)
    r=client.post('/predict',json=body);assert r.status_code==500 and 'private-test-stack-details' not in r.text

@pytest.mark.parametrize('model',['network_2020','cabin_2023'])
def test_quote_and_observation_splits_disjoint(model):
    d=pd.read_parquet(ROOT/f'data/processed/{model}_splits.parquet');labels=['train','validation','calibration','test']
    for i,left in enumerate(labels):
        for right in labels[i+1:]:
            for column in ['fingerprint','quote_group']:assert set(d[d.split.eq(left)][column]).isdisjoint(d[d.split.eq(right)][column])
    meta=json.loads((ROOT/f'models/{model}/metadata.json').read_text());assert hashlib.sha256((ROOT/f'models/{model}/model.cbm').read_bytes()).hexdigest()==meta['artifact_sha256']

def test_unknown_price_scope_never_becomes_inr():
    for name in ['network_2020','network_external_2020','cabin_2023']:
        d=pd.read_parquet(ROOT/f'data/processed/{name}.parquet');assert d.currency.isna().all() and d.normalized_price_inr.isna().all();assert d.price_scope.eq('unknown').all();assert not d.fingerprint.duplicated().any();assert (d.price>0).all();assert not d.origin.eq(d.destination).any()

def test_real_exclusion_accounting_and_airport_keys():
    p=json.loads((ROOT/'data/metadata/cohort_profiles.json').read_text())
    for name,stats in p.items():assert stats['input_rows']==stats['retained_rows']+len(pd.read_csv(ROOT/f'data/interim/{name}_exclusions.csv'))
    a=pd.read_csv(ROOT/'reports/india_airport_master.csv');assert not a[a.iata_code.notna()].iata_code.duplicated().any()

@pytest.mark.parametrize('text,expected',[('02h 05m',125),('1h',60),('45m',45),('invalid',None)])
def test_duration_parser(text,expected):
    actual=duration_minutes(text)
    if expected is None:assert np.isnan(actual)
    else:assert actual==expected
