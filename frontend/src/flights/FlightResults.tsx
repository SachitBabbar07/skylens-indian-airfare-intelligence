import {flightDate} from './dates';
import {cabinNames, passengerCount, type Airline, type FlightQuery, type SearchState} from './types';

const rupees = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0,
});
const rupeesWithPaise = new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR'});

function formatAmount(amount: string) {
  const value = Number(amount);
  return Number.isInteger(value) ? rupees.format(value) : rupeesWithPaise.format(value);
}

function PredictionStatus({query, airlines, message, retry}: {query: FlightQuery; airlines: Airline[]; message: string;
  retry?: () => void}) {
  const count = passengerCount(query.travellers);
  const airline = airlines.find(entry => entry.id === query.airline);
  return <section className="flight-status prediction-status" aria-labelledby="prediction-status-title" role="status">
    <h2 id="prediction-status-title">{query.origin} → {query.destination}</h2>
    <p>{flightDate(query.departure_date)}{query.return_date && ` – ${flightDate(query.return_date)}`}
      {' · '}{query.journey === 'round_trip' ? 'Round trip' : 'One way'}
      {' · '}{cabinNames[query.cabin]} · {count} {count === 1 ? 'traveller' : 'travellers'}</p>
    {airline && <p>Airline preference · {airline.name}</p>}
    <p>{message}</p>
    {retry && <button type="button" className="small-button" onClick={retry}>Try again</button>}
  </section>;
}

export function FlightResults({state, airlines = [], retry}: {state: SearchState; airlines?: Airline[]; retry: () => void}) {
  if (state.status === 'idle') return null;
  if (state.status === 'loading') return <div className="flight-status" role="status">Checking fare sources…</div>;
  if (state.status === 'error') return <PredictionStatus query={state.query} airlines={airlines}
    message={state.message} retry={state.retryable ? retry : undefined}/>;
  const estimate = state.estimate;
  if (estimate.estimation_method === 'unavailable') {
    return <PredictionStatus query={state.query} airlines={airlines} message={estimate.disclaimer}/>;
  }
  const median = formatAmount(estimate.estimated_median);
  const low = estimate.estimated_low ? formatAmount(estimate.estimated_low) : median;
  const high = estimate.estimated_high ? formatAmount(estimate.estimated_high) : median;
  const stops = estimate.stop_profile?.map(n => n === 0 ? 'Nonstop' : `${n} ${n === 1 ? 'stop' : 'stops'}`);
  return <section className="fare-estimate" aria-labelledby="estimate-title">
    <div className="estimate-body">
      <div className="estimate-price">
        <h2 id="estimate-title">SkyLens estimated fare</h2>
        <p className="estimate-amount">{low === high ? low : `${low} – ${high}`}</p>
        {estimate.range_kind === 'interquartile' && low !== high && <p>Median {median}</p>}
        <p>Total for {estimate.passenger_count} {estimate.passenger_count === 1 ? 'traveller' : 'travellers'}</p>
      </div>
      <dl className="estimate-trip">
        <div><dt>Route</dt><dd>{estimate.origin} → {estimate.destination}</dd></div>
        <div><dt>Journey</dt><dd>{estimate.journey_type === 'round_trip' ? 'Round trip' : 'One way'}</dd></div>
        <div><dt>Cabin</dt><dd>{cabinNames[estimate.cabin_class]}</dd></div>
        {stops && <div><dt>{stops.length === 2 ? 'Stops (out / back)' : 'Stops'}</dt><dd>{stops.join(' / ')}</dd></div>}
        <div className="estimate-dates"><dt>Travel dates</dt><dd>{flightDate(estimate.departure_date)}
          {estimate.return_date && ` – ${flightDate(estimate.return_date)}`}</dd></div>
      </dl>
    </div>
    <div className="estimate-source">
      <p className="estimate-method">{estimate.estimation_method === 'historical_ml' ?
        'Historical ML estimate' : 'Market-based indicative estimate'}</p>
      <p>{estimate.disclaimer}</p>
    </div>
  </section>;
}
