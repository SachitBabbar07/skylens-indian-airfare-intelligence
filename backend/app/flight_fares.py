"""Customer fare contracts. The historical research models are not fare sources."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


IST = ZoneInfo('Asia/Kolkata')
IATA = Annotated[str, StringConstraints(pattern=r'^[A-Z]{3}$')]
Cabin = Literal['economy', 'premium_economy', 'business', 'first']
Journey = Literal['one_way', 'round_trip']
# DGCA scheduled domestic passenger traffic, September 2026.
DOMESTIC_AIRLINES = {
    'air_india': 'Air India', 'air_india_express': 'Air India Express', 'akasa_air': 'Akasa Air',
    'alliance_air': 'Alliance Air', 'fly91': 'FLY91', 'indiaone_air': 'IndiaOne Air',
    'indigo': 'IndiGo', 'spicejet': 'SpiceJet', 'star_air': 'Star Air',
}


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Travellers(Contract):
    adults: Annotated[int, Field(strict=True, ge=1, le=9)] = 1
    children: Annotated[int, Field(strict=True, ge=0, le=9)] = 0
    infants: Annotated[int, Field(strict=True, ge=0, le=9)] = 0

    @model_validator(mode='after')
    def validate_party(self):
        if self.infants > self.adults:
            raise ValueError('Select at least one adult per infant.')
        if self.total > 9:
            raise ValueError('Select at most nine travellers.')
        return self

    @property
    def total(self) -> int:
        return self.adults + self.children + self.infants


class FlightSearch(Contract):
    origin: IATA
    destination: IATA
    journey: Journey
    departure_date: date
    return_date: date | None = None
    cabin: Cabin = 'economy'
    airline: str | None = None
    travellers: Travellers = Field(default_factory=Travellers)

    @field_validator('airline')
    @classmethod
    def validate_airline(cls, airline: str | None) -> str | None:
        if airline is not None and airline not in DOMESTIC_AIRLINES:
            raise ValueError('Select a listed domestic airline or Any airline.')
        return airline

    @model_validator(mode='after')
    def validate_journey(self):
        if self.origin == self.destination:
            raise ValueError('Choose different origin and destination airports.')
        if self.departure_date < datetime.now(IST).date():
            raise ValueError('Departure date must be today or later in India.')
        if self.journey == 'round_trip':
            if self.return_date is None or self.return_date < self.departure_date:
                raise ValueError('Choose a return date on or after departure.')
        elif self.return_date is not None:
            raise ValueError('Remove the return date for one-way travel.')
        return self


class SearchSupport(Contract):
    journeys: list[Journey]
    cabins: list[Cabin]
    children: bool = False
    infants: bool = False
    max_travellers: Annotated[int, Field(ge=1, le=9)] = 9
    last_departure_date: date | None = None
    airlines: list[str] = Field(default_factory=list)

    def accepts(self, request: FlightSearch) -> bool:
        return (
            request.journey in self.journeys and request.cabin in self.cabins
            and (request.airline is None or request.airline in self.airlines)
            and (self.children or request.travellers.children == 0)
            and (self.infants or request.travellers.infants == 0)
            and request.travellers.total <= self.max_travellers
            and (self.last_departure_date is None
                 or (request.return_date or request.departure_date) <= self.last_departure_date)
        )


class Fare(Contract):
    amount: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=4)]
    currency: Annotated[str, StringConstraints(pattern=r'^[A-Z]{3}$')]
    basis: Literal['party_total']
    taxes: Literal['included', 'excluded', 'unknown']
    fees: Literal['included', 'excluded', 'unknown']

    @field_validator('currency')
    @classmethod
    def require_documented_currency(cls, currency: str) -> str:
        # Sources normalize their documented currencies before returning a fare.
        if currency in {'XXX', 'XTS'}:
            raise ValueError('A priced result requires an actual currency.')
        return currency


class FlightLeg(Contract):
    origin: IATA
    destination: IATA
    departure: AwareDatetime
    arrival: AwareDatetime
    airlines: Annotated[list[Annotated[str, StringConstraints(min_length=1, max_length=100)]], Field(min_length=1)]
    duration_minutes: Annotated[int, Field(strict=True, gt=0)] | None = None
    stops: Annotated[int, Field(strict=True, ge=0)] | None = None

    @model_validator(mode='after')
    def validate_times(self):
        if self.origin == self.destination or self.arrival <= self.departure:
            raise ValueError('Invalid itinerary endpoints or times.')
        return self


class PricedResult(Contract):
    id: Annotated[str, StringConstraints(min_length=1, max_length=150)]
    source_name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    retrieved_at: AwareDatetime
    journey: Journey
    cabin: Cabin
    travellers: Travellers
    fare: Fare


class LiveQuote(PricedResult):
    source: Literal['live_quote']
    availability: Literal['available']
    legs: Annotated[list[FlightLeg], Field(min_length=1, max_length=2)]
    baggage: str | None = None
    conditions: str | None = None


class ModelEstimate(PricedResult):
    source: Literal['ml_estimate']


FareResult = Annotated[LiveQuote | ModelEstimate, Field(discriminator='source')]


class SearchResponse(Contract):
    results: list[FareResult]


class LiveFareProvider(Protocol):
    support: SearchSupport

    def supports_route(self, request: FlightSearch) -> bool: ...

    async def search(self, request: FlightSearch) -> list[LiveQuote]: ...


class ValidatedFareModel(Protocol):
    support: SearchSupport

    def supports_route(self, request: FlightSearch) -> bool: ...

    async def search(self, request: FlightSearch) -> list[ModelEstimate]: ...
