export type Journey = 'one_way' | 'round_trip';
export type Cabin = 'economy' | 'premium_economy' | 'business' | 'first';
export const cabinNames: Record<Cabin, string> = {
  economy: 'Economy', premium_economy: 'Premium Economy', business: 'Business', first: 'First Class',
};

export type Airport = {code: string; name: string; city: string; state: string; has_historical_evidence: boolean};
export type Travellers = {adults: number; children: number; infants: number};
export const passengerCount = (party: Travellers) => party.adults + party.children + party.infants;

export type SearchSupport = {
  journeys: Journey[]; cabins: Cabin[]; children: boolean; infants: boolean;
  max_travellers: number; last_departure_date: string | null;
};
export type SearchCapabilities = {live_quotes: SearchSupport | null; ml_estimates: SearchSupport | null;
  indicative_estimates: SearchSupport | null; today: string};
export type FlightQuery = {
  origin: string; destination: string; journey: Journey; departure_date: string;
  return_date?: string; cabin: Cabin; travellers: Travellers;
};
export type Fare = {amount: string; currency: string; basis: 'party_total'; taxes: string; fees: string};
export type FlightLeg = {
  origin: string; destination: string; departure: string; arrival: string; airlines: string[];
  duration_minutes: number | null; stops: number | null;
};
type PricedResult = {id: string; source_name: string; retrieved_at: string; journey: Journey; cabin: Cabin; travellers: Travellers; fare: Fare};
export type FareResult = (PricedResult & {source: 'live_quote'; availability: 'available'; legs: FlightLeg[];
  baggage: string | null; conditions: string | null}) | (PricedResult & {source: 'ml_estimate'});

export type IndicativeEstimate = {estimated_low: number; estimated_high: number; currency: 'INR'; journey_type: Journey;
  origin: string; destination: string; departure_date: string; return_date: string | null; cabin_class: Cabin;
  passenger_count: number; estimation_source: 'groq_indicative'; disclaimer: string};

export type SearchState = {status: 'idle'} | {status: 'loading'} | {status: 'error'; message: string; retryable: boolean} |
  {status: 'estimate'; estimate: IndicativeEstimate} | {status: 'success'; results: FareResult[]; query: FlightQuery};
