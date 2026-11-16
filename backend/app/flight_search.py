"""Flight search endpoints backed by the reviewed airport master and fare service."""

import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.app.fare_service import FareError, FareService
from backend.app.flight_fares import FlightSearch, SearchResponse


router = APIRouter(prefix='/flights', tags=['Flight search'])


def load_airports(root: Path) -> dict[str, dict]:
    with (root / 'reports/airport_fare_coverage.csv').open(encoding='utf-8', newline='') as source:
        return {
            row['iata_code']: {
                'code': row['iata_code'], 'name': row['name'], 'city': row['municipality'], 'state': row['state'],
                'has_historical_evidence': int(row['fare_endpoint_observations']) > 0,
            }
            for row in csv.DictReader(source) if row['iso_country'] == 'IN' and row['iata_code']
        }


@router.get('/airports')
def flight_airports(request: Request):
    if not request.app.state.flight_airports:
        raise HTTPException(503, 'The Indian airport directory could not be loaded.')
    return {'airports': sorted(request.app.state.flight_airports.values(), key=lambda airport: airport['code'])}


@router.get('/capabilities')
def flight_capabilities(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return request.app.state.fare_service.capabilities()


@router.post('/search', response_model=SearchResponse)
async def flight_search(payload: FlightSearch, request: Request, response: Response):
    airports = request.app.state.flight_airports
    if not airports:
        raise HTTPException(503, 'The Indian airport directory could not be loaded.')
    if payload.origin not in airports or payload.destination not in airports:
        raise HTTPException(422, 'Select both airports from the Indian airport directory.')
    service: FareService = request.app.state.fare_service
    try:
        result = await service.search(payload)
    except FareError as exc:
        return JSONResponse(status_code=exc.status, content={'detail': {'code': exc.code, 'message': exc.message}},
                            headers={'Cache-Control': 'no-store'})
    response.headers['Cache-Control'] = 'no-store'
    return result
