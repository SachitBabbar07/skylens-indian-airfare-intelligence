"""Read-only acquisition review and empty manual-intake assets. Never infer/train."""
import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from skylens.quotes import Quote, SourceGrant

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix='/acquisition', tags=['Evidence-gated data acquisition'])


def review_status(root: Path = ROOT):
    path = root/'data/metadata/phase5/acquisition_decision.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['customer_fare_prediction_available'] is not False
                or data['training_automatically_enabled'] is not False):
            raise ValueError('Acquisition metadata cannot approve customer prediction')
        for key in ['verified_one_way_observations', 'verified_round_trip_observations', 'approved_sources']:
            if type(data[key]) is not int or data[key] < 0:
                raise ValueError('Invalid acquisition counts')
        return data
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, 'The acquisition review is unavailable. Customer fare prediction remains disabled.') from exc


@router.get('/status')
def status():
    return review_status()


@router.get('/template.csv')
def template():
    buffer = io.StringIO(newline='')
    csv.writer(buffer).writerow(Quote.model_fields)
    return Response(buffer.getvalue(), media_type='text/csv', headers={
        'Content-Disposition': 'attachment; filename="skylens-quote-template.csv"',
        'X-Content-Type-Options': 'nosniff',
    })


@router.get('/schema')
def schema():
    return {'quote': Quote.model_json_schema(), 'source_grant': SourceGrant.model_json_schema(),
            'training_automatically_enabled': False}
