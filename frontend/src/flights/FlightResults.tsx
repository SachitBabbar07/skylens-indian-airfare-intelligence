import {useState} from 'react';
import {flightDate, flightTime} from './dates';
import {ESTIMATE_UNAVAILABLE, cabinNames, passengerCount, type Fare, type FareResult, type FlightLeg, type IndicativeEstimate,
  type SearchState} from './types';

type Sort = 'provider' | 'price' | 'duration' | 'departure';

export function formatFare(fare: Fare) {
  const amount = Number(fare.amount);
  if (fare.basis !== 'party_total' || !/^[A-Z]{3}$/.test(fare.currency) || ['XXX', 'XTS'].includes(fare.currency) ||
      !Number.isFinite(amount) || amount <= 0) return null;
  return new Intl.NumberFormat('en-IN', {style: 'currency', currency: fare.currency,
    currencyDisplay: fare.currency === 'INR' ? 'symbol' : 'code', maximumFractionDigits: 4}).format(amount);
}

export function sortResults(results: FareResult[], requested: Sort) {
  const sameCurrency = new Set(results.map(result => result.fare.currency)).size <= 1;
  const duration = (result: FareResult) => result.source === 'live_quote' && result.legs.every(leg => leg.duration_minutes !== null)
    ? result.legs.reduce((sum, leg) => sum + (leg.duration_minutes ?? 0), 0) : Infinity;
  const departure = (result: FareResult) => result.source === 'live_quote' ? Date.parse(result.legs[0].departure) : Infinity;
  if (requested === 'price' && sameCurrency) return [...results].sort((a, b) => Number(a.fare.amount) - Number(b.fare.amount));
  if (requested === 'duration') return [...results].sort((a, b) => duration(a) - duration(b));
  if (requested === 'departure') return [...results].sort((a, b) => departure(a) - departure(b));
  return results;
}

function Leg({leg, label}: {leg: FlightLeg; label?: string}) {
  const duration = leg.duration_minutes;
  return <div className="itinerary-leg">
    <div className="leg-carrier">{label && <small>{label}</small>}<strong>{leg.airlines.join(' · ')}</strong></div>
    <div><strong>{flightTime(leg.departure)} · {leg.origin}</strong><small>{flightDate(leg.departure)}</small></div>
    <div className="leg-connection">
      {duration !== null && <span>{duration >= 60 ? `${Math.floor(duration / 60)}h ` : ''}{duration % 60}m</span>}
      {leg.stops !== null && <small>{leg.stops === 0 ? 'Non-stop' : `${leg.stops} ${leg.stops === 1 ? 'stop' : 'stops'}`}</small>}
    </div>
    <div><strong>{flightTime(leg.arrival)} · {leg.destination}</strong><small>{flightDate(leg.arrival)}</small></div>
  </div>;
}

function FlightResultCard({result}: {result: FareResult}) {
  const price = formatFare(result.fare);
  if (!price) return <article className="flight-result"><p>The fare currency or total is unavailable.</p></article>;
  const count = passengerCount(result.travellers);
  const live = result.source === 'live_quote';
  const inclusion = (name: string, status: string) => status === 'unknown' ? `${name} information unavailable` : `${name} ${status}`;
  return <article className="flight-result">
    <div className="result-itinerary">
      <p className="fare-source">{live ? 'Live Fare Quote' : 'ML Estimated Fare'} · {result.source_name}</p>
      {live && result.legs.map((leg, index) => <Leg key={`${leg.origin}-${leg.departure}`} leg={leg}
        label={result.journey === 'round_trip' ? index === 0 ? 'Outbound' : 'Return' : undefined}/>)}
      <p className="result-details">{cabinNames[result.cabin]} · {result.journey === 'one_way' ? 'One Way' : 'Round Trip'}
        {live && ' · Available'} · Retrieved {flightDate(result.retrieved_at)}, {flightTime(result.retrieved_at)} IST</p>
      {live && (result.baggage || result.conditions) && <details><summary>Baggage and fare conditions</summary>
        {result.baggage && <p>{result.baggage}</p>}{result.conditions && <p>{result.conditions}</p>}
      </details>}
    </div>
    <div className="result-price"><strong>{price}</strong>
      <span>Total for {count} {count === 1 ? 'traveller' : 'travellers'}</span>
      <small>{inclusion('Taxes', result.fare.taxes)} · {inclusion('Fees', result.fare.fees)}</small>
    </div>
  </article>;
}

