"""Validated research-only API contracts; model metadata defines selectable values."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

class PredictionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    model_id:Literal['cabin_2023','network_2020']
    origin:str=Field(pattern=r'^[A-Z]{3}$')
    destination:str=Field(pattern=r'^[A-Z]{3}$')
    airline:str=Field(min_length=1,max_length=120)
    cabin_class:str=Field(min_length=1,max_length=40)
    journey_type:Literal['single_direction_record']='single_direction_record'
    days_left:int=Field(ge=0,le=365)
    duration_minutes:float=Field(gt=0,le=4320)
    stops:int=Field(ge=0,le=4)
    departure_hour:float=Field(ge=0,lt=24)
    research_acknowledged:bool

    @model_validator(mode='after')
    def check_context(self):
        if self.origin==self.destination:raise ValueError('Choose different origin and destination airports.')
        if not self.research_acknowledged:raise ValueError('Acknowledge the research limitations before requesting an estimate.')
        return self

class FareInterval(BaseModel):
    lower:float
    upper:float
    nominal_coverage:float
    measured_test_coverage:float
    label:str

class PredictionResponse(BaseModel):
    model_id:str
    model_version:str
    estimate:float
    unit:str
    currency:str|None
    price_scope:str
    passenger_basis:str
    research_only:bool
    coverage_status:str
    historical_support:int
    interval:FareInterval|None
    interval_status:str
    warnings:list[str]
    inputs:dict

class Contribution(BaseModel):
    feature:str
    value:str|float|int
    contribution:float

class ExplanationResponse(BaseModel):
    estimate:float
    baseline:float
    contributions:list[Contribution]
    additive_error:float
    unit:str
    interpretation:str
