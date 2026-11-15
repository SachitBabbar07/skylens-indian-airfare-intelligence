"""Generate evidence reports, figures and learning guides from executed artifacts."""
import datetime,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from catboost import CatBoostRegressor,Pool
from skylens.prepare import ROOT
from skylens.features import feature_frame,CATEGORICAL,FEATURES
R=ROOT/'reports';D=ROOT/'docs';M=ROOT/'data/metadata'
def write(path,text):path.write_text(text.strip()+'\n',encoding='utf-8')
def table(df):
    safe=lambda v:str(v).replace('|','/').replace('\n',' ')
    rows=[[safe(v) for v in df.columns]]+[[safe(v) for v in row] for row in df.fillna('not verified').values]
    return '\n'.join(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(row)+' |' for row in rows[1:]])
profiles=json.loads((M/'cohort_profiles.json').read_text());counts=json.loads((M/'coverage_counts.json').read_text())
models={n:json.loads((ROOT/f'models/{n}/metadata.json').read_text()) for n in ['network_2020','cabin_2023']}
registry=json.loads((M/'dataset_registry.json').read_text());files=json.loads((M/'file_profiles.json').read_text())
for entry in registry:
    if entry.get('role') == 'audit_only_not_training':continue
    if 'error' in entry or entry['source']=='OurAirports':continue
    ref=entry['source'];folder=ref.replace('/','__') if ref.startswith('promptcloud/') else ref.split('/')[0]
    archive=ROOT/'data/raw'/folder/'original.zip'
    entry['retrieved_at_utc']=datetime.datetime.fromtimestamp(archive.stat().st_mtime,datetime.timezone.utc).isoformat()
    entry['file_profiles']=[f for f in files if f.get('path','').replace('\\','/').startswith('data/raw/'+folder+'/')]
    entry['transformation_history']='Original bytes preserved; see skylens.prepare, cohort_profiles.json and per-row exclusion ledgers.'
write(M/'dataset_registry.json',json.dumps(registry,indent=2))
b=pd.concat([pd.read_csv(ROOT/'data/raw/shubhambathwal/economy.csv'),pd.read_csv(ROOT/'data/raw/shubhambathwal/business.csv')],ignore_index=True)
g=pd.read_csv(ROOT/'data/raw/iamavyukt/goibibo_flights_data.csv');bp=b.price.str.replace(',','').astype(float);gp=g.price.str.replace(',','').astype(float)
overlap={'rows_compared':len(b),'same_order_flight_fraction':float(((b.ch_code+'-'+b.num_code.astype(str))==g.flight_num).mean()),'same_origin_fraction':float(b['from'].eq(g['from']).mean()),'same_destination_fraction':float(b.to.eq(g.to).mean()),'date_shift_days':(pd.to_datetime(g['flight date'],dayfirst=True)-pd.to_datetime(b.date,dayfirst=True)).dt.days.value_counts().to_dict(),'rounded_price_times_1_01_fraction':float(np.rint(bp*1.01).eq(gp).mean()),'exact_price_match_fraction':float(bp.eq(gp).mean())}
write(M/'source_overlap_audit.json',json.dumps(overlap,indent=2))
decisions={
'yashdharme36':('G',76,'Selected isolated cabin research; one collection day and unknown standardized target.'),
'promptcloud':('G',72,'Selected separate domestic research cohort or later drift challenge; missing class/price definitions.'),
'shubhambathwal':('G',61,'Reference only: fewer cities and weaker collection lineage; not appended to inflate records.'),
'iamavyukt':('G',0,'Rejected: derivative ordered flight records with 500-day date shift; not independent validation.'),
'shraddha4ever20':('G',0,'Rejected: collection authenticity unverified; pseudo airport codes and inconsistent clock/duration fields.'),
'andrewgeorgeissac':('G',35,'Separate base-fare sample explicitly excluding taxes; missing dates/class/passenger basis.'),
'sumitjaiswar':('E',0,'No price column; traffic/network sample with insufficient collection provenance.'),
'nikhilmittal':('G',0,'Not downloaded: original license unknown; a mirror does not resolve original rights.')}
candidates=[]
for p in sorted(M.glob('kaggle_*.json')):
    if p.name.startswith('kaggle_search'):continue
    meta=json.loads(p.read_text());ref=meta.get('ref');entry=next((x for x in registry if x.get('source')==ref),{});fp=entry.get('file_profiles',[])
    cat,score,decision=decisions.get(ref.split('/')[0],('G',0,'Unverified price scope/provenance; not selected.'))
    candidates.append({'source':ref,'category':cat,'url':'https://www.kaggle.com/datasets/'+ref,'author':meta.get('ownerName'),'updated':meta.get('lastUpdated'),'license':meta.get('licenseName'),'files_inspected':len(fp),'actual_file_rows':'; '.join(f"{Path(f['path']).name}: {f.get('rows','parse failed')}" for f in fp) or None,'subjective_score_100':score,'decision':decision})
extras=[('OurAirports','C','https://ourairports.com/data/','Public domain','Selected commit-pinned airport/region metadata, not fare evidence.'),('HF IndianDomesticAirlineDataset mirror family','G','https://huggingface.co/datasets/Kabil007/IndianDomesticAirlineDataset','Original unknown','Schedules only. THULab conversion says defer to unknown original rights. Not ingested.'),('India Cheap Flights index','F','https://indiacheapflights.com/press/','CC BY 4.0 stated','Aggregated usual fares/ranges, not individual quotes. Not ingested.'),('Piratefly fare history','F','https://huggingface.co/datasets/DeusHorizon/flight-fare-history','Custom Travelpayouts-derived terms','EUR aggregates with underlying redistribution restrictions. Not ingested.'),('ATL international return quotes','G','https://huggingface.co/datasets/egupta/atl-intl-flight-data-sql-db','MIT card','Genuine returns described, but ATL international; not Indian domestic. Advertised 3.85 GB not downloaded.'),('Vonter DGCA traffic','E','https://github.com/Vonter/india-aviation-traffic','ODbL 1.0','Passenger/freight network data, no quoted prices. Not ingested.'),('IIMA Dutta and Santra 2015','G','https://www.iima.ac.in/sites/default/files/rnpfiles/9959095172015-01-02.pdf','Raw reuse rights not found','2012 one-way minima described in paper; reusable raw supplement not located.'),('OpenSky Zenodo movement data','E','https://zenodo.org/records/7923702','See source LICENSE.txt','Aircraft movements, not fares; no download needed for target.'),('Avij112 fare analysis','G','https://github.com/Avij112/flight-fare-analysis','Not established for raw fares','Repository describes interpolation; interpolated prices excluded.'),('Dhairya Flights-Dataset','G','https://github.com/dhairya903/Flights-Dataset','No explicit data license found','Aertrip non-stop economy source, six airports claimed; not downloaded without clear reuse rights.'),('OpenFlights routes','E','https://openflights.org/data.php','ODbL/DbCL reported, unverified here','Historical routes, not prices. Not ingested.')]
candidates += [{'source':s,'category':c,'url':u,'license':l,'files_inspected':0 if c!='C' else 2,'decision':d} for s,c,u,l,d in extras]
comparison=pd.DataFrame(candidates);comparison.to_csv(R/'dataset_comparison.csv',index=False)
refs={}
for p in M.glob('kaggle_search_*.json'):
    for x in json.loads(p.read_text()):refs[x['ref']]={k:x.get(k) for k in ['ref','title','licenseName','lastUpdated','totalBytes']}
