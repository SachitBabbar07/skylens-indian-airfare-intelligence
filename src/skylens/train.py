"""Temporal model selection, separate calibration, untouched final test, and stress tests."""
from pathlib import Path
import hashlib, json, logging, math, time
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score,median_absolute_error,mean_absolute_percentage_error
from skylens.prepare import ROOT
from skylens.features import CATEGORICAL,NUMERIC,FEATURES,feature_frame
SEED=42
logging.basicConfig(level=logging.INFO,format='%(message)s')

def metrics(y,p):
    err=np.abs(np.asarray(y)-np.asarray(p))
    return {'n':len(y),'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p)) if len(y)>1 else None,'median_absolute_error':float(median_absolute_error(y,p)),'mape_percent':float(mean_absolute_percentage_error(y,p)*100),'p90_absolute_error':float(np.quantile(err,.9))}

def cb(params):
    return CatBoostRegressor(**params,loss_function='MAE',random_seed=SEED,thread_count=8,verbose=False,allow_writing_files=False)

def temporal_split(df,cohort):
    col='travel_date' if cohort=='cabin_2023' else 'collection_date'
    dates=sorted(df[col].dt.normalize().unique());n=len(dates)
    if cohort=='network_2020':
        if n!=3:raise ValueError('Network collection-day protocol requires review after data changes')
        cuts=[dates[1],dates[1],dates[2]]
        middle=df[col].eq(dates[1]); validation_group=df.quote_group.astype('uint64').mod(2).eq(0)
        split=np.select([df[col].eq(dates[0]),middle & validation_group,middle & ~validation_group],['train','validation','calibration'],default='test')
    else:
        if n<10:raise ValueError('Insufficient distinct travel dates for temporal evaluation')
        cuts=[dates[int(n*.6)],dates[int(n*.7)],dates[int(n*.8)]]
        split=np.select([df[col]<cuts[0],df[col]<cuts[1],df[col]<cuts[2]],['train','validation','calibration'],default='test')
    df=df.assign(split=split)
    # Keep a quote in one split: remove its earlier appearances, preserving chronology.
    later=set();purged=[]
    for label in ['test','calibration','validation','train']:
        idx=df.index[df.split.eq(label)]
        remove=df.loc[idx,'quote_group'].isin(later)
        ridx=idx[remove];purged.extend(ridx.tolist());df.loc[ridx,'split']='purged_quote_overlap'
        later.update(df.loc[idx,'quote_group'])
    return df,{'date_column':col,'boundaries':[str(pd.Timestamp(x).date()) for x in cuts],'purged_rows':len(purged)}

def subgroups(df,p,q):
    work=df.copy();work['prediction']=p;work['lower']=np.maximum(0,p-q);work['upper']=p+q
    work['booking_window']=pd.cut(work.days_left,[-1,7,14,30,90,10000],labels=['0-7','8-14','15-30','31-90','91+']).astype(str)
    work['price_range']=pd.cut(work.price,[-1,5000,10000,25000,50000,np.inf]).astype(str)
    work['duration_band']=pd.cut(work.duration_minutes,[0,120,240,480,1440,np.inf]).astype(str)
    records=[]
    for col in ['origin','destination','route','airline','cabin_class','journey_type','booking_window','price_range','stops','duration_band']:
        for value,part in work.groupby(col):
            item={'group_type':col,'group':str(value),**metrics(part.price,part.prediction),'interval_coverage':float(((part.price>=part.lower)&(part.price<=part.upper)).mean()),'mean_interval_width':float((part.upper-part.lower).mean())}
            records.append(item)
    return pd.DataFrame(records),work

def stress_evaluations(dev,params):
    rows=[];x=feature_frame(dev);y=dev.price
    def fit_eval(name,tr,te,extra):
        if len(tr)<100 or len(te)<20:return
        model=cb({**params,'iterations':min(params['iterations'],250)})
        model.fit(x.loc[tr],y.loc[tr],cat_features=CATEGORICAL)
        rows.append({'protocol':name,**extra,**metrics(y.loc[te],model.predict(x.loc[te])),'training_rows':len(tr),'iterations':min(params['iterations'],250)})
    tr,te=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=SEED).split(dev,groups=dev.quote_group))
    fit_eval('random_quote_group_holdout',dev.index[tr],dev.index[te],{})
    # Multiple route folds; all endpoint airports must occur in the training portion.
    routes=sorted(dev.route.unique());rng=np.random.default_rng(SEED);rng.shuffle(routes)
    for i,held in enumerate(np.array_split(routes,3)):
        te=dev.index[dev.route.isin(held)];tr=dev.index[~dev.route.isin(held)]
        known=set(dev.loc[tr,'origin'])|set(dev.loc[tr,'destination'])
        te=te[dev.loc[te,'origin'].isin(known)&dev.loc[te,'destination'].isin(known)]
        fit_eval('route_holdout_known_airports',tr,te,{'fold':i,'held_routes':len(held)})
    # Remove every row touching each chosen airport from training, in both directions.
    counts=pd.concat([dev.origin,dev.destination]).value_counts()
    selected=counts.index.tolist() if len(counts)<=7 else [counts.index[0],counts.index[len(counts)//2],counts.index[-1]]
    for airport in selected:
        mask=dev.origin.eq(airport)|dev.destination.eq(airport)
        fit_eval('unseen_airport_holdout',dev.index[~mask],dev.index[mask],{'held_airport':airport})
    return rows

def train_one(cohort):
    logging.info('Training %s',cohort);started=time.time()
    df=pd.read_parquet(ROOT/f'data/processed/{cohort}.parquet')
    # Rare labels stay in the data audit but cannot become a supported prediction class.
    cabin_counts=df.cabin_class.value_counts();rare=set(cabin_counts[cabin_counts<500].index)
    excluded=df[df.cabin_class.isin(rare)].copy();df=df[~df.cabin_class.isin(rare)].copy()
    excluded[['source_record_id','cabin_class']].to_csv(ROOT/f'reports/{cohort}_rare_class_exclusions.csv',index=False)
    df,protocol=temporal_split(df,cohort)
    df[['source_record_id','fingerprint','quote_group','travel_date','collection_date','split']].to_parquet(ROOT/f'data/processed/{cohort}_splits.parquet',index=False)
    parts={s:df[df.split.eq(s)] for s in ['train','validation','calibration','test']}
    assert all(len(v)>30 for v in parts.values()), {k:len(v) for k,v in parts.items()}
    for i,left in enumerate(parts):
        for right in list(parts)[i+1:]:
            assert set(parts[left].quote_group).isdisjoint(parts[right].quote_group)
            assert set(parts[left].fingerprint).isdisjoint(parts[right].fingerprint)
    tr,va=parts['train'],parts['validation'];xtr,xva=feature_frame(tr),feature_frame(va)
    prep=lambda:ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),CATEGORICAL),('num',StandardScaler(),NUMERIC)])
    specs=[('Mean',make_pipeline(prep(),DummyRegressor(strategy='mean'))),('Median',make_pipeline(prep(),DummyRegressor(strategy='median'))),('Ridge',make_pipeline(prep(),Ridge(alpha=10))),('DecisionTree',make_pipeline(prep(),DecisionTreeRegressor(max_depth=12,min_samples_leaf=20,random_state=SEED)))]
    trials=[{'iterations':300,'depth':6,'learning_rate':.08,'l2_leaf_reg':3},{'iterations':400,'depth':8,'learning_rate':.06,'l2_leaf_reg':5},{'iterations':550,'depth':7,'learning_rate':.07,'l2_leaf_reg':7}]
    experiments=[]
    for name,model in specs+[(f'CatBoost_{i}',cb(p)) for i,p in enumerate(trials)]:
        t=time.perf_counter()
        if name.startswith('CatBoost'):model.fit(xtr,tr.price,cat_features=CATEGORICAL)
        else:model.fit(xtr,tr.price)
        train_s=time.perf_counter()-t;t=time.perf_counter();pred=model.predict(xva);infer=time.perf_counter()-t
        row={'cohort':cohort,'model':name,'protocol':'temporal_validation','training_rows':len(tr),'training_seconds':train_s,'inference_ms_per_row':infer*1000/len(va),**metrics(va.price,pred)}
        experiments.append(row);logging.info('%s %s MAE %.2f',cohort,name,row['mae'])
    table=pd.DataFrame(experiments);table.to_csv(ROOT/f'reports/{cohort}_model_comparison.csv',index=False)
    # Select the best measured CatBoost for native additive explanations; compare its gap to all baselines.
    best=min([r for r in experiments if r['model'].startswith('CatBoost')],key=lambda r:r['mae'])
    overall=min(experiments,key=lambda r:r['mae'])
    if best['mae']>overall['mae']*1.05:raise RuntimeError('Tree ensemble materially worse than simpler model; revisit selection')
    params=trials[int(best['model'].split('_')[-1])]
    dev=pd.concat([tr,va]);final=cb(params);t=time.perf_counter();final.fit(feature_frame(dev),dev.price,cat_features=CATEGORICAL);fit_seconds=time.perf_counter()-t
    model_dir=ROOT/'models'/cohort;model_dir.mkdir(exist_ok=True);model_path=model_dir/'model.cbm';final.save_model(str(model_path))
    # Calibration data never participate in fitting or model selection.
    cal=parts['calibration'];cal_pred=final.predict(feature_frame(cal));resid=np.abs(cal.price.to_numpy()-cal_pred)
    alpha=.1;level=min(1,math.ceil((len(resid)+1)*(1-alpha))/len(resid));q=float(np.quantile(resid,level,method='higher'))
    test=parts['test'];t=time.perf_counter();pred=final.predict(feature_frame(test));latency=time.perf_counter()-t
    overall_test=metrics(test.price,pred);overall_test['inference_ms_per_row']=latency*1000/len(test)
    subgroup,test_output=subgroups(test,pred,q);subgroup.to_csv(ROOT/f'reports/{cohort}_subgroup_metrics.csv',index=False)
    test_output.to_parquet(ROOT/f'reports/{cohort}_test_predictions.parquet',index=False)
    interval={'method':'split-calibration absolute residual quantile','nominal_coverage':.9,'residual_quantile':q,'calibration_rows':len(cal),'test_coverage':float(((test.price>=np.maximum(0,pred-q))&(test.price<=pred+q)).mean()),'mean_test_width':float((pred+q-np.maximum(0,pred-q)).mean()),'guarantee':'No distribution-free guarantee under temporal shift; historical empirical evaluation only.'}
    sample=test.sample(n=min(400,len(test)),random_state=SEED)
    shap=final.get_feature_importance(Pool(feature_frame(sample),cat_features=CATEGORICAL),type='ShapValues')
    shap_pred=final.predict(feature_frame(sample));assert np.allclose(shap[:,:-1].sum(axis=1)+shap[:,-1],shap_pred,atol=1e-6)
    importance=pd.DataFrame({'feature':FEATURES,'mean_absolute_shap':np.abs(shap[:,:-1]).mean(axis=0)}).sort_values('mean_absolute_shap',ascending=False)
    importance.to_csv(model_dir/'feature_importance.csv',index=False)
    example={'inputs':sample.iloc[0][FEATURES].to_dict(),'prediction':float(shap_pred[0]),'baseline':float(shap[0,-1]),'contributions':dict(zip(FEATURES,shap[0,:-1].tolist()))}
    (model_dir/'explanation_example.json').write_text(json.dumps(example,indent=2),encoding='utf-8')
    # Permutation on validation with the selection-fit model, never the final holdout.
    selection=cb(params);selection.fit(xtr,tr.price,cat_features=CATEGORICAL)
    perm_sample=va.sample(n=min(2500,len(va)),random_state=SEED);px=feature_frame(perm_sample);base=mean_absolute_error(perm_sample.price,selection.predict(px));rng=np.random.default_rng(SEED)
    permutation=[]
    for col in FEATURES:
        shuffled=px.copy();shuffled[col]=rng.permutation(shuffled[col].to_numpy());permutation.append({'feature':col,'mae_increase':float(mean_absolute_error(perm_sample.price,selection.predict(shuffled))-base)})
    pd.DataFrame(permutation).to_csv(ROOT/f'reports/{cohort}_permutation_importance.csv',index=False)
    logging.info('%s running development-only generalization stress tests',cohort)
    stress=stress_evaluations(dev,params)
    pd.DataFrame(stress).to_csv(ROOT/f'reports/{cohort}_generalization.csv',index=False)
    # Prediction support comes only from model-fitting rows, with conservative joint support.
    keys=['origin','destination','airline','cabin_class','stops']
    groups=dev.groupby(keys).agg(n=('price','size'),duration_min=('duration_minutes','min'),duration_max=('duration_minutes','max'),lead_min=('days_left','min'),lead_max=('days_left','max'),hour_min=('departure_hour','min'),hour_max=('departure_hour','max')).reset_index()
    groups['eligible']=groups.n.ge(50);groups.to_csv(model_dir/'support.csv',index=False)
    vocab={col:sorted(dev[col].unique().tolist()) for col in CATEGORICAL}
    meta={'id':cohort,'version':'0.1.0','research_only':True,'production_ready':False,'name':'Cabin research · 2023' if cohort=='cabin_2023' else 'Network research · 2020','target':'Source-recorded fare; currency, tax inclusion and passenger basis not independently verified','currency':None,'unit':'source fare units','journey_types':['single_direction_record'],'price_scope':'unknown','passenger_basis':'unknown','source_datasets':sorted(df.source_dataset.unique().tolist()),'processed_sha256':hashlib.sha256((ROOT/f'data/processed/{cohort}.parquet').read_bytes()).hexdigest(),'artifact_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'trained_at_utc':pd.Timestamp.now(tz='UTC').isoformat(),'random_seed':SEED,'features':FEATURES,'categorical_features':CATEGORICAL,'hyperparameters':params,'selected_model':best['model'],'best_baseline':overall['model'],'selection_mae':best['mae'],'training_seconds':fit_seconds,'total_experiment_seconds':time.time()-started,'split_protocol':protocol,'split_sizes':{k:len(v) for k,v in parts.items()},'rare_classes_excluded':sorted(rare),'vocabulary':vocab,'training_airports':sorted(set(dev.origin)|set(dev.destination)),'training_routes':sorted(dev.route.unique().tolist()),'data_travel_dates':[str(df.travel_date.min().date()),str(df.travel_date.max().date())],'data_collection_dates':[str(df.collection_date.min().date()),str(df.collection_date.max().date())],'test_metrics':overall_test,'interval':interval,'generalization':stress,'limits':['Research use only: source price scope and currency are undocumented.','Single-direction rows do not prove a genuine one-way booking.','No round-trip or multi-city fare evidence qualified for training.','Historical carriers and airport mappings do not imply current services.','New airports and unobserved routes are blocked.','One collection day in the cabin cohort confounds lead time and departure date.' if cohort=='cabin_2023' else 'Sparse airport/route cells and 2020 market conditions limit reliability.']}
    (model_dir/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    logging.info('%s final test MAE %.2f; empirical interval coverage %.3f; total %.1fs',cohort,overall_test['mae'],interval['test_coverage'],time.time()-started)
    return meta

def main():
    results=[train_one(name) for name in ['network_2020','cabin_2023']]
    pd.concat([pd.read_csv(ROOT/f'reports/{m["id"]}_model_comparison.csv') for m in results]).to_csv(ROOT/'reports/model_comparison.csv',index=False)
    # Pandemic-era external challenge, same source family. Not claimed independent or target-compatible.
    ext=pd.read_parquet(ROOT/'data/processed/network_external_2020.parquet');m=CatBoostRegressor();m.load_model(str(ROOT/'models/network_2020/model.cbm'))
    train=pd.read_parquet(ROOT/'data/processed/network_2020.parquet');contamination=int(ext.fingerprint.isin(train.fingerprint).sum());ext=ext[~ext.fingerprint.isin(train.fingerprint)]
    ext['prediction']=m.predict(feature_frame(ext));ext.to_parquet(ROOT/'reports/external_predictions.parquet',index=False)
    (ROOT/'reports/external_metrics.json').write_text(json.dumps({'label':'Research drift challenge only; same collector, unknown target scope and currency','removed_exact_overlap':contamination,**metrics(ext.price,ext.prediction)},indent=2))
if __name__=='__main__':main()
