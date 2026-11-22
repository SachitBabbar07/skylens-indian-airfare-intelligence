"""Bounded, read-only route probes and network-free replay of normalized observations."""

import argparse
import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

from backend.app.capabilities import product_capabilities
from backend.app.fare_service import FareError
from backend.app.flight_fares import IST, FlightSearch, LiveQuote, Travellers
from backend.app.flight_search import load_airports
from backend.app.hybrid_estimator import select_estimate
from backend.app.kiwi_fares import KiwiFareProvider


ROOT = Path(__file__).resolve().parents[1]
# Origin, destination, days after the first departure, return stay in days, adults.
# The fixed itinerary panel samples market coverage independently of fare values.
PROBE_CASES = (
    ('DEL', 'IXC', 0, 0, 1), ('BOM', 'BLR', 0, 0, 1), ('BOM', 'BLR', 7, 3, 2),
    ('MAA', 'CJB', 2, 0, 2), ('IXB', 'CCU', 5, 0, 1), ('CCU', 'IXB', 9, 4, 1),
    ('GAU', 'IMF', 6, 0, 1), ('IXA', 'JAI', 7, 0, 1), ('SLV', 'IXC', 11, 0, 1),
)
STOP_BATCH = {'authentication', 'quota', 'rate_limit', 'tls_verification'}


def json_line(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n'


async def capture(directory: Path, first_departure: date) -> None:
    if os.getenv('SKYLENS_KIWI_FARES_ENABLED', 'true').strip().lower() == 'false':
        raise SystemExit('Market provider is disabled.')
    if product_capabilities()['fare_estimation']['available']:
        raise SystemExit('Review the probe source registration for the approved customer model.')
    airports = load_airports(ROOT)
    directory.mkdir(parents=True, exist_ok=True)
    provider = KiwiFareProvider()
    try:
        for origin, dest, offset, stay, adults in PROBE_CASES:
            departure = first_departure + timedelta(days=offset)
            query = FlightSearch(origin=origin, destination=dest, departure_date=departure,
                                 journey='round_trip' if stay else 'one_way',
                                 return_date=departure + timedelta(days=stay) if stay else None,
                                 travellers=Travellers(adults=adults))
            if origin not in airports or dest not in airports:
                raise ValueError('Probe contains an unknown airport.')
            path = directory / f'{origin}-{dest}-{departure}.json'
            payload = query.model_dump(mode='json')
            if path.exists():
                prior = json.loads(path.read_text(encoding='utf-8'))
                if prior['request'] != payload:
                    raise ValueError(f'Conflicting existing capture: {path.name}')
                if prior['market_status'] in STOP_BATCH:
                    break
                continue
            observations = []
            try:
                async with asyncio.timeout(10):
                    observations = await provider.search(query)
                status = 'available' if observations else 'no_observations'
            except FareError as error:
                status = error.code
            except TimeoutError:
                status = 'timeout'
            now = datetime.now(timezone.utc).isoformat()
            quotes = []
            for value in observations:
                quote = value.model_dump(mode='json')
                quote['id'] = sha256(quote['id'].encode()).hexdigest()
                quotes.append(quote)
            capture_row = {'captured_at': now, 'request': payload, 'market_status': status, 'quotes': quotes}
            estimate = select_estimate(query, None, observations, coverage_status='unsupported', market_status=status)
            capture_row['response'] = estimate.response.model_dump(mode='json')
            capture_row['computed_at'] = datetime.now(timezone.utc).isoformat()
            with path.open('x', encoding='utf-8') as target:
                target.write(json_line(capture_row))
            print(path.name, status, len(quotes), flush=True)
            if status in STOP_BATCH:
                break
            await asyncio.sleep(3)
    finally:
        await provider.close()


def summarize(directory: Path, report: Path) -> None:
    rows, estimates = [], []
    for path in sorted(directory.glob('*.json')):
        capture_row = json.loads(path.read_text(encoding='utf-8'))
        captured_at = datetime.fromisoformat(capture_row['captured_at'])
        if captured_at.tzinfo is None:
            raise ValueError('Expected timestamp with timezone')
        query = FlightSearch.model_validate(capture_row['request'], context={'as_of_date': captured_at.astimezone(IST).date()})
        quotes = [LiveQuote.model_validate(q) for q in capture_row['quotes']]
        status = capture_row['market_status']
        response = select_estimate(query, None, quotes, coverage_status='unsupported', market_status=status).response
        result = response.model_dump(mode='json')
        if status not in {'available', 'incompatible_observations', 'no_observations'}:
            count = None
        else:
            count = result['observation_count']
        # Keep only scoped derived statistics in the public artifact.
        rows.append(dict(origin=query.origin, destination=query.destination, departure_date=query.departure_date.isoformat(),
                         return_date=str(query.return_date) if query.return_date else None, journey_type=query.journey,
                         cabin_class=query.cabin, airline=query.airline, **query.travellers.model_dump(),
                         checked_at=capture_row['captured_at'], provider='Kiwi.com', source_status=result['source_status'],
                         observation_count=count, currency=result['currency'], estimation_method=result['estimation_method'],
                         reason=result['source_status']['market'] if result['estimation_method'] == 'unavailable' else None,
                         normalized_offer_count=len(quotes) if count is not None else None,
                         range_kind=result['range_kind'], stop_profile=result['stop_profile'],
                         estimated_low=result['estimated_low'], estimated_median=result['estimated_median'],
                         estimated_high=result['estimated_high']))
        # An identical original prediction remains prospective. A changed rule or
        # a raw-only capture must use the time of this new computation.
        computed = (capture_row.get('computed_at') if capture_row.get('response') == result else None)
        estimates.append(json_line({**capture_row, 'response': result,
                                    'computed_at': computed or datetime.now(timezone.utc).isoformat()}))
    if not rows:
        raise ValueError('No captures to replay.')
    (directory / 'estimates.jsonl').write_text(''.join(estimates), encoding='utf-8')
    report.write_text(json.dumps(rows, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    live = commands.add_parser('capture', help='Read the free provider once per uncaptured search')
    live.add_argument('--first-departure', type=date.fromisoformat, required=True)
    live.add_argument('--directory', type=Path, required=True)
    replay = commands.add_parser('summarize', help='Recalculate current estimates offline')
    replay.add_argument('--directory', type=Path, required=True)
    replay.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture':
        asyncio.run(capture(args.directory, args.first_departure))
    else:
        summarize(args.directory, args.report)
