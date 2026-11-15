"""Portable product-boundary checks. Numerical fixtures are software-only."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.capabilities import FARE_UNAVAILABLE_MESSAGE, router
from backend.app.schemas import PredictionResponse, ExplanationResponse


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_customer_capability_requires_semantics_and_scope_evaluation(client, monkeypatch):
    monkeypatch.setenv('SKYLENS_CURRENCY', 'INR')
    monkeypatch.setenv('SKYLENS_ENABLE_FARE_PREDICTION', 'true')
    result = client.get('/capabilities').json()
    customer = result['fare_estimation']
    assert customer['available'] is False
    assert customer['currency'] is None and customer['approved_model_id'] is None
    assert customer['message'] == FARE_UNAVAILABLE_MESSAGE
    assert len(customer['missing_evidence']) == 7
    assert any('Independent evaluation' in item for item in customer['missing_evidence'])
    assert result['research']['enabled'] is True
    assert result['research']['unit_label'] == 'unverified model-output units'
    assert result['research']['output_is_ticket_price'] is False
    assert result['research']['output_is_booking_quote'] is False


@pytest.mark.parametrize('path', ['/predict', '/explain', '/fare-estimate'])
@pytest.mark.parametrize('body', [{}, {'currency': 'INR', 'research_acknowledged': True,
                                    'enable_customer': True, 'exchange_rate': 1}])
def test_legacy_and_customer_requests_fail_closed_without_loading_any_model(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 503
    detail = response.json()['detail']
    assert detail['message'] == FARE_UNAVAILABLE_MESSAGE
    assert detail['available'] is False and detail['currency'] is None
    assert 'estimate' not in detail and 'quote' not in detail


def raw_result():
    return dict(model_id='software_fixture', model_version='fixture', estimate=12345.6789,
                unit='source fare units', currency=None, price_scope='unknown',
                passenger_basis='unknown', research_only=True, coverage_status='research',
                historical_support=50, interval=None,
                interval_status='withheld_unvalidated_serving_domain', warnings=[], inputs={})


@pytest.mark.parametrize('changes', [dict(currency='INR'), dict(unit='INR'),
    dict(unit='rupees'), dict(research_only=False), dict(unit_verification='verified'),
    dict(output_kind='ticket_price'), dict(price_scope='total_fare'),
    dict(passenger_basis='per_person'), dict(estimate=float('nan')),
    dict(interval={'lower': 1, 'upper': 2}), dict(interval_status='validated')])
def test_research_response_cannot_be_relabelled_or_promoted(changes):
    with pytest.raises(ValidationError):
        PredictionResponse(**{**raw_result(), **changes})


def test_raw_number_is_preserved_without_invented_currency_conversion():
    result = PredictionResponse(**raw_result()).model_dump()
    assert result['estimate'] == 12345.6789
    assert result['currency'] is None and result['unit_verification'] == 'unverified'
    assert result['output_kind'] == 'unverified_research_model_output'


@pytest.mark.parametrize('changes', [dict(currency='INR'), dict(unit='INR'),
                                    dict(unit_verification='verified'), dict(research_only=False)])
def test_shap_response_cannot_claim_monetary_units(changes):
    body = dict(estimate=12, baseline=10, contributions=[], additive_error=0,
                unit='source fare units', interpretation='Unverified research contributions.')
    with pytest.raises(ValidationError):
        ExplanationResponse(**{**body, **changes})