write(M/'discovered_catalog_inventory.json',json.dumps(list(refs.values()),indent=2))
write(R/'dataset_discovery_report.md',f'''# Dataset discovery
Research: 14–15 November 2026, Asia/Kolkata. This is a bounded search, not a claim to enumerate every possible dataset.

Kaggle's public catalog yielded {len(refs)} distinct references across Indian flight price, India airfare, flight fare, round trip and domestic-flight searches. Original cards/search snapshots are in data/metadata. Hugging Face broad searches were supplemented by specific schedule, fare-history and return-quote cards. Web searches also covered GitHub, Zenodo, Figshare, OpenML, government sources and academic studies. No additional qualified Indian domestic return-fare file was located; this does not prove none exists.

Eight original free public Kaggle source archives and a commit-pinned OurAirports snapshot were downloaded without credentials. dataset_registry.json and file_profiles.json contain actual byte sizes, hashes, rows, schemas, dtypes, missing counts and samples. No paid API, live booking-site scraping, authentication bypass or restricted download was used.

Important file findings:
- The 2023 cabin raw source has 452,088 rows, seven cities and four cabin labels. All booking dates are 15 January 2023: 50 departure days are not 50 collection days. First has only 144 rows and is excluded from modeling.
- The pre-pandemic PromptCloud sample has 30,024 rows, with 14,877 domestic records retained across 88 airports and 679 directional routes. It has only three collection days. The later sample actually has one collection day and departures 16–27 April, narrower than its advertised April–June range.
- The Goibibo file has {overlap['rows_compared']:,} identical ordered flight IDs versus the 2022 raw files, and every date shifts by 500 days. {overlap['rounded_price_times_1_01_fraction']:.4%} of prices equal rounded original × 1.01. It cannot establish independent 2023 validation.
- The broad 2019–2025 candidate uses route tokens such as MUM/PUN/BAN and inconsistent clock/duration fields without collection evidence. Authenticity is unverified; it is not asserted to be proven synthetic.

Selected sources have no verified currency, tax inclusion, passenger basis or booking journey type. They remain category G research datasets, with currency and normalized_price_inr missing. Single-direction rows are not automatically genuine one-way bookings. No reverse routes are combined into return fares. ATL international returns are out of scope. Schedule, airport, traffic and aggregate datasets are classified separately.

{table(comparison[['source','category','license','decision']])}

Mirrors and raw/cleaned representations are one source family. Inaccessible or unlicensed candidates remain unverified rather than silently used.''')
write(R/'dataset_selection_decision.md','''# Selection decision
No dataset qualified for a verified INR total-fare production target. This is a data-definition barrier, not a request for paid access.

Primary research: Yash Dharme's original 2023 raw EaseMyTrip file, reconciled against its cleaned representation. Separate supplementary research: PromptCloud pre-pandemic domestic records for geographic evaluation. Later same-collector PromptCloud data supply a distribution-shift challenge, not independent compatible validation. The 2022 source is a reference; the Goibibo derivative is excluded. MakeMyTrip tax-exclusive base fares stay separate. No price target is pooled across sources.

OurAirports supplies metadata only. No broad schedule source was ingested because the promising HF original has unknown licensing. A scheduled-service flag is community metadata, not a verified current timetable.

Subjective comparison weights: legality/provenance 40%, target/schema 25%, geographic evidence 20%, time/reproducibility 15%. Scores are documented judgments, not measured quality percentages. Hard gates dominate scores: unknown price scope blocks production, inconsistent lineage blocks training, and no price blocks fare modeling.

Only the cabin model has eligible serving profiles. The broader network's maximum exact training cell is 17, below the unchanged minimum 50. New routes/airports are blocked. First, confirmed one-way booking prices, round trips, multi-city, calendar-date forecasts and current INR totals remain unsupported. More legitimately licensed quotes with documented settings and repeated collection dates are required.''')
write(R/'dataset_licensing_and_provenance.md',f'''# Licensing and provenance
Original author cards and versioned URLs are saved. Publisher-declared licenses are not independent proof of rights in an upstream booking platform's content. Public access is not automatically unrestricted ML permission.

{table(comparison[['source','url','license','decision']])}

Selected research sources declare CC0. OurAirports states its data are public domain; its repository LICENSE is the Unlicense. The Goibibo file declares CC BY-NC-SA 4.0 but is rejected for independence. The MakeMyTrip sample declares CDLA Sharing 1.0 and is not merged or redistributed. The HF schedule original has unknown rights despite an MIT conversion tag. Current Piratefly terms are custom derived-data terms, superseding stale CC-BY catalog claims. No underlying-price sublicense is assumed.

Raw archives/extracts are ignored by Git. Before public/commercial deployment, verify upstream rights and target definitions. The deliverable is local research, not a legal clearance claim.

Acquisition correction: the initial owner-only PromptCloud folder caused archive-name ambiguity. Both sources were downloaded again to distinct owner__dataset folders with separate version URLs/hashes. Only these folders feed preparation. The initial folder remains untouched and excluded from modeling. Raw bytes were never edited; subsequent verification does not invent a new original retrieval time.''')
summary=pd.DataFrame([{'cohort':n,'input':p['input_rows'],'retained':p['retained_rows'],'excluded':p['excluded_rows'],'origins':p['origins'],'destinations':p['destinations'],'routes':p['routes']} for n,p in profiles.items()])
write(R/'data_audit_report.md',f'''# Data audit
{table(summary)}

Actual per-file schemas, dtypes, missing values, duplicates, hashes and samples are in data/metadata/file_profiles.json. Per-row exclusions in data/interim reconcile input = retained + excluded. International/unmapped endpoints/layovers are rejected; valid missing layover slots are not invented. Exact canonical duplicates are removed before splitting. Valid expensive fares remain. First's 144 rows stay in audit data but are excluded from training.

The 2023 raw/cleaned pair agrees on all recorded fares, departure dates and lead times. Its sole collection day prevents identifying independent booking-date and seasonal effects. Source 2+-stop remains a bucket represented as 2, not a claim of exactly two stops. Network carrier combinations retain original strings. Network cabin remains Unspecified.

All selected currencies, passenger bases and tax scopes remain unknown; normalized INR is entirely missing. Single-direction records do not establish genuine one-way booking settings. No return date is fabricated. Reviewed city aliases join unique nonempty Indian IATA codes, without fuzzy nearest-airport matching. Historical Goa maps to GOI and pre-2023 Rajkot to RAJ; no historical RAJ fare is silently moved to HSR. These mappings do not confirm current operations.''')
coverage=f'''# Airport and route coverage
{table(pd.DataFrame([{'concept':k,'actual_count':v} for k,v in counts.items()]))}

661 master records include heliports, closed and noncommercial airfields. They are not 661 passenger airports. The 120 scheduled flags come from OurAirports, not independent current-service verification. No separate schedule source is ingested. The master includes source commit/date, state, coordinates and status caveats; district information is unavailable and not invented.

The selected observations span 88 historical airports, 66 origins, 82 destinations and 720 directional routes across primary and later challenge cohorts. The pre-pandemic candidate alone has 679 routes; external-only data do not expand serving eligibility. There are 573 master records without selected fare evidence.

Cabin research: 592 eligible exact profiles across seven airports and 42 routes. Network: maximum exact training profile 17, so zero eligible profiles. Verified production-eligible airports: zero. The minimum 50 observations per route × airline × class × stops is a conservative research operational heuristic, not a reliability theorem. Observed numeric ranges also gate requests. It was not lowered after discovering sparsity. New airports and routes remain blocked despite coordinates.

See india_airport_master.csv, airport_fare_coverage.csv, route_fare_coverage.csv, data/metadata/city_airport_mapping.csv and models/COHORT/support.csv. Current passenger/commercial operations require authoritative independent evidence. Fare observations, metadata, schedule flags and supported predictions remain separate concepts.'''
for name in ['dataset_coverage_report.md','airport_coverage_analysis.md','airport_coverage_report.md','route_coverage_report.md']:write(R/name,coverage)
write(R/'leakage_audit.md',f'''# Leakage audit
The raw and cleaned files are representations, never stacked. The Goibibo derivative is excluded; source_overlap_audit.json contains the measured alignment. Canonical duplicates are removed before splits. Quote keys use endpoints, carrier/flight, class, travel date, departure hour, duration and stops, excluding price and collection timestamp. Earlier appearances of quotes present in later partitions are purged.

{table(pd.DataFrame([{'cohort':n,**m['split_sizes'],'purged_earlier_quotes':m['split_protocol']['purged_rows']} for n,m in models.items()]))}

All six partition pairs pass quote-group and exact-fingerprint disjointness assertions. Automated tests repeat these checks. The split manifests preserve source IDs and dates. Encoders/scalers live inside each training pipeline. Native CatBoost categorical statistics are fit only on the training portion. Geography is target-independent; target prices, IDs, source labels and post-flight outcomes are not features.

The final test does not choose parameters; calibration does not fit the model. Random, route and unseen-airport stress tests use development data only. Airport holdouts remove all rows touching the held airport in either direction. Route holdouts evaluate only endpoints still present in training. Native SHAP on test observations is post-selection analysis, not feature tuning.

Residual limitation: all cabin observations were collected on one day, linking lead time and travel date. Repeated flight numbers across different departure dates remain because familiar services are part of the intended research scenario. This does not establish unseen-flight generalization. The later PromptCloud challenge removes exact fingerprint overlap, but shared collector and unknown target definitions prevent a fully independent validation claim.''')
write(R/'feature_engineering_report.md',f'''# Feature engineering
Shared training/inference schema: {', '.join(FEATURES)}. See src/skylens/features.py.

Carrier, airport and class labels preserve source meaning. Network cabin stays Unspecified. Duration parses explicit hours/minutes; missing/invalid values are excluded rather than guessed. Lead time uses the actual booking day or crawl timestamp converted from UTC to Asia/Kolkata. Departure hour is a decimal local clock hour. Haversine distance uses pinned OurAirports coordinates and a 6,371 km Earth radius; it is a geographic approximation, not flown itinerary length.

Calendar-date/season/weekend features were not added because short periods and single-snapshot confounding cannot justify current-date forecasts. Fuel, holidays, demand, baggage and refundability are not invented. Targets, price statistics and quote IDs are excluded. Both source models remain isolated; pooling would mix unverified definitions. Cabin classes are pooled within their source for sufficient evidence, while First is excluded as sparse. Confirmed one-way/return architectures cannot be compared without verified journey labels.''')
results=pd.DataFrame([{'cohort':n,**m['test_metrics'],'interval_coverage':m['interval']['test_coverage']} for n,m in models.items()])
write(R/'model_evaluation_report.md',f'''# Model evaluation
{table(results.round(4))}

Error units are source fare units, not verified rupees. MAE averages absolute misses; RMSE emphasizes large errors; median absolute error shows a typical miss; MAPE applies only to positive prices; p90 absolute error exposes the error tail. R² is explained variance under this protocol, not accuracy.

Mean, median, Ridge, a depth-limited decision tree and three CatBoost settings share identical selection partitions. The fixed three-setting search is small and reproducible, not exhaustive optimization. model_comparison.csv records every validation score, training time and inference time. CatBoost is selected by validation MAE with a stop if a simpler baseline is materially better; native additive explanation availability also favors operational simplicity. Final fits use train+validation only. Saved metadata includes parameters, seed 42, training date, hashes and schema.

Network: earliest collection day trains; middle-day quote groups are deterministically split for validation/calibration; latest collection day is the final holdout. Cabin: first 60% departure days train, next 10% validation, next 10% calibration and last 20% final test, all from one collection snapshot. This is not future booking-day validation.

Development-only random quote-group, route and unseen-airport tests are stored separately. Stress models cap tree count at 250, explicitly differing from final 400/550-tree fits. They diagnose gaps and never authorize unseen-airport serving. Class, journey, airline, airport, route, booking-window, price-range, stops and duration errors are in COHORT_subgroup_metrics.csv.

The historical interval uses a finite-sample 90% absolute-residual quantile from calibration data, then truncates the lower bound at zero for positive fares. Temporal dependence means conformal exchangeability is not established; no distribution-free/future-price guarantee is claimed. Actual test coverage: network {models['network_2020']['interval']['test_coverage']:.2%}; cabin {models['cabin_2023']['interval']['test_coverage']:.2%}. The API requires at least 30 tested route observations and aggregate coverage >=85% to expose a historical range. This heuristic does not establish conditional calibration. Never call the range a confidence interval or promise 90% coverage for each route/class.''')
errors=[];stress=[]
for name in models:
    sg=pd.read_csv(R/f'{name}_subgroup_metrics.csv');worst=sg[(sg.group_type=='route')&(sg.n>=30)].nlargest(8,'mae').copy();worst.insert(0,'cohort',name);errors.append(worst[['cohort','group','n','mae','rmse','p90_absolute_error']])
    gen=pd.read_csv(R/f'{name}_generalization.csv');gen.insert(0,'cohort',name);stress.append(gen)
