export type Journey = 'one_way' | 'round_trip';
export type Airline = {id: string; name: string};
export type Cabin = 'economy' | 'premium_economy' | 'business' | 'first';
export const cabinNames: Record<Cabin, string> = {
  economy: 'Economy', premium_economy: 'Premium Economy', business: 'Business', first: 'First Class',
};

export type Airport = {code: string; name: string; city: string; state: string; has_historical_evidence: boolean};
export type Travellers = {adults: number; children: number; infants: number};
export const passengerCount = (party: Travellers) => party.adults + party.children + party.infants;

export type SearchSupport = {
  journeys: Journey[]; cabins: Cabin[]; children: boolean; infants: boolean;
  max_travellers: number; last_departure_date: string | null; airlines: string[];
};
export type SearchCapabilities = {live_quotes: SearchSupport | null; ml_estimates: SearchSupport | null;
  today: string; airlines: Airline[]};
export type FlightQuery = {
  origin: string; destination: string; journey: Journey; departure_date: string;
  return_date?: string; cabin: Cabin; airline?: string; travellers: Travellers;
};
type EstimateContext = {
  origin: string; destination: string; departure_date: string; return_date: string | null;
  journey_type: Journey; passenger_count: number; cabin_class: Cabin;
  coverage_status: 'validated' | 'unsupported' | 'unavailable';
  source_status: {model: string; market: string}; disclaimer: string;
};
export type PricedEstimate = EstimateContext & {
  estimation_method: 'historical_ml' | 'market_reference';
  estimated_low: string; estimated_high: string; currency: 'INR'; price_scope: 'party_total';
};
export type FareEstimate = PricedEstimate | (EstimateContext & {
  estimation_method: 'unavailable';
  estimated_low: null; estimated_high: null; currency: null; price_scope: null;
});
export type SearchState = {status: 'idle'} | {status: 'loading'} |
  {status: 'error'; message: string; retryable: boolean; query: FlightQuery} |
  {status: 'success'; estimate: FareEstimate; query: FlightQuery};
