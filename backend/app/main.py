"""Local research application. Startup only loads existing artifacts."""
from contextlib import asynccontextmanager
from pathlib import Path
import logging,os
from fastapi import FastAPI,HTTPException,Query,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.schemas import PredictionRequest,PredictionResponse,ExplanationResponse
from backend.app.services import ModelStore
from backend.app.capabilities import router as capability_router
from backend.app.acquisition import router as acquisition_router
from backend.app.evidence import historical_evidence
from skylens.prepare import ROOT
LOG=logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    app.state.store=ModelStore()
    try:
        app.state.evidence=historical_evidence(ROOT)
    except HTTPException as exc:
        LOG.warning('%s', exc.detail)
        app.state.evidence=None
    logging.getLogger('uvicorn.error').info('Research startup: %d models loaded; %d model artifacts unavailable',
             len(app.state.store.models),len(app.state.store.errors))
    yield

app=FastAPI(title='SkyLens · Historical Fare Research',version='0.1.0',lifespan=lifespan,description='Research only. No verified current INR total-fare or round-trip predictor qualified from the audited data.')
origins=[value.strip() for value in os.getenv('SKYLENS_CORS_ORIGINS','http://127.0.0.1:5173,http://localhost:5173').split(',') if value.strip()]
if '*' in origins:
    raise RuntimeError('SKYLENS_CORS_ORIGINS requires explicit origins; wildcard access is unsupported.')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type'])
app.add_middleware(GZipMiddleware,minimum_size=1024,compresslevel=4)
app.include_router(capability_router)
app.include_router(acquisition_router)

def store(request):return request.app.state.store

@app.exception_handler(Exception)
async def unexpected(request:Request,exc:Exception):
    LOG.error('Unexpected request failure on %s', request.scope.get('route').path if request.scope.get('route') else 'unmatched route',exc_info=exc)
    return JSONResponse(status_code=500,content={'detail':'The request could not be completed. Check local server logs or try again.'})

@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc:RequestValidationError):
    # Report fields and reasons without echoing payloads or non-JSON numbers.
    return JSONResponse(status_code=422,content={'detail':[
        {key: error[key] for key in ('loc','msg','type')} for error in exc.errors()]})

@app.get('/health')
def health(request:Request):
    s=store(request);ready=len(s.models)==2 and not s.airports.empty
    return JSONResponse(status_code=200 if ready else 503,content={'status':'ok' if ready else 'degraded','models_loaded':list(s.models),'research_only':True,'production_predictor_available':False})

@app.get('/model-info')
def model_info(request:Request):return {'models':[b['meta'] for b in store(request).models.values()],'unavailable_models':store(request).errors}

@app.get('/supported-options')
def options(request:Request,model_id:str='cabin_2023'):return store(request).options(model_id)

@app.get('/airports')
def airports(request:Request,query:str=Query('',max_length=100),model_id:str='cabin_2023',supported_only:bool=True):
    s=store(request)
    if s.airports.empty:raise HTTPException(503,'Airport directory is unavailable. Restore the coverage report and retry.')
    bundle=s.get(model_id) if supported_only else s.models.get(model_id)
    a=s.airports.copy()
    eligible=set(bundle['support'].origin)|set(bundle['support'].destination) if bundle else set()
    a['research_eligible']=a.iata_code.isin(eligible)
    trained=set(bundle['meta']['training_airports']) if bundle else set()
    a['in_selected_model_training']=a.iata_code.isin(trained)
    a['serving_status']='no_selected_fare_evidence'
    a.loc[a.fare_endpoint_observations.gt(0),'serving_status']='fare_evidence_other_cohort'
    a.loc[a.in_selected_model_training,'serving_status']='insufficient_profile_support'
    if bundle is None:
        a.loc[a.fare_endpoint_observations.gt(0),'serving_status']='model_unavailable'
    a.loc[a.research_eligible,'serving_status']='eligible_research_profile'
    a.loc[a.iata_code.eq(''),'serving_status']='no_iata_code'
    if supported_only:a=a[a.research_eligible]
    if query:
        mask=a[['iata_code','name','municipality']].astype(str).apply(lambda col:col.str.contains(query,case=False,regex=False)).any(axis=1);a=a[mask]
    return {'airports':a.to_dict('records'),'total':len(a),'source':'OurAirports (public domain); scheduled-service flag is not a current operating guarantee.'}

@app.get('/research/evidence',tags=['Historical coverage'])
def evidence(request:Request):
    if request.app.state.evidence is None:
        raise HTTPException(503,'Historical route evidence is unavailable. Restore the coverage reports and retry.')
    return request.app.state.evidence

@app.get('/airlines')
def airlines(request:Request,model_id:str='cabin_2023'):return {'airlines':store(request).options(model_id)['airlines'],'historical_only':True}

@app.get('/fare-semantics')
def fare_semantics(request:Request,model_id:str='cabin_2023'):
    import json
    bundle=store(request).get(model_id)
    path=ROOT/'data/metadata/phase2/fare_semantics.json'
    evidence=json.loads(path.read_text(encoding='utf-8')).get(model_id,{}) if path.exists() else {}
    return {'model_id':model_id,'currency':bundle['meta']['currency'],
            'price_scope':bundle['meta']['price_scope'],
            'passenger_basis':bundle['meta']['passenger_basis'],
            'research_only':True,'evidence':evidence,
            'interval_status':'withheld_unvalidated_serving_domain'}

@app.get('/coverage')
def coverage(request:Request):
    import json
    s=store(request)
    counts=json.loads((ROOT/'data/metadata/coverage_counts.json').read_text())
    for name,b in s.models.items():
        support=b['support']
        counts[name]={'eligible_research_airports':len(set(support.origin)|set(support.destination)),
                      'eligible_research_routes':len(support[['origin','destination']].drop_duplicates()),
                      'eligible_combinations':len(support)}
    return {'counts':counts,'production_eligible_airports':0,'note':'Airport metadata, observed fares, research eligibility and reliable current fares are distinct.'}

@app.get('/route-coverage')
def route_coverage(request:Request,model_id:str='cabin_2023',origin:str|None=None,destination:str|None=None):
    s=store(request).get(model_id)['support']
    if origin:s=s[s.origin.eq(origin)]
    if destination:s=s[s.destination.eq(destination)]
    return {'combinations':s.to_dict('records'),'minimum_training_observations':50,'coverage_status':'research_only'}

@app.post('/research/predict',response_model=PredictionResponse,tags=['Unverified research outputs'],description='Raw model output in unverified source units. Not an airfare estimate, INR amount or booking quote.')
def predict(payload:PredictionRequest,request:Request):return store(request).predict(payload)

@app.post('/research/explain',response_model=ExplanationResponse,tags=['Unverified research outputs'],description='SHAP research contributions in unverified model-output units, not rupee impacts.')
def explain(payload:PredictionRequest,request:Request):return store(request).explain(payload)

@app.get('/feature-importance')
def importance(request:Request,model_id:str='cabin_2023'):
    return {'method':'Mean absolute SHAP over a fixed sample of final-test observations','unit':'source fare units','unit_verification':'unverified','currency':None,'interpretation':'Research contributions in unverified model-output units, not rupee impacts.','features':store(request).get(model_id)['importance']}

web=ROOT/'frontend/dist'
if web.is_dir():app.mount('/',StaticFiles(directory=web,html=True),name='frontend')