write(R/'error_analysis_report.md',f'''# Error analysis
Worst final-test routes with >=30 observations:

{table(pd.concat(errors).round(2))}

Development-only stress tests (individual results, not an inflated pooled score):

{table(pd.concat(stress)[['cohort','protocol','n','mae','rmse']].round(2))}

Sparse-cell errors are unstable rankings. Expensive but valid fares remain and can dominate RMSE. Subgroup tables expose weaknesses that overall R² hides. The wider network fails serving support despite 88 observed airports. Stronger familiar-city results cannot establish nationwide reliability. Geographic holdouts and route holdouts answer different questions.''')
ext=json.loads((R/'external_metrics.json').read_text())
write(R/'external_validation_report.md',f'''# Later-source challenge
{table(pd.DataFrame([ext]).round(4))}

The later PromptCloud sample is a same-collector distribution-shift challenge, not independent compatible validation. Actual collection is one day with April departures; advertised quarter labels are not substituted for file dates. Pandemic disruption and unknown target/currency compatibility limit interpretation. All retained real challenge rows are measured, including unseen categories; there is no easy-case filtering. They do not authorize unknown-category API serving.

No fully independent, licensed and price-definition-compatible INR total-fare dataset qualified. The Goibibo derivative cannot provide independence. MakeMyTrip explicitly excludes taxes and lacks needed quote settings/dates; its base fares cannot validate an unknown total-fare target. No conversion, interpolation or synthetic validation is used.''')
plt.rcParams.update({'axes.prop_cycle':plt.cycler(color=['#4c7288','#9e8574','#718373']),'font.size':10})
def plot(name,title,draw):
    fig,ax=plt.subplots(figsize=(9,5));draw(ax);ax.set_title(title,loc='left',pad=18);ax.spines[['right','top']].set_visible(False);fig.tight_layout();fig.savefig(R/'figures'/name,dpi=150);plt.close(fig)
