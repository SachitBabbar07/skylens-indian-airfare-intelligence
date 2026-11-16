"""Flight search endpoints backed by the reviewed airport master and fare service."""

import csv
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.app.fare_service import FareError, FareService
from backend.app.flight_fares import FlightSearch, SearchResponse
from backend.app.groq_fare_estimator import EstimateError, GroqFareEstimator, IndicativeEstimate


router = APIRouter(prefix='/flights', tags=['Flight search'])


def load_airports(root: Path) -> dict[str, dict]:
    with (root / 'reports/airport_fare_coverage.csv').open(encoding='utf-8', newline='') as source:
        return {
            row['iata_code']: {
                'code': row['iata_code'], 'name': row['name'], 'city': row['municipality'], 'state': row['state'],
                'has_historical_evidence': int(row['fare_endpoint_observations']) > 0,
                'coordinates': coordinates(row['latitude_deg'], row['longitude_deg']),
            }
            for row in csv.DictReader(source) if row['iso_country'] == 'IN' and row['iata_code']
        }


def coordinates(latitude: str, longitude: str) -> tuple[float, float] | None:
    try:
        lat, lon = float(latitude), float(longitude)
    except ValueError:
        return None
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def flight_distance(origin: tuple[float, float] | None, destination: tuple[float, float] | None) -> int | None:
    if origin is None or destination is None:
        return None
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    angle = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(12_742 * asin(sqrt(min(1.0, angle))))


def itinerary_airports(request: Request, payload: FlightSearch) -> tuple[dict, dict]:
    airports = request.app.state.flight_airports
    if not airports:
        raise HTTPException(503, 'The Indian airport directory could not be loaded.')
    if payload.origin not in airports or payload.destination not in airports:
        raise HTTPException(422, 'Select both airports from the Indian airport directory.')
    return airports[payload.origin], airports[payload.destination]


@router.get('/airports')
def flight_airports(request: Request):
    if not request.app.state.flight_airports:
        raise HTTPException(503, 'The Indian airport directory could not be loaded.')
    airports = sorted(request.app.state.flight_airports.values(), key=lambda airport: airport['code'])
    return {'airports': [{key: value for key, value in airport.items() if key != 'coordinates'} for airport in airports]}


@router.get('/capabilities')
def flight_capabilities(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    estimator = getattr(request.app.state, 'groq_estimator', None)
    return {**request.app.state.fare_service.capabilities(), 'indicative_estimates': estimator.support if estimator else None}


@router.post('/estimate', response_model=IndicativeEstimate)
async def flight_estimate(payload: FlightSearch, request: Request, response: Response):
    origin, destination = itinerary_airports(request, payload)
    estimator: GroqFareEstimator = request.app.state.groq_estimator
    try:
        estimate = await estimator.estimate(payload, flight_distance(origin['coordinates'], destination['coordinates']))
    except EstimateError as error:
        headers = {'Cache-Control': 'no-store'}
        if error.retry_after is not None:
            headers['Retry-After'] = str(error.retry_after)
        return JSONResponse(status_code=error.status, headers=headers, content={'detail': {
            'code': error.code, 'message': error.message, 'retryable': error.retryable,
        }})
    response.headers['Cache-Control'] = 'no-store'
    return estimate


@router.post('/search', response_model=SearchResponse)
async def flight_search(payload: FlightSearch, request: Request, response: Response):
    itinerary_airports(request, payload)
    service: FareService = request.app.state.fare_service
    try:
        result = await service.search(payload)
    except FareError as exc:
        return JSONResponse(status_code=exc.status, content={'detail': {'code': exc.code, 'message': exc.message}},
                            headers={'Cache-Control': 'no-store'})
    response.headers['Cache-Control'] = 'no-store'
    return result
