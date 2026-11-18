import {useState} from 'react';
import {flightDate, flightTime} from './dates';
import {fareComparisonUrl} from './fareComparison';
import {cabinNames, passengerCount, type Airline, type Fare, type FareResult, type FlightLeg, type FlightQuery,
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

const travelDate = new Intl.DateTimeFormat('en-IN', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});

function ComparisonCard({query, airlines, message, retry}: {query: FlightQuery; airlines: Airline[]; message?: string;
  retry?: () => void}) {
  const formatDate = (date: string) => travelDate.format(new Date(`${date}T00:00:00Z`));
  const count = passengerCount(query.travellers);
  const airline = airlines.find(entry => entry.id === query.airline);
  return <section className="flight-status fare-comparison" aria-labelledby="comparison-title" aria-live="polite">
    <h2 id="comparison-title">{query.origin} → {query.destination}</h2>
    <p>{formatDate(query.departure_date)}{query.return_date && ` – ${formatDate(query.return_date)}`}
      {' · '}{query.journey === 'round_trip' ? 'Round trip' : 'One way'}
      {' · '}{cabinNames[query.cabin]} · {count} {count === 1 ? 'traveller' : 'travellers'}</p>
    <p>{message ?? 'SkyLens has no sourced fare for this trip. Compare prices on Google Flights.'}</p>
    {airline && <p>Airline filter {airline.name}</p>}
    <div className="comparison-actions">
      <a className="comparison-link" href={fareComparisonUrl(query)} target="_blank" rel="noopener noreferrer">
        Check current fares <span aria-hidden="true">↗</span>
      </a>
      {retry && <button type="button" className="small-button" onClick={retry}>Try again</button>}
    </div>
  </section>;
}

export function FlightResults({state, airlines = [], retry}: {state: SearchState; airlines?: Airline[]; retry: () => void}) {
  const [sort, setSort] = useState<Sort>('price');
  if (state.status === 'idle') return null;
  if (state.status === 'loading') return <div className="flight-status" role="status">
    Searching for available flights…
  </div>;
  if (state.status === 'comparison') return <ComparisonCard query={state.query} airlines={airlines}/>;
  if (state.status === 'error') return <ComparisonCard query={state.query} airlines={airlines}
    message={state.message} retry={state.retryable ? retry : undefined}/>;
  if (!state.results.length) return <ComparisonCard query={state.query} airlines={airlines}
    message="The connected source returned no fares for this trip."/>;
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