for name in models:
    df=pd.read_parquet(ROOT/f'data/processed/{name}.parquet');test=pd.read_parquet(R/f'{name}_test_predictions.parquet')
    plot(name+'_fare_distribution.png','Recorded fare distribution · '+name,lambda ax:(ax.hist(df.price,bins=70),ax.set(xlabel='Source fare units (scope/currency unverified)',ylabel='Observations',yscale='log')))
    for col in ['airline','origin','route','cabin_class','journey_type','stops']:
        v=df.groupby(col).price.median().sort_values().tail(18)
        plot(name+'_fare_by_'+col+'.png','Median recorded fare by '+col+' · '+name,lambda ax,v=v:(v.plot.barh(ax=ax),ax.set_xlabel('Source fare units')))
    for col in ['days_left','duration_minutes','distance_km','travel_date']:
        v=df.groupby(col).price.median()
        plot(name+'_fare_vs_'+col+'.png','Median fare vs '+col+' · '+name,lambda ax,v=v,col=col:(ax.plot(v.index,v.values,linewidth=1),ax.set(xlabel=col,ylabel='Source fare units')))
    rc=df.route.value_counts()
    plot(name+'_sparse_routes.png','Directional route observation support · '+name,lambda ax:(ax.hist(rc,bins=40),ax.set(xlabel='Observations per route',ylabel='Routes')))
    ss=test.sample(min(2000,len(test)),random_state=42)
    plot(name+'_actual_vs_predicted.png','Actual vs predicted · final holdout · '+name,lambda ax:(ax.scatter(ss.price,ss.prediction,s=8,alpha=.35),ax.plot([0,ss.price.max()],[0,ss.price.max()],color='#a88776'),ax.set(xlabel='Actual source fare',ylabel='Predicted source fare')))
    imp=pd.read_csv(ROOT/f'models/{name}/feature_importance.csv').sort_values('mean_absolute_shap')
    plot(name+'_global_shap.png','Mean absolute SHAP · '+name,lambda ax:(ax.barh(imp.feature,imp.mean_absolute_shap),ax.set_xlabel('Mean absolute contribution (source units)')))
    e=json.loads((ROOT/f'models/{name}/explanation_example.json').read_text());cs=pd.Series(e['contributions']).sort_values()
    plot(name+'_individual_shap.png','Actual individual contributions · '+name,lambda ax:(ax.barh(cs.index,cs.values,color=['#a38878' if x<0 else '#4c7288' for x in cs]),ax.axvline(0,color='#88959d',linewidth=.7),ax.set_xlabel('Contribution (not a causal effect)')))
    m=CatBoostRegressor();m.load_model(str(ROOT/f'models/{name}/model.cbm'));ss=test.sample(min(300,len(test)),random_state=42);sh=m.get_feature_importance(Pool(feature_frame(ss),cat_features=CATEGORICAL),type='ShapValues')
    plot(name+'_shap_lead_dependence.png','Lead-time SHAP dependence · '+name,lambda ax:(ax.scatter(ss.days_left,sh[:,FEATURES.index('days_left')],s=12,alpha=.4),ax.set(xlabel='Days before departure',ylabel='SHAP contribution (source units)')))
