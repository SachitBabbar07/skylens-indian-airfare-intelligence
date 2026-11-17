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
  const estimateAvailable = Boolean(capabilities?.indicative_estimates || capabilities?.ml_estimates);
  const indicative = Boolean(capabilities?.indicative_estimates) || !capabilities?.live_quotes;
  const {state, search, clear, retry} = useFlightSearch(indicative);

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
    <header className="flight-header">
      <div className="flight-width header-inner">
        <a className="flight-brand" href="/"><img src="/favicon.svg" alt="" width="36" height="36"/>SkyLens</a>
        <nav aria-label="Main navigation">
          <a href="/" aria-current="page">Flights</a>
          <a href="/research.html">Research</a>
        </nav>
      </div>
    </header>
    <main className="flight-main">
      <section className="flight-width flight-hero" aria-labelledby="flight-title">
        <img className="flight-hero-photo" src="/flights-hero.webp" alt="" fetchPriority="high"/>
        <div className="flight-hero-content">
          <h1 id="flight-title">Find flights <span>in India</span></h1>
          <p className="flight-intro">Choose your route, travel dates and cabin.</p>
        </div>
      </section>
      <div className="flight-search-area" id="flight-main" tabIndex={-1}>
        <FlightSearchForm airports={airports} capabilities={capabilities} indicative={indicative} busy={state.status === 'loading'}
          onSearch={query => void search(query)} onEdit={clear}/>
        {loadError && <div className="flight-status" role="status"><p>{loadError}</p>
          <button className="small-button" type="button" onClick={() => setAttempt(value => value + 1)}>Retry connection</button></div>}
        {(capabilities || state.status !== 'idle') && <FlightResults state={state} indicative={indicative}
          unavailable={indicative && !estimateAvailable} retry={retry}/>}
      </div>
    </main>
    <footer className="flight-width flight-footer"><span>SkyLens</span><span>Indian domestic flights</span><a href="/research.html">Research</a></footer>
  </div>;
}

createRoot(document.getElementById('root')!).render(<FlightApp/>);
