import {useState, type FormEvent} from 'react';
import {AirportAutocomplete} from './AirportAutocomplete';
import {TravellerSelector} from './TravellerSelector';
import {indiaToday} from './dates';
import {passengerCount, type Airline, type Airport, type Cabin, type FlightQuery, type Journey, type Travellers} from './types';

const cabins: Cabin[] = ['economy', 'premium_economy', 'business', 'first'];
const maximumTravellers = 9;

export function FlightSearchForm({airports, airlines, busy, onSearch, onEdit}: {
  airports: Airport[]; airlines: Airline[]; busy: boolean;
  onSearch: (query: FlightQuery) => void; onEdit: () => void;
}) {
  const [journey, setJourney] = useState<Journey>('one_way');
  const [origin, setOrigin] = useState<Airport | null>(null);
  const [destination, setDestination] = useState<Airport | null>(null);
  const [departure, setDeparture] = useState('');
  const [returnDate, setReturn] = useState('');
  const [party, setParty] = useState<Travellers>({adults: 1, children: 0, infants: 0});
  const [selectedCabin, setCabin] = useState<Cabin>('economy');
  const [preferredAirline, setAirline] = useState('');
  const [error, setError] = useState('');
  const [swapCount, setSwapCount] = useState(0);
  const today = indiaToday();
  const roundTrip = journey === 'round_trip';
  const airline = airlines.some(airline => airline.id === preferredAirline) ? preferredAirline : '';

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
    if (passengerCount(party) > maximumTravellers) {setError(`Choose up to ${maximumTravellers} travellers.`); return;}
    setError('');
    onSearch({origin: origin.code, destination: destination.code, journey, departure_date: departure,
      ...(roundTrip ? {return_date: returnDate} : {}), ...(airline ? {airline} : {}), cabin: selectedCabin, travellers: party});
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
          <input id="departure-date" type="date" min={today} required disabled={busy} value={departure}
            onInput={event => {setDeparture(event.currentTarget.value);edited();}}/>
        </div>
        {roundTrip && <div className="flight-field"><label htmlFor="return-date">Return</label>
          <input id="return-date" type="date" min={departure >= today ? departure : today} required
            disabled={busy} value={returnDate} onInput={event => {setReturn(event.currentTarget.value);edited();}}/>
        </div>}
      </div>
      <TravellerSelector party={party} cabin={selectedCabin} cabins={cabins} childrenAllowed
        infantsAllowed maximum={maximumTravellers} disabled={busy}
        onParty={value => {setParty(value);edited();}} onCabin={value => {setCabin(value);edited();}}/>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="form-actions">
      {airlines.length > 0 && <label className="airline-field">Airline preference
        <select value={airline} disabled={busy} onChange={event => {setAirline(event.target.value);edited();}}>
          <option value="">Any airline</option>
          {airlines.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      </label>}
      <button className="search-flights" type="submit" disabled={busy || !airports.length}>
        {busy ? 'Searching flights…' : 'Search Flights'}
      </button>
    </div>
  </form>;
}
