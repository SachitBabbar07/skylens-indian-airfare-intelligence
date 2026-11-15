"""Fail-closed customer capability. Research metadata is not a product approval.

No current artifact has a documented, validated ticket-price target. There is
deliberately no environment variable, currency-label shortcut or request flag
that can promote a research model to customer fare estimation.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

FARE_UNAVAILABLE_MESSAGE = "Fare prediction is temporarily unavailable because the training data's price definition has not yet been verified."
UNVERIFIED_UNIT_LABEL = "unverified model-output units"
MISSING_EVIDENCE = (
    "Documented target currency",
    "Whether taxes and mandatory fees are included",
    "Whether the target is a total fare or base fare",
    "Per-passenger versus complete-booking price basis",
    "Genuine one-way, return or other booking type",
    "Original source documentation establishing those meanings",
    "Independent evaluation for the intended customer prediction scope",
)
router = APIRouter()


def product_capabilities():
    return {
        "fare_estimation": {
            "available": False,
            "status": "unavailable_unverified_target",
            "message": FARE_UNAVAILABLE_MESSAGE,
            "currency": None,
            "approved_model_id": None,
            "missing_evidence": list(MISSING_EVIDENCE),
        },
        "research": {
            "enabled": True,
            "requires_loaded_artifacts": True,
            "acknowledgement_required": True,
            "unit_label": UNVERIFIED_UNIT_LABEL,
            "output_is_ticket_price": False,
            "output_is_booking_quote": False,
            "prediction_endpoint": "/research/predict",
            "explanation_endpoint": "/research/explain",
        },
    }


@router.get("/capabilities", tags=["Product status"])
def capabilities():
    return product_capabilities()


UNAVAILABLE_RESPONSE = {503: {
    "description": FARE_UNAVAILABLE_MESSAGE,
    "content": {"application/json": {"example": {"detail": product_capabilities()["fare_estimation"]}}},
}}


@router.post("/fare-estimate", tags=["Unavailable customer capability"], status_code=503, responses=UNAVAILABLE_RESPONSE)
@router.post("/predict", tags=["Unavailable customer capability"], status_code=503, deprecated=True, responses=UNAVAILABLE_RESPONSE)
@router.post("/explain", tags=["Unavailable customer capability"], status_code=503, deprecated=True, responses=UNAVAILABLE_RESPONSE)
def customer_fare_unavailable():
    """Never call a model or convert an undocumented target into a ticket price.

The former generic paths are blocked too, so cached/older price-card clients
cannot obtain new outputs from them. Use explicitly acknowledged research paths.
"""
    return JSONResponse(status_code=503, content={"detail": product_capabilities()["fare_estimation"]})