write(R/'eda_report.md','''# Exploratory analysis
All figures use actual retained observations or fitted outputs. Each cohort has separate fare distributions, medians by airline/origin/route/class/journey-label/stops, fare versus lead-time/duration/distance/date, sparse-route histograms, holdout actual-vs-predicted plots, global/individual SHAP and lead-time SHAP dependence. Source targets are not mixed into a normalized INR chart.

Cabin medians distinguish premium products, so expensive business fares are not automatically invalid outliers. Airline/route medians remain confounded by itinerary mix. Sparse-route counts explain why observation coverage is larger than serving coverage. Actual-vs-predicted plots show large misses hidden by averages. Cabin lead time also tracks departure date from a single query snapshot, so a plot cannot prove a causal benefit of waiting.

True one-way versus return comparisons cannot be made without booking labels. Multi-year seasonal analysis is unsupported by these short windows. Network cabin remains Unspecified. Calendar-date plots are descriptive only. Price tails stay intact. Profiles and subgroup CSVs provide underlying counts and errors.''')
e=json.loads((ROOT/'models/cabin_2023/explanation_example.json').read_text())
write(R/'explainability_report.md',f'''# Explainability
Native CatBoost SHAP comes from fitted models, not handwritten pricing rules. Global importance averages absolute contributions over a fixed seed-42 sample of up to 400 final-test rows. Validation permutation importance shuffles one feature at a time using the selection-fit model; correlated coordinates/distance mean it is not an independent causal ranking.

Saved real cabin example: prediction {e['prediction']:.4f}, baseline {e['baseline']:.4f}, in source units.

{table(pd.DataFrame([{'feature':f,'input':e['inputs'][f],'contribution':v} for f,v in e['contributions'].items()]).round(4))}

Baseline plus all contributions reproduces the model output within 1e-6; automated tests repeat additivity for both fitted models. Positive contributions raise the output relative to the baseline, negative ones lower it. Neither demonstrates causation or guarantees what an airline would charge if an input changed. /predict and /explain validate the same scenario against the same loaded artifact. The UI retains all contributions, even when only six appear as bars.''')
common='SkyLens is a local historical research application. A verified current INR total-fare predictor could not be established. Unknown currency, tax/passenger scope and booking journey type stay visible; source units are never labeled rupees.'
guides={
'PROJECT_WALKTHROUGH.md':f'''# Project walkthrough
{common}

**Research.** scripts/discover.py snapshots catalog searches; inspect_sources.py saves original cards; acquire.py downloads free versioned archives and a commit-pinned airport master. This solves traceability: every file can be identified by URL, version, hash and actual row count. Mirrored datasets do not add independent evidence.

**Preparation.** src/skylens/prepare.py reconciles the cabin raw/cleaned pair, parses dates/durations, joins reviewed city aliases and computes distance. Every removed record has an ID and reason. Input = retained + excluded. An unknown class does not become Economy, and missing quote settings do not become invented totals.

**Learning.** train.py separates training, validation, calibration and final testing. Training learns patterns; validation chooses a configuration; calibration measures residual size; final testing estimates errors after choices are fixed. Reusing the final test for choices would create an optimistic result. Baselines and three CatBoost settings are measured before selecting a model.

**Results.** Cabin final MAE: {models['cabin_2023']['test_metrics']['mae']:.2f} source units. Network: {models['network_2020']['test_metrics']['mae']:.2f}. Full comparison and subgroup CSVs expose alternatives and weak cases. First's 144 rows are excluded. The wider network has no eligible exact profiles; the cabin model has 592 profiles across seven airports.

**Serving.** backend/app loads already-trained native models, checks file hashes and validates support. frontend/src retrieves options, sends a scenario and shows the actual output and native SHAP. Normal requests never train. The 88-airport observation set does not mean 88 supported airports.

**Verification.** Forty automated tests and the production TypeScript/Vite build pass. Browser permission was declined, leaving visual/mobile/interactive browser QA unverified. Raw files remain untouched. The deliverable is code plus evidence and boundaries, not a claim of nationwide live-price readiness.''',
'DATASET_GUIDE.md':'''# Dataset guide
Use reports/dataset_discovery_report.md and dataset_comparison.csv for every assessed candidate, source URL, license declaration and rejection reason. Actual schemas, hashes, row counts and missing values are in data/metadata/file_profiles.json; immutable raw archives are retained locally.

Yash Dharme's 2023 raw source provides seven cities, three sufficiently represented cabin classes and a booking date, but all queries belong to one collection day. PromptCloud provides broader geography across three collection days, without cabin and standardized price definitions. These are separate research cohorts, never a pooled INR target.

The 2022 EaseMyTrip file is a reference. The Goibibo candidate has matching ordered flight IDs, dates shifted 500 days and altered prices, so it is not independent validation. The broad 2019–2025 candidate lacks authentic collection evidence and has questionable route/time fields. Its authenticity is unverified, rather than asserted to be proven synthetic. MakeMyTrip's 404 rows explicitly exclude taxes and lack key quote settings, so they cannot validate a total-price model.

Airport masters and schedules do not contain ticket prices; traffic files do not become fare observations; aggregate fare indexes are not individual quotes. ATL international returns do not establish domestic return support. The HF schedule original has unknown rights, and a mirror's MIT tag does not cure that. Publisher licenses and upstream-rights caveats appear in dataset_licensing_and_provenance.md. No paid API, credentials or unauthorized scraping is required.''',
'DATA_PIPELINE_GUIDE.md':'''# Data pipeline guide
A canonical schema means translating available information into consistent column names without pretending missing information exists. For example, 02h 05m becomes duration_minutes=125. An unknown network cabin stays Unspecified. Unknown currency and fare scope remain null/unknown, and normalized_price_inr remains missing.

Explicit city aliases join to actual nonempty IATA keys. Unresolved or international endpoints and layovers are excluded, with a reason. Empty layover slots legitimately mean no additional recorded stop. Historical Goa maps to GOI, and old Rajkot fares stay RAJ instead of being transferred to HSR. Coordinates yield approximate great-circle distance, not flown itinerary length.

Exact canonical duplicates are removed before splitting; valid expensive fares remain. Quote keys group the same itinerary independently of its price. Earlier appearances in a later partition are purged. Fingerprints and quote groups are checked across all split pairs. No full-data target statistics are used; fitted encoders/scalers are inside training pipelines.

Data leakage means giving the learner information it would not have when making a new prediction. Keeping prices, quote IDs and future outcomes out of features avoids direct leakage. Keeping the final test separate avoids evaluation leakage. Reports and split manifests show the actual checks. A single query snapshot still confounds booking lead time and departure date; more feature columns cannot repair missing collection history.''',
'ML_MODEL_GUIDE.md':f'''# Model guide
Regression estimates a number from inputs. Mean/median baselines ignore inputs and set a reference error. Ridge learns a regularized weighted combination after training-only encoding/scaling. A decision tree learns conditional branches. CatBoost combines many trees and handles categorical data with training-only statistics.

Seven configurations per source share validation partitions. Three fixed tree settings form a small reproducible hyperparameter search, not exhaustive optimization. Validation MAE selects a tree model, with a stop if a simpler baseline is materially better. Native additive explanations are also operationally useful. Final settings: {json.dumps({n:m['hyperparameters'] for n,m in models.items()})}.

MAE is the average size of a miss. RMSE gives large misses more weight. Median absolute error describes a typical case. MAPE uses positive target values and is a percentage, while R² measures explained variance under this experiment; it is not accuracy. All absolute errors here use source units, not verified rupees.

The final holdout is not used to choose parameters. The network tests the latest collection day, while the cabin model tests later departure dates from one snapshot. Random groups, unseen routes and unseen airports answer distinct questions; those stress fits use development data and cap iterations at 250, unlike the final models. They never authorize new-airport serving.

Calibration measures held-out absolute residuals. Nominal 90% is a target: measured coverage is {models['network_2020']['interval']['test_coverage']:.2%} for network and {models['cabin_2023']['interval']['test_coverage']:.2%} for cabin. Dependence/temporal shift means exchangeability is not established, so the usual conformal coverage guarantee cannot be claimed. These historical residual ranges are not confidence intervals or future-price promises.''',
'EXPLAINABILITY_GUIDE.md':f'''# Explaining an estimate
SHAP distributes a fitted model's output among input contributions relative to a baseline. In the saved actual cabin example, baseline {e['baseline']:.2f} plus contributions equals prediction {e['prediction']:.2f}, in source units. The exact inputs and numbers are in models/cabin_2023/explanation_example.json and reports/explainability_report.md.

A positive contribution raises the output relative to the baseline; a negative contribution lowers it. This describes how the model used the inputs. It does not establish what caused the airline's price or promise a counterfactual price change. Correlated geography fields share information, so one coordinate's importance is not a causal discovery.

Global importance averages absolute native SHAP over real held-out rows. Permutation importance shuffles a validation input and measures its error increase using the selection-fit model. Local explanations use the exact validated request and the saved native model. All thirteen contributions are retained even when six are shown as bars. Automated checks confirm baseline plus contributions equals the actual prediction within 1e-6.''',
'API_GUIDE.md':'''# API guide
Run ./run.ps1. The built frontend is at http://127.0.0.1:8000; generated API documentation is /docs.

GET /health reports artifact readiness (503 if incomplete). /model-info returns measured metadata. /supported-options?model_id=cabin_2023 returns eligible profiles and numeric bounds. /airports accepts query, model_id and supported_only; false exposes the full directory. /airlines returns eligible historical labels. /coverage distinguishes master/fare/serving evidence. /route-coverage filters eligible profiles by model_id, origin and destination. /feature-importance returns actual mean absolute SHAP.

POST /predict and /explain require model_id, origin, destination, airline, cabin_class, days_left, duration_minutes, stops, departure_hour and research_acknowledged=true. journey_type defaults to single_direction_record. Select a real combination and its bounds from /supported-options; do not assume every carrier serves every route/class. Network has zero eligible profiles and rejects ordinary scenarios. The prediction response includes estimate, source unit, null currency, unknown scope/passenger basis, support, warnings and an optional empirically evaluated interval. /explain returns baseline, thirteen contributions and additive error.

Extra fields, incorrect types, invalid ranges and unsupported routes/classes/carriers produce 422. Missing/corrupt models produce 503. Unexpected failures return safe 500 messages without stack traces. No travel_date, return_date or passenger_count is accepted because those targets are unsupported. Models load once; there is no retraining endpoint or fake fallback. Explicit local CORS origins are configurable through SKYLENS_CORS_ORIGINS.''',
'FRONTEND_GUIDE.md':'''# Frontend guide
React + TypeScript + Vite, ordinary CSS and system fonts keep the UI small and free of external runtime services. main.tsx owns metadata loading, scenario state, API calls, airport comboboxes, the directory and model tables. style.css supplies a warm-neutral/navy editorial design with responsive layout rules.

Every airport/carrier/class/profile choice comes from the API. Endpoint changes choose an eligible route; cabin/carrier/stops depend on joint support, not independent hard-coded lists. Defaults use observed field minima for a hypothetical historical scenario, not an advertised real flight schedule. Numeric fields show support ranges. A model without eligible cells displays the reason and remains inspectable in coverage and methodology.

Submission clears old output, calls /predict and /explain, and displays output only when both succeed. API failure never becomes a sample fare. Loading, no-result and error states are explicit. Airport search supports names, cities and codes plus arrow keys, Enter and Escape. Labels, focus rings, live regions and reduced-motion rules are included. Tables scroll in their own containers on small screens.

The TypeScript production build passes. Browser permission was declined, so actual keyboard interaction, responsive overflow and visual appearance remain unverified browser QA items.''',
'EDGE_CASES_AND_VALIDATION.md':'''# Edge cases and validation
Forty executed tests cover native fitted-model outputs and SHAP additivity, missing fields, malformed JSON, invalid types/ranges, unknown IATA/ICAO, same endpoints, unsupported class/carrier/journey, extra dates/return/passenger fields, failed artifacts, safe internal errors, search/metadata, exclusion accounting, duplicate/quote separation and unknown currency preservation.

The sparse network is an expected restriction: its fitted outputs can be evaluated offline while the API blocks profiles below fifty observations. Tests verify both behaviors without lowering the gate. Support uses training+validation fitting rows, never test membership. Missing/corrupt artifact fixtures stay in a temporary test folder; malformed requests and corrupt bytes are the only synthetic test data, and none enter learning or metrics.

Real domestic return, same-day return and multi-city flows cannot be asserted as supported without data. They are rejected by schema restrictions. Unknown cabin labels do not become Economy. The final split manifests and reports/test_results.xml are independently inspectable.

The production TypeScript build passes, but browser permission was declined. Interactive/mobile/visual QA remains outstanding and must precede any production-readiness claim.''',
'VIVA_PREPARATION.md':f'''# Viva preparation
**Problem statement:** Public airfare data are uneven, and prices change with itinerary conditions. I built a traceable historical research system and tested which claims its data can support.

**Why not claim all airports?** The master has 661 airfield records, selected fares map to 88 airports, and only seven have eligible cabin research profiles. Zero qualify for verified current INR totals. Airport metadata is not fare evidence.

**Why these data?** The 2023 source offers cabin/booking fields; PromptCloud offers wider geography. Actual files, licenses, duplicate lineage and price definitions determine selection. Raw/cleaned copies are not independent observations. The Goibibo derivative cannot validate a later period.

**Why no live quote or round trip?** Tax inclusion, passenger basis, currency fields and booking types are undocumented in selected sources. There is no qualified domestic return-price/return-date dataset. Summing two one-way-looking rows would invent a return booking.

**What was cleaned?** Dates and durations were parsed; reviewed city aliases were joined; international/unmapped itineraries were excluded with reasons; duplicates were removed; valid expensive fares stayed. First has only 144 rows and is not trained/offered.

**Features:** Endpoints, carrier, class, stops, duration, lead time, departure hour and geography. They are scenario inputs or target-independent metadata; target values and post-flight outcomes are excluded.

**Why CatBoost?** It performed well against tested baselines on the same validation partitions and supports native additive explanations. Three configurations were tried, not every algorithm. Saved comparison CSVs show the alternatives.

**How is leakage prevented?** Distinct quote/fingerprint groups across train, validation, calibration and final test; fold-specific preprocessing; no target-derived features; no concatenated mirrors; no test tuning.

**Actual results:** Cabin MAE {models['cabin_2023']['test_metrics']['mae']:.2f}, RMSE {models['cabin_2023']['test_metrics']['rmse']:.2f}, R² {models['cabin_2023']['test_metrics']['r2']:.4f}. Network MAE {models['network_2020']['test_metrics']['mae']:.2f}, RMSE {models['network_2020']['test_metrics']['rmse']:.2f}, R² {models['network_2020']['test_metrics']['r2']:.4f}. These are source fare units, not rupees. R² is not percent accuracy.

**Validation limits:** Random groups test familiar distributions; route holdouts and airport holdouts test different gaps. Cabin departure-day chronology is only one booking snapshot, not future booking-day evidence. Geographic stress fits cap trees at 250 and do not enable unseen-airport serving.

**SHAP:** Baseline plus input contributions equals the fitted prediction. Positive raises that output, negative lowers it. Association is not causation.

**App architecture:** React retrieves metadata and sends validated scenarios to FastAPI. FastAPI loads hashed native artifacts and returns real model and SHAP outputs. It never retrains per request or fills failures with samples.

**Improvements:** Legitimately licensed quotes with documented INR/taxes/passengers/journey type, repeated query dates, more joint route evidence, compatible independent validation and current service verification. Browser visual/interactive QA also remains unfinished because permission was declined.'''}
for name,text in guides.items():write(D/name,text)
write(R/'final_project_report.md',f'''# Final project report
{common}

Delivered: source discovery/acquisition, immutable originals and hashes, a 661-record airport master, honest mapping of fares to 88 historical airports, source-specific canonical research cohorts and exclusions, measured baselines/tuning, temporal/random/route/airport validation, native artifacts, real SHAP and empirical residual intervals, FastAPI, React, automated tests, reports/figures and learning guides.

{table(results.round(4))}

Not established: current verified INR totals, confirmed one-way booking fares, domestic returns/multi-city, First serving, reliable unseen routes/airports, compatible independent validation or broad network serving. All wider exact training cells have <=17 observations, below the unchanged minimum 50. Seven airports have eligible cabin research profiles. These limitations are enforced, not buried.

Forty automated tests and the TypeScript production build pass. Browser access was declined; mobile/interactive/visual browser QA remains unverified. No paid runtime dependency or credentials are needed. This is a working local research project with explicit data barriers, not a completed validated nationwide price service.''')
write(ROOT/'README.md',f'''# SkyLens
Indian domestic historical airfare research, coverage and model explanations. A college ML project with traceable files, measured validation and a local application.

> Research edition: no verified current INR total-fare model qualified from the audited data. Currency, taxes, passenger basis and booking type remain undocumented. Outputs stay in source fare units. Confirmed one-way booking fares, round-trip/multi-city and live quotes are unsupported.

## Run locally (Windows PowerShell)
From this repository root, with free Python 3.12, Node 22+ and uv:

```powershell
.\\setup.ps1
.\\run.ps1
```

Open http://127.0.0.1:8000. API reference: http://127.0.0.1:8000/docs. The trained artifacts and datasets already exist in this workspace; setup does not retrain. To reconstruct a source-only checkout:

```powershell
.venv\\Scripts\\python.exe scripts\\discover.py
.venv\\Scripts\\python.exe scripts\\inspect_sources.py
.venv\\Scripts\\python.exe scripts\\acquire.py
$env:PYTHONPATH = 'src'
.venv\\Scripts\\python.exe -m skylens.prepare
.venv\\Scripts\\python.exe -m skylens.train
.venv\\Scripts\\python.exe -m skylens.report
.venv\\Scripts\\python.exe -m pytest -q --junitxml=reports/test_results.xml
npm --prefix frontend ci
npm --prefix frontend run build
.\\run.ps1
```

Separate frontend development: start the API and run `npm --prefix frontend run dev`. Vite proxies API endpoints to port 8000. CORS allows only configured local origins. `.env.example` documents SKYLENS_CORS_ORIGINS, read from the process environment (the file is not automatically loaded). No account, paid API or secret is needed. Acquisition needs internet; subsequent inference is local. No cloud publication was performed.

## Evidence and scope
{table(pd.DataFrame([{'concept':k,'count':v} for k,v in counts.items()]))}

661 includes heliports/closed/noncommercial airfields. Scheduled flags are community metadata, not authoritative current schedules. The 88 observed airports are not 88 supported airports. The cabin model has 592 eligible exact profiles across seven airports and 42 routes. Every exact wider-network cell has fewer than 50 training observations, so that model is offline-evaluation-only. Economy, Business and Premium Economy appear in cabin research; First's 144 rows are excluded. Carrier availability is historical, not current service verification.

## Data discovery and selection
Sources were investigated across Kaggle, GitHub, Hugging Face, Zenodo, Figshare, OpenML, government and academic sources. Eight free public source archives and commit-pinned OurAirports metadata were inspected. Original cards, declared licenses, actual schemas, rows, sizes, hashes and exclusions are saved. Unknown target definitions mean the selected fares remain isolated research cohorts; normalized_price_inr is missing.

The 2023 raw EaseMyTrip source has seven cities and one collection day. Separate pre-pandemic PromptCloud records offer broader geography across three collection days. A later same-collector sample is a drift challenge, not independent compatible validation. Raw/cleaned representations are not stacked. The Goibibo candidate shifts the original 2022 dates 500 days with identical ordered flight IDs; it is excluded. Tax-exclusive base fares, aggregates, schedules and traffic are not mixed into an individual total-price target. See [discovery](reports/dataset_discovery_report.md), [selection](reports/dataset_selection_decision.md), [licenses](reports/dataset_licensing_and_provenance.md) and [coverage](reports/airport_coverage_report.md).

## Pipeline and architecture
Public archives → immutable raw files → audited canonical cohorts → leakage-controlled splits → candidate comparisons → fitted native models → FastAPI → React.

src/skylens separates preparation, feature schema, training and report generation; scripts separates acquisition. backend/app loads existing artifacts and validates requests; frontend retrieves metadata and renders real outputs. Model code and API serving are independent. Geography does not automatically validate unseen airports.

Preparation parses explicit duration/date values, preserves unknown scope/currency and records every exclusion. Native categorical labels are preserved. Training-only encoders/scalers and CatBoost fitting avoid full-data target statistics. Quote-group/fingerprint checks prevent cross-split duplicates. No final-test tuning, synthetic training data or guessed booking metadata is used. The single cabin collection date still confounds lead time and departure date.

## Models and actual results
Mean, median, Ridge, a decision tree and three CatBoost settings share identical temporal validation partitions. A small seeded parameter search selects the final model; final testing and calibration stay separate.

{table(results[['cohort','n','mae','rmse','r2','median_absolute_error','mape_percent','p90_absolute_error','interval_coverage']].round(4))}

Absolute errors use source fare units, not verified INR. R² is explained variance under the specified protocol, not accuracy. Cabin chronology tests later departures from one snapshot; network chronology tests the latest collection day. Random-group, route and unseen-airport stress fits use development data and cap tree count at 250, unlike final fits. [Evaluation](reports/model_evaluation_report.md), [errors](reports/error_analysis_report.md) and [external challenge](reports/external_validation_report.md) expose limits rather than relying only on R².

Native SHAP assigns actual fitted contributions: baseline + all contributions reproduces the output. Global mean absolute SHAP and validation permutation importance are saved. Contributions describe associations, not causes. [Explainability report](reports/explainability_report.md) includes an actual example. Residual intervals use separate calibration observations, with measured final-test coverage. Temporal shift prevents a distribution-free/future-price guarantee; optional ranges are labeled historical empirical intervals, not confidence intervals.

## API and interface
FastAPI validates schema, categories, joint support and numeric bounds. It hashes native model files at startup; requests never retrain. Errors return meaningful 422/503 or safe 500 responses without internal stacks. Explicit CORS is configurable. See [API guide](docs/API_GUIDE.md).

React + TypeScript + Vite offers searchable airports, dependent scenario fields, real model results and SHAP, a coverage directory and measured model tables. Backend metadata supplies every available option. A minimum 50 training observations is required per route/airline/class/stops profile, with observed numeric bounds; it is a conservative research heuristic, not a reliability theorem. Unsupported routes are blocked. Calendar-date inputs are omitted because current/future dates cannot be supported. API failure never falls back to fictional sample prices.

## Checks and reproducibility
Forty automated tests passed, including real model output, SHAP additivity, quote separation, corruption handling, invalid inputs and support rejection. The TypeScript/Vite production build passed. Browser permission was declined; browser interaction, mobile overflow and visual QA remain unverified. Run tests with `.venv\\Scripts\\python.exe -m pytest -q`; results are saved in reports/test_results.xml.

Python packages are pinned in requirements.txt, npm in package-lock.json. Model metadata includes parameters, seed, dataset and artifact hashes, dates and metrics. Native artifacts/raw data are kept locally but ignored by Git to avoid unnecessary large-data redistribution. A source-only checkout must rerun acquisition/preparation/training. Never commit secrets or replace missing authentic fares with synthetic training rows.

## Learn and present
Start with [walkthrough](docs/PROJECT_WALKTHROUGH.md), [datasets](docs/DATASET_GUIDE.md), [pipeline](docs/DATA_PIPELINE_GUIDE.md), [models](docs/ML_MODEL_GUIDE.md), [SHAP](docs/EXPLAINABILITY_GUIDE.md), [API](docs/API_GUIDE.md), [frontend](docs/FRONTEND_GUIDE.md), [edge cases](docs/EDGE_CASES_AND_VALIDATION.md) and [viva preparation](docs/VIVA_PREPARATION.md). Reports and figures provide actual evidence.

## Remaining work and future improvements
A verified total-ticket service needs legitimately licensed quotes with currency, tax/passenger basis, real journey types and repeated query days. Wider serving needs more joint route evidence, compatible independent validation and current airline/airport verification. Real return fares are needed before round trips. First Class needs sufficient samples. Residual-interval shortfalls and external drift remain visible. Browser QA must still be completed. This deliverable is a working local research application, not a validated nationwide live-price service.
''')
print('Generated research reports, teaching guides, README and actual-data figures.')

