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
        if not self.research_acknowledged:raise ValueError('Acknowledge the research limitations before requesting raw research output.')
        return self

class FareInterval(BaseModel):
    lower:float
    upper:float
    nominal_coverage:float
    measured_test_coverage:float
    label:str

class PredictionResponse(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    model_id:str
    model_version:str
    estimate:float
    unit:Literal['source fare units']
    currency:Literal[None]
    price_scope:Literal['unknown']
    passenger_basis:Literal['unknown']
    research_only:Literal[True]
    output_kind:Literal['unverified_research_model_output']='unverified_research_model_output'
    unit_verification:Literal['unverified']='unverified'
    coverage_status:str
    historical_support:int
    interval:Literal[None]
    interval_status:Literal['withheld_unvalidated_serving_domain']
    warnings:list[str]
    inputs:dict

class Contribution(BaseModel):
    feature:str
    value:str|float|int
    contribution:float

class ExplanationResponse(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    estimate:float
    baseline:float
    contributions:list[Contribution]
    additive_error:float
    unit:Literal['source fare units']
    currency:Literal[None]=None
    research_only:Literal[True]=True
    unit_verification:Literal['unverified']='unverified'
    interpretation:str
