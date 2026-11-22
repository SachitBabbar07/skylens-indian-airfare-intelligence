"""Offline checks on the customer route inventory and request-scoped market evidence."""

import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/build_market_coverage.py'


def report(output, records):
    probes = output / 'probes.json'
    probes.write_text(json.dumps(records), encoding='utf-8')
    return subprocess.run(
        [sys.executable, str(SCRIPT), '--probes', str(probes), '--output-dir', str(output)],
        capture_output=True, text=True,
    )


def read_rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def check(**overrides):
    return {
        'origin': 'DEL', 'destination': 'BOM', 'departure_date': '2026-11-26',
        'return_date': None, 'journey_type': 'one_way', 'cabin_class': 'economy',
        'adults': 1, 'children': 0, 'infants': 0, 'airline': None,
        'checked_at': '2026-11-19T10:00:00+00:00', 'provider': 'coverage-test',
        'source_status': {'model': 'unsupported', 'market': 'no_observations'},
        'observation_count': 0, 'currency': None, 'estimation_method': 'unavailable',
        'reason': 'Empty result for this search.', **overrides,
    }


@pytest.fixture(scope='module')
def coverage(tmp_path_factory):
    output = tmp_path_factory.mktemp('market-coverage')
    records = [
        check(),
        check(adults=2, journey_type='round_trip', return_date='2026-11-30', airline='indigo',
              source_status='available', observation_count=2, currency='INR',
              estimation_method='market_reference', reason=''),
        check(departure_date='2026-12-01', source_status='timeout', reason='Request timed out.'),
        check(origin='BOM', destination='DEL', source_status='unconfigured', reason='No provider configured.'),
        check(origin='MAA', destination='DEL', source_status='incompatible_observations', observed_currency='EUR',
              reason='No comparable INR prices.'),
    ]
    result = report(output, records)
    assert result.returncode == 0, result.stderr
    return {name: read_rows(output / f'{name}.csv') for name in ['airports', 'routes', 'requests']}


def test_routes_cover_all_search_endpoints_and_distinguish_listings_from_fit(coverage):
    from backend.app.flight_search import load_airports

    codes = set(load_airports(ROOT))
    assert len(codes) == 165
    assert {row['iata'] for row in coverage['airports']} == codes
    rows = {(row['origin'], row['destination']): row for row in coverage['routes']}
    assert set(rows) == {(origin, destination) for origin in codes for destination in codes if origin != destination}
    assert len(coverage['routes']) == len(rows)
    assert sum(int(row['network_2020_fit_rows']) for row in rows.values()) == 7028
    assert sum(int(row['cabin_2023_fit_rows']) for row in rows.values()) == 311968
    assert sum(int(row['research_eligible_profiles']) for row in rows.values()) == 592
    assert sum(int(row['historical_listing_rows']) > 0 for row in rows.values()) == 720
    assert rows['AGR', 'DEL']['historical_listing_rows'] == '11'
    assert rows['AGR', 'DEL']['network_2020_fit_rows'] == rows['AGR', 'DEL']['cabin_2023_fit_rows'] == '0'
    assert {row['customer_ml_eligible'] for row in rows.values()} == {'False'}
    assert rows['DEL', 'BOM']['recorded_checks'] == '3'
    assert rows['BOM', 'DEL']['recorded_checks'] == '1'
    assert all(row['market_evidence'] == 'unprobed' for pair, row in rows.items()
               if pair not in {('DEL', 'BOM'), ('BOM', 'DEL'), ('MAA', 'DEL')})


def test_probe_coverage_preserves_journey_party_and_failure_semantics(coverage):
    rows = coverage['requests']
    assert len(rows) == 5
    observed = next(row for row in rows if row['source_status'] == 'available')
    assert (observed['adults'], observed['return_date'], observed['airline']) == ('2', '2026-11-30', 'indigo')
    assert observed['currency_compatibility'] == 'INR'
    assert observed['observation_count'] == '2'
    empty = next(row for row in rows if row['source_status'] == 'no_observations')
    assert empty['observation_count'] == '0' and empty['market_outcome'] == 'no_usable_observations'
    mismatch = next(row for row in rows if row['source_status'] == 'incompatible_observations')
    assert mismatch['currency_compatibility'] == 'incompatible'
    failure = next(row for row in rows if row['source_status'] == 'timeout')
    unconfigured = next(row for row in rows if row['source_status'] == 'unconfigured')
    assert failure['market_outcome'] == 'technical_failure'
    assert unconfigured['market_outcome'] == 'unconfigured'
    assert failure['observation_count'] == unconfigured['observation_count'] == ''
    assert failure['currency_compatibility'] == unconfigured['currency_compatibility'] == 'unknown'


@pytest.mark.parametrize('overrides', [
    {'destination': 'ZZZ'}, {'checked_at': None}, {'return_date': None, 'journey_type': 'round_trip'},
    {'source_status': 'available', 'estimation_method': 'market_reference', 'observation_count': 0},
])
def test_incomplete_evidence_cannot_be_reported_as_a_route_check(tmp_path, overrides):
    result = report(tmp_path, [check(**overrides)])
    assert result.returncode != 0
    assert 'Coverage export failed:' in result.stderr
    assert not (tmp_path / 'routes.csv').exists()
