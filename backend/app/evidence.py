"""Projection of frozen historical coverage; no price values enter the directory."""
import csv
import json
from pathlib import Path

from fastapi import HTTPException


def historical_evidence(root: Path) -> dict:
    try:
        profiles = json.loads((root/'data/metadata/cohort_profiles.json').read_text(encoding='utf-8'))
        semantics = json.loads((root/'data/metadata/phase2/fare_semantics.json').read_text(encoding='utf-8'))
        cohorts = {key: {
            'id': key, 'source': semantics[key]['source'],
            'retained_observations': p['retained_rows'], 'airport_count': len(p['airports']),
            'directional_routes': p['routes'], 'observed_cabins': sorted(p['cabins']),
            'collection_dates': [p['collection_min'], p['collection_max']],
            'travel_dates': [p['date_min'], p['date_max']],
            'role': 'external_challenge' if key == 'network_external_2020' else 'frozen_research_cohort',
        } for key,p in profiles.items()}
        by_source = {v['source']: key for key,v in cohorts.items()}
        with (root/'reports/route_fare_coverage.csv').open(encoding='utf-8', newline='') as source:
            rows = [{**{k: row[k] for k in ('origin','destination','cabin_class')},
                     'cohort_id': by_source[row['source_dataset']], 'observations': int(row['observations'])}
                    for row in csv.DictReader(source)]
        return {'cohorts': list(cohorts.values()), 'routes': rows,
                'distinct_directional_routes': len({(r['origin'],r['destination']) for r in rows}),
                'currency': None, 'research_only': True}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, 'Historical route evidence is unavailable. Restore the coverage reports and retry.') from exc