const rupees = new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR', maximumFractionDigits: 0});
const travelDate = new Intl.DateTimeFormat('en-IN', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});

function EstimateCard({estimate}: {estimate: IndicativeEstimate}) {
  const departure = travelDate.format(new Date(`${estimate.departure_date}T00:00:00Z`));
  const returnDate = estimate.return_date && travelDate.format(new Date(`${estimate.return_date}T00:00:00Z`));
  return <section className="flight-status indicative-estimate" aria-labelledby="indicative-title" aria-live="polite">
    <h2 id="indicative-title">SkyLens Indicative Fare Estimate</h2>
    <p className="indicative-route"><strong>{estimate.origin} → {estimate.destination}</strong> · {estimate.journey_type === 'round_trip' ? 'Round Trip' : 'One Way'}
      {' · '}{cabinNames[estimate.cabin_class]}</p>
    <p>Departure {departure}{returnDate && ` · Return ${returnDate}`}</p>
    <p className="indicative-price">{rupees.format(estimate.estimated_low)} – {rupees.format(estimate.estimated_high)}</p>
    <p>Estimated total for {estimate.passenger_count} {estimate.passenger_count === 1 ? 'traveller' : 'travellers'}</p>
    <p className="indicative-disclosure">AI-generated indicative estimate. Not a live airline quote or guaranteed ticket price. Actual fares may differ.</p>
  </section>;
}

export function FlightResults({state, unavailable, indicative = false, retry}: {state: SearchState; unavailable: boolean;
  indicative?: boolean; retry: () => void}) {
  const [sort, setSort] = useState<Sort>('price');
  if (state.status === 'idle') {
    if (indicative) return <div className="flight-status" role="status">
      {unavailable ? ESTIMATE_UNAVAILABLE : <>
        <strong>AI-assisted fare estimates</strong>
        <p>SkyLens sends your selected trip details to Groq to generate an approximate fare range.</p>
      </>}
    </div>;
    return unavailable ? <div className="flight-status" role="status">
      <strong>Live fares unavailable</strong><p>Flight search needs a connected fare provider.</p>
    </div> : null;
  }
  if (state.status === 'loading') return <div className="flight-status" role="status">
    {indicative ? 'Generating an indicative fare estimate…' : 'Searching for available flights…'}
  </div>;
  if (state.status === 'error') return <div className="flight-status" role="alert">
    {!indicative && <strong>Search unavailable</strong>}<p>{state.message}</p>
    {state.retryable && <button type="button" className="small-button" onClick={retry}>Try again</button>}
  </div>;
  if (state.status === 'estimate') return <EstimateCard estimate={state.estimate}/>;
  if (!state.results.length) return <div className="flight-status" role="status">
    <strong>No flights found</strong><p>Try a different date, airport or cabin.</p>
  </div>;
  const mixed = new Set(state.results.map(result => result.fare.currency)).size > 1;
  const hasDuration = state.results.some(result => result.source === 'live_quote' && result.legs.every(leg => leg.duration_minutes !== null));
  const hasDeparture = state.results.some(result => result.source === 'live_quote');
  const activeSort = (sort === 'price' && mixed) || (sort === 'duration' && !hasDuration) ||
    (sort === 'departure' && !hasDeparture) ? 'provider' : sort;
  return <section className="flight-results" aria-labelledby="flight-results-title">
    <div className="results-header"><div><h2 id="flight-results-title">{state.query.origin} → {state.query.destination}</h2>
      <p role="status">{state.results.length} {state.results.length === 1 ? 'result' : 'results'}</p></div>
      <label>Sort by<select value={activeSort} onChange={event => setSort(event.target.value as Sort)}>
        {!mixed && <option value="price">Lowest fare</option>}
        {hasDuration && <option value="duration">Shortest duration</option>}
        {hasDeparture && <option value="departure">Departure time</option>}
        <option value="provider">Source order</option>
      </select></label>
    </div>
    {mixed && <p className="currency-note">Fares are shown in their original currencies.</p>}
    {sortResults(state.results, activeSort).map(result => <FlightResultCard key={result.id} result={result}/>)}
  </section>;
}
