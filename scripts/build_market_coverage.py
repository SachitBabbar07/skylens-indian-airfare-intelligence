"""Export all domestic search endpoints, directed routes and dated market checks offline."""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, datetime
from itertools import permutations
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COHORTS = ('network_2020', 'cabin_2023')
ROUTE = ('origin', 'destination')
SCOPE = ('departure_date', 'return_date', 'journey_type', 'cabin_class', 'adults', 'children', 'infants', 'airline')
REQUEST_FIELDS = (*ROUTE, *SCOPE, 'checked_at', 'provider', 'source_status', 'market_outcome',
                  'observation_count', 'currency', 'observed_currency', 'currency_compatibility',
                  'estimation_method', 'reason')
OUTCOMES = {
    'available': 'observed', 'no_observations': 'no_usable_observations',
    'incompatible_observations': 'no_usable_observations', 'unsupported': 'unsupported_request',
    'unconfigured': 'unconfigured', 'not_requested': 'not_requested',
    **dict.fromkeys(('authentication', 'quota', 'rate_limit', 'timeout', 'tls_verification',
                     'unavailable', 'invalid_response'), 'technical_failure'),
}


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as stream:
        yield from csv.DictReader(stream)


def write_csv(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def history_by_route():
    history = defaultdict(Counter)
    for row in read_csv(ROOT / 'reports/route_fare_coverage.csv'):
        history[row['origin'], row['destination']]['historical_listing_rows'] += int(row['observations'])

    for cohort in COHORTS:
        folder = ROOT / 'models' / cohort
        meta = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
        if not meta['research_only'] or meta['production_ready']:
            raise ValueError(f'{cohort}: review customer model eligibility before publishing coverage.')
        fitting_rows = 0
        for row in read_csv(folder / 'support.csv'):
            count = int(row['n'])
            fitting_rows += count
            route = history[row['origin'], row['destination']]
            route[f'{cohort}_fit_rows'] += count
            route['research_eligible_profiles'] += int(row['eligible'] == 'True')
        if fitting_rows != meta['split_sizes']['train'] + meta['split_sizes']['validation']:
            raise ValueError(f'{cohort}: support table differs from saved fit.')
    return history


def checked_requests(probes, codes):
    records = json.loads(probes.read_text(encoding='utf-8'))
    if not isinstance(records, list):
        raise ValueError('Expected a list of dated market checks.')
    rows = []
    seen = set()
    for record in records:
        row = {field: record[field] for field in (*ROUTE, *SCOPE, 'checked_at', 'estimation_method', 'reason')}
        if row['origin'] == row['destination'] or not {row['origin'], row['destination']} <= codes:
            raise ValueError('Probe endpoints must identify a domestic search route.')
        departure = date.fromisoformat(row['departure_date'])
        returning = date.fromisoformat(row['return_date']) if row['return_date'] else None
        if (row['journey_type'] not in ('one_way', 'round_trip') or
                (row['journey_type'] == 'round_trip') != bool(returning) or (returning and returning < departure)):
            raise ValueError('Probe dates do not match its journey type.')
        if (datetime.fromisoformat(row['checked_at']).utcoffset() is None
                or row['cabin_class'] not in ('economy', 'premium_economy', 'business', 'first')):
            raise ValueError('Probe needs a timezone-aware retrieval time and a cabin.')
        party = [row[field] for field in ('adults', 'children', 'infants')]
        if (any(type(n) is not int or n < 0 for n in party) or party[0] < 1
                or party[2] > party[0] or sum(party) > 9):
            raise ValueError('Invalid traveller composition in probe.')
        row['provider'] = record.get('provider')
        identity = tuple(row[field] for field in (*ROUTE, *SCOPE, 'checked_at', 'provider'))
        if identity in seen:
            raise ValueError('Duplicate dated probe.')
        seen.add(identity)

        status = record['source_status']
        status = status['market'] if isinstance(status, dict) else status
        outcome = OUTCOMES[status]
        count = record['observation_count']
        currency = record['currency']
        observed_currency = record.get('observed_currency')
        if row['estimation_method'] == 'market_reference':
            if outcome != 'observed' or type(count) is not int or count < 1 or currency != 'INR':
                raise ValueError('Market reference needs comparable INR observations.')
        elif row['estimation_method'] != 'unavailable' or not row['reason']:
            raise ValueError('Expected a documented market reference or an unavailable reason for these models.')
        if outcome == 'no_usable_observations' and (type(count) is not int or count != 0):
            raise ValueError('Successful checks without comparable observations need count zero.')
        if outcome == 'observed' and row['estimation_method'] != 'market_reference':
            raise ValueError('Market status must agree with its estimation method.')
        if row['estimation_method'] == 'unavailable' and currency is not None:
            raise ValueError('An unavailable estimate cannot declare an output currency.')
        compatibility = 'unknown'
        if outcome == 'observed' or observed_currency == 'INR':
            compatibility = 'INR'
        elif observed_currency:
            compatibility = 'incompatible'
        row.update(source_status=status, market_outcome=outcome, observed_currency=observed_currency,
                   observation_count=count if outcome in ('observed', 'no_usable_observations') else None,
                   currency=currency, currency_compatibility=compatibility)
        rows.append(row)
    return rows


def build(probes, output):
    airports = {
        row['iata_code']: row for row in read_csv(ROOT / 'reports/airport_fare_coverage.csv')
        if row['iso_country'] == 'IN' and row['iata_code']
    }
    history = history_by_route()
    review = json.loads((ROOT / 'data/metadata/phase5/acquisition_decision.json').read_text(encoding='utf-8'))
    if review['customer_fare_prediction_available'] or review['production_eligible_airports'] != 0:
        raise ValueError('Customer approval changed. Review the approved model and scope before publishing coverage.')
    requests = checked_requests(probes, set(airports))
    checks = Counter((row['origin'], row['destination']) for row in requests)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / 'requests.csv', REQUEST_FIELDS, requests)

    counts = ('historical_listing_rows', *(f'{c}_fit_rows' for c in COHORTS), 'research_eligible_profiles')
    route_fields = (*ROUTE, *counts, 'customer_ml_eligible', 'recorded_checks', 'market_evidence')
    airport_counts = defaultdict(Counter)

    def routes():
        for origin, destination in permutations(sorted(airports), 2):
            pair = origin, destination
            stats = history.get(pair, Counter())
            for code in pair:
                airport_counts[code].update(stats)
                airport_counts[code]['routes_with_checks'] += int(pair in checks)
            yield {'origin': origin, 'destination': destination, **{name: stats[name] for name in counts},
                   'customer_ml_eligible': False, 'recorded_checks': checks[pair],
                   'market_evidence': 'see_dated_requests' if pair in checks else 'unprobed'}

    write_csv(output / 'routes.csv', route_fields, routes())
    airport_fields = ('iata', 'name', 'city', 'state', *counts, 'customer_ml_eligible', 'routes_with_checks')
    write_csv(output / 'airports.csv', airport_fields, (
        {'iata': code, 'name': airports[code]['name'], 'city': airports[code]['municipality'],
         'state': airports[code]['state'], **{name: airport_counts[code][name] for name in counts},
         'customer_ml_eligible': False, 'routes_with_checks': airport_counts[code]['routes_with_checks']}
        for code in sorted(airports)
    ))
    route_count = len(airports) * (len(airports) - 1)
    print(f'{len(airports)} airports, {route_count} directed routes, {len(requests)} recorded checks, '
          f'{route_count - len(checks)} unprobed routes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probes', type=Path, default=ROOT / 'reports/market_probe_results.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/cache/market_coverage')
    args = parser.parse_args()
    try:
        build(args.probes, args.output_dir)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f'Coverage export failed: {error}\n')


if __name__ == '__main__':
    main()
