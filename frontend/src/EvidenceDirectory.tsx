import {useEffect, useState} from 'react';
import {api} from './api';

export type Combo = {origin: string; destination: string; airline: string; cabin_class: string; stops: number;
  n: number; duration_min: number; duration_max: number; lead_min: number; lead_max: number;
  hour_min: number; hour_max: number};
type ObservedRoute = {origin: string; destination: string; cabin_class: string; cohort_id: string; observations: number};
type Cohort = {id: string; source: string; retained_observations: number; airport_count: number; directional_routes: number;
  observed_cabins: string[]; collection_dates: string[]; travel_dates: string[]; role: string};
type Evidence = {cohorts: Cohort[]; routes: ObservedRoute[]; distinct_directional_routes: number};
const fmt = (n: number) => n.toLocaleString('en-IN');
const titles: Record<string, string> = {cabin_2023: 'Cabin research · 2023', network_2020: 'Network research · 2020',
  network_external_2020: 'External challenge · 2020'};

export function matchesRoute(row: {origin: string; destination: string}, from: string, to: string) {
  return row.origin.includes(from.trim().toUpperCase()) && row.destination.includes(to.trim().toUpperCase());
}

export function EvidenceDirectory({profiles, modelName, modelId, models, onModel, onProfile}: {
  profiles: Combo[] | undefined; modelName: string | undefined; modelId: string; models: {id: string; name: string}[];
  onModel: (id: string) => void; onProfile: (profile: Combo) => void;
}) {
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [view, setView] = useState<'observed' | 'eligible'>('observed');
  const [from, setFrom] = useState(''), [to, setTo] = useState('');
  const [cohort, setCohort] = useState(''), [cabin, setCabin] = useState('');
  const [airline, setAirline] = useState(''), [stops, setStops] = useState('');
  const [page, setPage] = useState(0);
  useEffect(() => {
    const request = new AbortController();
    setError('');
    api<Evidence>('/research/evidence', undefined, AbortSignal.any([request.signal, AbortSignal.timeout(15_000)])).then(value => {
      if (!request.signal.aborted) setEvidence(value);
    }).catch(err => {
      if (!request.signal.aborted) setError(err.message);
    });
    return () => request.abort();
  }, [retry]);
  const observed = (evidence?.routes ?? []).filter(r => !cohort || r.cohort_id === cohort);
  const eligible = profiles ?? [];
  const cabins = [...new Set((view === 'observed' ? observed : eligible).map(r => r.cabin_class))].sort();
  const matchingObserved = observed.filter(r => matchesRoute(r, from, to) && (!cabin || r.cabin_class === cabin));
  const matchingEligible = eligible.filter(r => matchesRoute(r, from, to) && (!cabin || r.cabin_class === cabin) &&
    (!airline || r.airline === airline) && (!stops || r.stops === Number(stops)));
  const count = view === 'observed' ? matchingObserved.length : matchingEligible.length;
  const pages = Math.max(1, Math.ceil(count / 15)), currentPage = Math.min(page, pages - 1);
  const start = currentPage * 15;
  function mode(next: 'observed' | 'eligible') {setView(next); setCabin(''); setPage(0);}
  return <section className="evidence-directory" id="route-directory" aria-labelledby="route-directory-title">
    <span className="small-label">ROUTES AND PROFILES</span>
    <h2 id="route-directory-title">Route evidence</h2>
    <p className="muted">Observations describe past listings. Eligible profiles meet the selected model’s research support rules. Neither establishes a verified fare or current service.</p>
    <div className="segmented" role="group" aria-label="Route directory view">
      <button type="button" aria-pressed={view === 'observed'} onClick={() => mode('observed')}>Historical routes</button>
      <button type="button" aria-pressed={view === 'eligible'} onClick={() => mode('eligible')}>Eligible research profiles</button>
    </div>
    {view === 'observed' && !evidence ? <div role={error ? 'alert' : 'status'} className="panel empty-directory">
      {error || 'Loading historical route evidence…'} {error && <button className="secondary" onClick={() => setRetry(n => n + 1)}>Retry routes</button>}
    </div> : <>
      <div className="evidence-filters">
        <label>Origin IATA <input value={from} maxLength={3} onChange={e => {setFrom(e.target.value);setPage(0);}} placeholder="e.g. DEL"/></label>
        <label>Destination IATA <input value={to} maxLength={3} onChange={e => {setTo(e.target.value);setPage(0);}} placeholder="e.g. BOM"/></label>
        {view === 'observed' ? <label>Source cohort <select value={cohort} onChange={e => {setCohort(e.target.value);setCabin('');setPage(0);}}>
          <option value="">All cohorts</option>{evidence?.cohorts.map(c => <option key={c.id} value={c.id}>{titles[c.id] ?? c.id}</option>)}
        </select></label> : <label>Research model <select value={modelId} disabled={!models.length}
          onChange={e => {setCabin('');setAirline('');setStops('');setPage(0);onModel(e.target.value);}}>
          {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select></label>}
        <label>Cabin filter <select value={cabin} onChange={e => {setCabin(e.target.value);setPage(0);}}>
          <option value="">All cabin labels</option>{cabins.map(c => <option key={c}>{c}</option>)}
        </select></label>
        {view === 'eligible' && <>
          <label>Airline filter <select value={airline} onChange={e => {setAirline(e.target.value);setPage(0);}}><option value="">All historical airlines</option>
            {[...new Set(eligible.map(r => r.airline))].sort().map(a => <option key={a}>{a}</option>)}
          </select></label>
          <label>Stops filter <select value={stops} onChange={e => {setStops(e.target.value);setPage(0);}}><option value="">Any stops</option>
            {[...new Set(eligible.map(r => r.stops))].sort().map(n => <option key={n} value={n}>{stopLabel(n)}</option>)}
          </select></label>
        </>}
      </div>
      <p className="muted" role="status">{view === 'observed' ?
        `${fmt(new Set(matchingObserved.map(r => `${r.origin}-${r.destination}`)).size)} directional routes · ${fmt(count)} source/cabin entries` :
        profiles === undefined ? 'Selected model profiles are unavailable.' : `${fmt(count)} matching profiles · ${modelName ?? 'selected model'}`}</p>
      {!count ? <p className="panel empty-directory">{view === 'eligible' && profiles?.length === 0 ?
        'This model has no profile that meets the minimum support rule.' : 'No entries match the current filters.'}</p> : <>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable route evidence table"><table>
          <caption>{view === 'observed' ? 'Observed routes grouped by source and cabin' : 'Exact itinerary profiles eligible for research'}</caption>
          <thead><tr><th scope="col">Direction</th><th scope="col">Cabin</th><th scope="col">{view === 'observed' ? 'Source cohort' : 'Historical airline'}</th>
            {view === 'eligible' && <th scope="col">Stops</th>}<th scope="col">{view === 'observed' ? 'Historical observations' : 'Training observations'}</th>
            {view === 'eligible' && <th scope="col">Research action</th>}</tr></thead>
          <tbody>{view === 'observed' ? matchingObserved.slice(start, start+15).map(r => <tr key={`${r.cohort_id}:${r.origin}:${r.destination}:${r.cabin_class}`}>
            <th scope="row">{r.origin} → {r.destination}</th><td>{r.cabin_class}</td><td>{titles[r.cohort_id] ?? r.cohort_id}</td><td>{fmt(r.observations)}</td>
          </tr>) : matchingEligible.slice(start,start+15).map(r => <tr key={`${r.origin}:${r.destination}:${r.cabin_class}:${r.airline}:${r.stops}`}>
            <th scope="row">{r.origin} → {r.destination}</th><td>{r.cabin_class}</td><td>{r.airline}</td><td>{stopLabel(r.stops)}</td><td>{fmt(r.n)}</td>
            <td><button className="table-action" aria-label={`Inspect ${r.origin} to ${r.destination}, ${r.cabin_class}, ${r.airline}, ${stopLabel(r.stops)}`} onClick={() => onProfile(r)}>Inspect profile</button></td>
          </tr>)}</tbody>
        </table></div>
        <div className="pagination"><span>Page {currentPage + 1} of {pages}</span><div>
          <button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Previous routes</button>
          <button disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}>Next routes</button>
        </div></div>
      </>}
    </>}
    {evidence && <details className="dataset-details"><summary>Dataset sources and date coverage</summary><div className="dataset-grid">
      {evidence.cohorts.map(c => <article className="panel" key={c.id}><h3>{titles[c.id] ?? c.id}</h3>
        <p>{fmt(c.retained_observations)} retained observations · {fmt(c.airport_count)} airports · {fmt(c.directional_routes)} routes</p>
        <p>Collected: {c.collection_dates.join(' to ')}<br/>Travel: {c.travel_dates.join(' to ')}<br/>Cabin labels: {c.observed_cabins.join(', ')}</p>
        <p>{c.role === 'external_challenge' ? 'External challenge only; excluded from model fitting.' : 'Frozen research cohort; target currency and scope unknown.'}</p>
        <a href={`https://www.kaggle.com/datasets/${c.source}`} target="_blank" rel="noreferrer">Original dataset ↗</a>
      </article>)}
    </div></details>}
  </section>;
}

export function stopLabel(n: number) {return n === 0 ? 'Non-stop' : n === 1 ? '1 stop' : '2+ stops';}