import runpy
runpy.run_path(str(ROOT/'scripts/finalize_evidence.py'),run_name='__main__')

http=json.loads((R/'http_integration_results.json').read_text())
integrity=json.loads((R/'raw_integrity_results.json').read_text())
extra=f'\n\nAdditional executed checks: {http["profiles_checked"]} advertised profiles passed real HTTP prediction with {len(http["failures"])} failures; {http["compiled_assets_checked"]} compiled frontend assets and the HTML page returned HTTP 200. All {integrity["verified_original_files"]} original file hashes match. Frozen-version acquisition was rerun successfully without raw overwrites. These checks do not replace the declined browser QA.\n'
for name in [ROOT/'README.md',R/'final_project_report.md',D/'EDGE_CASES_AND_VALIDATION.md']:
    name.write_text(name.read_text(encoding='utf-8')+extra,encoding='utf-8')

architecture_path=R/'cabin_architecture_comparison.csv'
if architecture_path.exists():
    architecture=pd.read_csv(architecture_path)
    text='\n\n## Additional cabin architecture diagnostic\n'+table(architecture[['architecture','class','n','mae','rmse']].round(3))+'\nThese are post-hoc development-only results. The frozen pooled artifact and its final-test results remain unchanged. Separate class models are a promising follow-up requiring a fresh untouched evaluation before promotion. Reproduce with `$env:PYTHONPATH = "src"` then `.venv\\Scripts\\python.exe scripts\\compare_cabins.py`.\n'
    for path in [ROOT/'README.md',R/'model_evaluation_report.md',R/'final_project_report.md',D/'ML_MODEL_GUIDE.md']:
        path.write_text(path.read_text(encoding='utf-8')+text,encoding='utf-8')

# Preserve current phase-two corrections when baseline reports are regenerated.
checkpoint_file=ROOT/'data/metadata/phase2_checkpoint.json'
if (ROOT/'reports/phase2_final_audit.json').exists() and checkpoint_file.exists():
    checkpoint=json.loads(checkpoint_file.read_text(encoding='utf-8'))
    if (ROOT/'backups'/Path(checkpoint['checkpoint_dir']).name).exists():
        extension=runpy.run_path(str(ROOT/'scripts/phase2_reports.py'))
        extension['main']()
