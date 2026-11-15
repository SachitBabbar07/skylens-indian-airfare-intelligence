"""Reproduce Phase 5 candidate quality/lineage checks, never train or alter fares.

Requires the locally restored Bathwal archive and pinned public audit archives.
Optional GitHub CSVs are inspected only when separately available locally; this
script does not fetch sources with unresolved reuse rights.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def key_hashes(frame, fields):
    values = frame[fields].astype(str).copy()
    for field in fields:
        if field in {'duration', 'days_left', 'price'}:
            values[field] = pd.to_numeric(frame[field], errors='raise').map(lambda n: format(float(n), '.8f'))
        else:
            values[field] = values[field].str.lower().str.replace(r'[^a-z0-9.]', '', regex=True)
    return pd.util.hash_pandas_object(values, index=False)


def main():
    base = pd.read_csv(ROOT/'data/raw/shubhambathwal/Clean_Dataset.csv')
    common = ['airline', 'flight', 'source_city', 'departure_time', 'stops', 'arrival_time',
              'destination_city', 'class', 'duration', 'days_left', 'price']
    result = {'baseline_rows': len(base), 'normalization': 'case/separators and eight-decimal numeric key formatting only; no price conversion',
              'training_automatically_enabled': False, 'candidates': []}
    for slug in ['rohitgrewal__airlines-flights-data', 'youssefkhaled117__flight-price-cleaned',
                 'usmankhankk__india-domestic-flight-prices']:
        path = next((ROOT/'data/raw/phase5'/slug).glob('*.csv'))
        frame = pd.read_csv(path)
        fields = [field for field in common if field in frame and not
                  (slug.startswith('youssef') and field == 'flight')]
        original, candidate = key_hashes(base, fields), key_hashes(frame, fields)
        item = {'file': str(path.relative_to(ROOT)).replace('\\', '/'), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'rows': len(frame), 'compared_fields': fields,
                'matching_baseline_keys': int(candidate.isin(original).sum()),
                'multiset_overlap_rows': int(pd.concat([original.value_counts(), candidate.value_counts()], axis=1).fillna(0).min(axis=1).sum()),
                'ordered_keys_identical': len(base) == len(frame) and original.equals(candidate),
                'missing': {k: int(v) for k, v in frame.isna().sum().items()},
                'currency_field_present': 'currency' in frame,
                'observation_timestamp_field_present': any(k in frame for k in ['observation_date', 'collected_at_utc', 'scrape_timestamp'])}
        if slug.startswith('rohit'):
            without_flight = [k for k in common if k != 'flight']
            item['ordered_other_ten_fields_identical'] = all(base[k].equals(frame[k]) for k in without_flight)
            item['flight_label_differences'] = int(base.flight.ne(frame.flight).sum())
        if 'price_capped' in frame:
            item['capped_price_rows'] = int(frame.price_outlier_iqr.eq(True).sum())
            item['target_equals_capped_price'] = bool(frame.price.eq(frame.price_capped).all())
        result['candidates'].append(item)
    optional = ROOT/'data/raw/phase5/AyushyaRanjan__APIx/exports/real_raw_quotes.csv'
    if optional.exists():
        frame = pd.read_csv(optional)
        result['ixigo_export_audit'] = {'sha256': hashlib.sha256(optional.read_bytes()).hexdigest(), 'rows': len(frame),
            'full_breakdown_rows': int(frame.has_full_breakdown.eq(True).sum()),
            'missing_components': {field: int(frame[field].isna().sum()) for field in
                                   ['base_fare', 'taxes_statutory', 'udf_airport_fees', 'convenience_fee']}}
    output = ROOT/'data/metadata/phase5/quality_reproduction.json'
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'candidate_files_checked': len(result['candidates']), 'output': str(output.relative_to(ROOT)),
                      'training_automatically_enabled': False}))


if __name__ == '__main__':
    main()
