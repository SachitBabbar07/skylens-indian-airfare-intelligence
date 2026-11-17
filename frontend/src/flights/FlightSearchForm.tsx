import {useState, type FormEvent} from 'react';
import {AirportAutocomplete} from './AirportAutocomplete';
import {TravellerSelector} from './TravellerSelector';
import {indiaToday} from './dates';
import {passengerCount, type Airport, type Cabin, type FlightQuery, type Journey, type SearchCapabilities, type Travellers} from './types';

export function FlightSearchForm({airports, capabilities, indicative, busy, onSearch, onEdit}: {
  airports: Airport[]; capabilities: SearchCapabilities | null; indicative: boolean; busy: boolean;
  onSearch: (query: FlightQuery) => void; onEdit: () => void;
}) {
  const [journey, setJourney] = useState<Journey>('one_way');
  const [origin, setOrigin] = useState<Airport | null>(null);
  const [destination, setDestination] = useState<Airport | null>(null);
  const [departure, setDeparture] = useState('');
  const [returnDate, setReturn] = useState('');
  const [party, setParty] = useState<Travellers>({adults: 1, children: 0, infants: 0});
  const [selectedCabin, setCabin] = useState<Cabin>('economy');
  const [error, setError] = useState('');
  const [swapCount, setSwapCount] = useState(0);
  const today = indiaToday();
  const roundTrip = journey === 'round_trip';
  const sources = (indicative ? [capabilities?.ml_estimates, capabilities?.indicative_estimates] :
    [capabilities?.live_quotes, capabilities?.ml_estimates]).filter(source => source != null);
  const journeySources = sources.filter(source => source.journeys.includes(journey));
  const cabins = [...new Set((journeySources.length ? journeySources : sources).flatMap(source => source.cabins))];
  const options = cabins.length ? cabins : ['economy' as const];
  const cabin = options.includes(selectedCabin) ? selectedCabin : options[0];
  const selectedSources = journeySources.filter(source => source.cabins.includes(cabin));
  const childrenAllowed = selectedSources.some(source => source.children);
  const infantsAllowed = selectedSources.some(source => source.infants);
  const travellers = {...party, children: childrenAllowed ? party.children : 0, infants: infantsAllowed ? party.infants : 0};
  const maximum = selectedSources.length ? Math.max(...selectedSources.map(source => source.max_travellers)) : 9;
  const lastDate = selectedSources.length && selectedSources.every(source => source.last_departure_date)
    ? selectedSources.flatMap(source => source.last_departure_date ?? []).sort().at(-1) : undefined;

  function edited() {setError(''); onEdit();}
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (!origin || !destination || origin.code === destination.code) {
      setError('Select two different airports from the suggestions.');
      return;
    }
    if (!departure || departure < today) {setError('Choose a departure date from today onward.'); return;}
    if (roundTrip && (!returnDate || returnDate < departure)) {
      setError('Choose a return date on or after departure.');
      return;
    }
    if (passengerCount(travellers) > maximum) {setError(`Choose up to ${maximum} travellers.`); return;}
    setError('');
    onSearch({origin: origin.code, destination: destination.code, journey, departure_date: departure,
      ...(roundTrip ? {return_date: returnDate} : {}), cabin, travellers});
  }

  return <form className="flight-panel" onSubmit={submit} aria-label="Flight search" aria-busy={busy}>
    <fieldset className="journey-options" disabled={busy}>
      <legend className="flight-sr-only">Journey type</legend>
      <label><input type="radio" name="journey" checked={!roundTrip}
        onChange={() => {setJourney('one_way');setReturn('');edited();}}/> One Way</label>
      <label><input type="radio" name="journey" checked={roundTrip}
        onChange={() => {setJourney('round_trip');edited();}}/> Round Trip</label>
    </fieldset>

    <div className={`flight-fields${roundTrip ? ' has-return' : ''}`}>
      <div className="route-fields">
        <AirportAutocomplete key={`from-${swapCount}`} label="From" value={origin} airports={airports} excludedCode={destination?.code}
          disabled={busy} onChange={value => {setOrigin(value);edited();}}/>
        <button className="swap-airports" aria-label="Swap airports" type="button"
          disabled={busy || (!origin && !destination)} onClick={() => {
            setOrigin(destination);setDestination(origin);setSwapCount(count => count + 1);edited();
          }}>⇄</button>
        <AirportAutocomplete key={`to-${swapCount}`} label="To" value={destination} airports={airports} excludedCode={origin?.code}
          disabled={busy} onChange={value => {setDestination(value);edited();}}/>
      </div>
      <div className="date-fields">
        <div className="flight-field"><label htmlFor="departure-date">Departure</label>
          <input id="departure-date" type="date" min={today} max={lastDate} required disabled={busy} value={departure}
            onInput={event => {setDeparture(event.currentTarget.value);edited();}}/>
        </div>
        {roundTrip && <div className="flight-field"><label htmlFor="return-date">Return</label>
          <input id="return-date" type="date" min={departure >= today ? departure : today} max={lastDate} required
            disabled={busy} value={returnDate} onInput={event => {setReturn(event.currentTarget.value);edited();}}/>
        </div>}
      </div>
      <TravellerSelector party={travellers} cabin={cabin} cabins={options} childrenAllowed={childrenAllowed}
        infantsAllowed={infantsAllowed} maximum={maximum} disabled={busy}
        onParty={value => {setParty(value);edited();}} onCabin={value => {setCabin(value);edited();}}/>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="form-actions">
      <button className="search-flights" type="submit" disabled={busy || !airports.length}>
        {busy ? 'Searching flights…' : 'Search Flights'}
      </button>
    </div>
  </form>;
}
