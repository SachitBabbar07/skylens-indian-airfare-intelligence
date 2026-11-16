import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {api} from './api';
import {FlightSearchForm} from './flights/FlightSearchForm';
import {FlightResults} from './flights/FlightResults';
import {useFlightSearch} from './flights/useFlightSearch';
import type {Airport, SearchCapabilities} from './flights/types';
import './flights/flights.css';

function FlightApp() {
  const [airports, setAirports] = useState<Airport[]>([]);
  const [capabilities, setCapabilities] = useState<SearchCapabilities | null>(null);
  const [loadError, setLoadError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const {state, search, clear, retry} = useFlightSearch();

  useEffect(() => {
    const request = new AbortController();
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(15_000)]);
    setLoadError('');
    void Promise.allSettled([
      api<{airports: Airport[]}>('/flights/airports', undefined, signal),
      api<SearchCapabilities>('/flights/capabilities', undefined, signal),
    ]).then(([directory, sources]) => {
      if (request.signal.aborted) return;
      if (directory.status === 'fulfilled') setAirports(directory.value.airports);
      if (sources.status === 'fulfilled') setCapabilities(sources.value);
      if (directory.status === 'rejected' || sources.status === 'rejected') {
        setLoadError(directory.status === 'rejected' ? 'The airport directory could not load.' : 'Fare source status could not load.');
      }
    });
    return () => request.abort();
  }, [attempt]);

  return <div className="flight-app">
    <a className="flight-skip" href="#flight-main">Skip to flight search</a>
    <header className="flight-header"><div className="flight-width header-inner">
      <a className="flight-brand" href="/"><img src="/favicon.svg" alt="" width="34" height="34"/> SkyLens</a>
      <nav aria-label="Main navigation"><a href="/" aria-current="page">Flights</a><a href="/research.html">Research</a></nav>
    </div></header>
    <main className="flight-width flight-main" id="flight-main" tabIndex={-1}>
      <h1>Find flights in India</h1>
      <p className="flight-intro">Choose your airports, travel dates and cabin.</p>
      <FlightSearchForm airports={airports} capabilities={capabilities} busy={state.status === 'loading'}
        onSearch={query => void search(query)} onEdit={clear}/>
      {loadError && <div className="flight-status" role="status"><p>{loadError}</p>
        <button className="small-button" type="button" onClick={() => setAttempt(value => value + 1)}>Retry connection</button></div>}
      <FlightResults state={state} unavailable={capabilities !== null && !capabilities.live_quotes && !capabilities.ml_estimates} retry={retry}/>
    </main>
    <footer className="flight-width flight-footer"><span>SkyLens</span><span>Indian domestic flights</span><a href="/research.html">Research</a></footer>
  </div>;
}

createRoot(document.getElementById('root')!).render(<FlightApp/>);
