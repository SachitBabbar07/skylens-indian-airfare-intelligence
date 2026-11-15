"""Identical train/inference feature schema; no learned preprocessing outside folds."""
CATEGORICAL=['origin','destination','airline','cabin_class']
NUMERIC=['stops','duration_minutes','days_left','departure_hour','distance_km','origin_lat','origin_lon','destination_lat','destination_lon']
FEATURES=CATEGORICAL+NUMERIC

def feature_frame(df):
    x=df[FEATURES].copy()
    for col in CATEGORICAL:x[col]=x[col].astype(str)
    for col in NUMERIC:x[col]=x[col].astype(float)
    return x
