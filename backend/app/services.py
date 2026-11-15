"""Read-only native CatBoost artifacts, verified on load; never train in a request."""
from pathlib import Path
import hashlib,json,logging,math
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor,Pool
from fastapi import HTTPException
from skylens.prepare import ROOT
from skylens.features import feature_frame,FEATURES,CATEGORICAL
from backend.app.schemas import PredictionRequest
LOG=logging.getLogger(__name__)

class ModelStore:
    def __init__(self,root:Path=ROOT):
        self.root=root;self.models={};self.errors={}
        try:self.airports=pd.read_csv(root/'reports/airport_fare_coverage.csv',keep_default_na=False)
        except Exception:self.airports=pd.DataFrame()
        for name in ['cabin_2023','network_2020']:
            try:
                folder=root/'models'/name;meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
                if meta['id']!=name:raise ValueError('Model identity mismatch')
                if hashlib.sha256((folder/'model.cbm').read_bytes()).hexdigest()!=meta['artifact_sha256']:raise ValueError('Artifact integrity check failed')
                model=CatBoostRegressor();model.load_model(str(folder/'model.cbm'))
                if list(model.feature_names_)!=FEATURES:raise ValueError('Feature schema mismatch')
                support=pd.read_csv(folder/'support.csv');support=support[support.eligible.eq(True)]
                importance=pd.read_csv(folder/'feature_importance.csv').to_dict('records')
                groups=pd.read_csv(root/f'reports/{name}_subgroup_metrics.csv')
                self.models[name]={'model':model,'meta':meta,'support':support,'importance':importance,'groups':groups}
            except Exception as e:
                LOG.warning('Model %s unavailable: %s',name,type(e).__name__);self.errors[name]='Model artifacts are unavailable or failed integrity checks.'
    def get(self,name):
        if name not in self.models:raise HTTPException(503,'This model is unavailable. Rebuild or restore the verified artifacts.')
        return self.models[name]
    def options(self,name):
        bundle=self.get(name);s=bundle['support'];meta=bundle['meta']
        records=s.replace({np.nan:None}).to_dict('records')
        return {'model_id':name,'name':meta['name'],'research_only':True,'journey_types':meta['journey_types'],'classes':sorted(s.cabin_class.unique()),'airlines':sorted(s.airline.unique()),'airports':sorted(set(s.origin)|set(s.destination)),'combinations':records,'target':meta['target'],'unit':meta['unit'],'limits':meta['limits'],'travel_date_input_supported':False,'reason_no_travel_date':'The model does not support current or future calendar-date prices. Enter historical lead time instead.'}
    def frame(self,request:PredictionRequest):
        bundle=self.get(request.model_id);s=bundle['support'];meta=bundle['meta']
        if self.airports.empty:raise HTTPException(503,'Airport metadata is unavailable.')
        codes=set(self.airports.iata_code)-{''}
        for code in [request.origin,request.destination]:
            if code not in codes:raise HTTPException(422,f'{code} is not a known Indian IATA airport in this snapshot.')
            if code not in meta['training_airports']:raise HTTPException(422,f'{code} has no training observations for the selected research model.')
        for column,value in [('airline',request.airline),('cabin_class',request.cabin_class)]:
            if value not in meta['vocabulary'][column]:raise HTTPException(422,f'The selected {column.replace("_"," ")} is unsupported by this model.')
        match=s[(s.origin==request.origin)&(s.destination==request.destination)&(s.airline==request.airline)&(s.cabin_class==request.cabin_class)&(s.stops==request.stops)]
        if len(match)!=1:raise HTTPException(422,'This route, airline, cabin and stops combination has insufficient training evidence (minimum 50 observations).')
        support=match.iloc[0]
        normalized = {}
        for field,low,high in [('duration_minutes','duration_min','duration_max'),('days_left','lead_min','lead_max'),('departure_hour','hour_min','hour_max')]:
            value=getattr(request,field)
            lower, upper = float(support[low]), float(support[high])
            # CSV and HH:mm conversion may encode the same minute with different
            # binary floats. 1e-9 hour is 3.6 microseconds, far below source precision.
            tolerance = 1e-9 if field == 'departure_hour' else 0
            if not lower-tolerance<=value<=upper+tolerance:raise HTTPException(422,f'{field.replace("_"," ")} must be within this historical combination\'s observed range: {support[low]:g}–{support[high]:g}.')
            normalized[field] = min(max(value, lower), upper)
        row=request.model_dump();row.update(normalized);ref=self.airports.set_index('iata_code')
        for end in ['origin','destination']:
            row[end+'_lat']=float(ref.loc[row[end],'latitude_deg']);row[end+'_lon']=float(ref.loc[row[end],'longitude_deg'])
        lat1,lat2=np.radians(row['origin_lat']),np.radians(row['destination_lat']);dl=np.radians(row['destination_lon']-row['origin_lon'])
        row['distance_km']=float(6371*2*np.arcsin(np.sqrt(np.clip(np.sin((lat2-lat1)/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dl/2)**2,0,1))))
        return bundle,feature_frame(pd.DataFrame([row])),int(support['n'])
    def predict(self,request):
        bundle,x,n=self.frame(request);meta=bundle['meta'];pred=float(bundle['model'].predict(x)[0])
        if not math.isfinite(pred) or pred<=0:raise HTTPException(503,'The model could not produce a valid research estimate for these inputs.')
        # Phase-two audit: calibration/test lead windows do not validate the
        # accepted cabin serving domain. Preserve offline intervals in metadata,
        # but do not imply their coverage applies to an accepted request.
        return {'model_id':request.model_id,'model_version':meta['version'],'estimate':pred,'unit':meta['unit'],'currency':None,'price_scope':'unknown','passenger_basis':'unknown','research_only':True,'coverage_status':'experimental_historical_route','historical_support':n,'interval':None,'interval_status':'withheld_unvalidated_serving_domain','warnings':['Historical machine-learning estimate. This is not a live airline quote or guaranteed booking price.','Currency, tax inclusion, passenger basis and booking journey type are not verified. Values remain source fare units.','This research model cannot provide a verified INR total, round-trip fare, or current-date quote.','Prediction interval withheld: the offline holdout does not validate the currently accepted input domain.'],'inputs':request.model_dump(exclude={'research_acknowledged'})}
    def explain(self,request):
        bundle,x,n=self.frame(request)
        shap=bundle['model'].get_feature_importance(Pool(x,cat_features=CATEGORICAL),type='ShapValues')[0];pred=float(bundle['model'].predict(x)[0]);baseline=float(shap[-1])
        contributions=[{'feature':f,'value':x.iloc[0][f].item() if isinstance(x.iloc[0][f],np.generic) else x.iloc[0][f],'contribution':float(shap[i])} for i,f in enumerate(FEATURES)]
        return {'estimate':pred,'baseline':baseline,'contributions':sorted(contributions,key=lambda v:abs(v['contribution']),reverse=True),'additive_error':float(abs(baseline+sum(c['contribution'] for c in contributions)-pred)),'unit':'source fare units','interpretation':'SHAP assigns each input a contribution relative to the model baseline. Positive values raise this output; negative values lower it. These are model associations, not causal effects.'}
