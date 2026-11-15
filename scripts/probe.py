from pathlib import Path
import json, pandas as pd, re
R=Path(__file__).resolve().parents[1]
a=pd.read_csv(R/'data/raw/ourairports/airports.csv'); a=a[a.iso_country.eq('IN') & a.iata_code.notna()]
for c in ['class','Source','destination']:
    d=pd.read_csv(R/'data/raw/shraddha4ever20/flights.csv')
    if c in d: print(c,d[c].nunique())
b=pd.read_csv(R/'data/raw/shubhambathwal/economy.csv');g=pd.read_csv(R/'data/raw/iamavyukt/goibibo_flights_data.csv').iloc[:len(b)]
print('goibibo delta range',(g.price.str.replace(',','').astype(int)-b.price.str.replace(',','').astype(int)).describe().to_dict())
pd.set_option('display.max_rows',200)
print(a[['iata_code','municipality','name']].to_string(index=False))
