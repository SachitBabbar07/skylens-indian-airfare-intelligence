"""Post-hoc development-only architecture comparison; final holdout remains closed."""
from pathlib import Path
import json,time
import pandas as pd
from catboost import CatBoostRegressor
from skylens.prepare import ROOT
from skylens.features import feature_frame,CATEGORICAL
from skylens.train import metrics
m=json.loads((ROOT/'models/cabin_2023/metadata.json').read_text());df=pd.read_parquet(ROOT/'data/processed/cabin_2023.parquet');splits=pd.read_parquet(ROOT/'data/processed/cabin_2023_splits.parquet')
df=df.merge(splits[['fingerprint','split']],on='fingerprint',validate='one_to_one');tr=df[df.split.eq('train')];va=df[df.split.eq('validation')];rows=[]
def fitted(train):
    model=CatBoostRegressor(**m['hyperparameters'],loss_function='MAE',random_seed=42,thread_count=8,verbose=False,allow_writing_files=False)
    model.fit(feature_frame(train),train.price,cat_features=CATEGORICAL);return model
pooled=fitted(tr);print('Pooled development model fitted',flush=True)
for cabin in sorted(tr.cabin_class.unique()):
    train=tr[tr.cabin_class.eq(cabin)];valid=va[va.cabin_class.eq(cabin)];started=time.perf_counter();special=fitted(train)
    for name,model in [('pooled',pooled),('class_specific',special)]:rows.append({'architecture':name,'class':cabin,'training_rows':len(tr) if name=='pooled' else len(train),**metrics(valid.price,model.predict(feature_frame(valid)))})
    print(cabin,rows[-2]['mae'],rows[-1]['mae'],flush=True)
result=pd.DataFrame(rows);result.to_csv(ROOT/'reports/cabin_architecture_comparison.csv',index=False)
text='''# Cabin architecture comparison
This additional diagnostic uses training and validation partitions only, with the same selected hyperparameters. The final test is not evaluated or used to revise the frozen model. It is a post-hoc research comparison, not part of the original model-selection claim. Pooled and separate models use identical validation rows for each class. No return/one-way specialized model can be compared because booking journey types remain unverified. First is still excluded as sparse.

'''+result.to_csv(index=False)+'''\nThe deployed research artifact stays the previously selected pooled model. Separate-class results identify an improvement candidate that would require a fresh untouched evaluation before promotion, avoiding retrospective selection on an already-opened holdout.\n'''
(ROOT/'reports/cabin_architecture_comparison.md').write_text(text,encoding='utf-8')
