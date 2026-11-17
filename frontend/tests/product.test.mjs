import {test, after} from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

const server = await createServer({root: fileURLToPath(new URL('..', import.meta.url)),
  configFile: false, server: {middlewareMode: true}, appType: 'custom',
  optimizeDeps: {noDiscovery: true, include: []}, esbuild: {jsx: 'automatic'}});
after(() => server.close());
const views = await server.ssrLoadModule('/src/ResearchViews.tsx');
const acquisition = await server.ssrLoadModule('/src/AcquisitionStatus.tsx');
const directory = await server.ssrLoadModule('/src/EvidenceDirectory.tsx');
const {findAirports} = await server.ssrLoadModule('/src/flights/AirportAutocomplete.tsx');
const {FlightResults, formatFare, sortResults} = await server.ssrLoadModule('/src/flights/FlightResults.tsx');
const {requestFlightSearch} = await server.ssrLoadModule('/src/flights/useFlightSearch.ts');
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
// Explicit software fixtures, never training data or displayed sample fares.
const result = {estimate: 12345.6789, currency: null, unit: 'source fare units', research_only: true,
  output_kind: 'unverified_research_model_output', unit_verification: 'unverified', historical_support: 50,
  interval: null, interval_status: 'withheld_unvalidated_serving_domain'};
const explanation = {estimate: 12345.6789, baseline: 12000, currency: null, unit: 'source fare units',
  research_only: true, unit_verification: 'unverified', additive_error: 0,
  contributions: [{feature: 'software_fixture', value: 1, contribution: 345.6789}]};

test('the autocomplete finds directory airports by city, airport name and IATA and excludes the other endpoint', () => {
  const airports = [
    {code: 'PNQ', city: 'Pune', name: 'Pune International Airport', has_historical_evidence: true},
    {code: 'AYJ', city: 'Faizabad', name: 'Maharshi Valmiki International Airport', has_historical_evidence: false},
  ];
  for (const query of [' ayj ', 'faizabad', 'Valmiki']) assert.equal(findAirports(airports, query)[0].code, 'AYJ');
  assert.deepEqual(findAirports(airports, 'pune', 'PNQ'), []);
  assert.deepEqual(findAirports(airports, 'absent'), []);
});

const fixtureFare = {amount: '1234.5', currency: 'INR', basis: 'party_total', taxes: 'included', fees: 'unknown'};
const fixtureLeg = {origin: 'PNQ', destination: 'DEL', departure: '2027-04-05T08:00:00+05:30',
  arrival: '2027-04-05T10:00:00+05:30', airlines: ['Software fixture'], duration_minutes: 120, stops: 0};
const fixtureResult = {id: 'quote', source: 'live_quote', availability: 'available', source_name: 'Software fixture',
  retrieved_at: '2027-04-01T12:00:00Z', journey: 'one_way', cabin: 'economy', travellers: {adults: 2, children: 0, infants: 0},
  legs: [fixtureLeg], fare: fixtureFare};

const indicativeQuery = {origin: 'PNQ', destination: 'DEL', journey: 'round_trip', departure_date: '2027-04-05',
  return_date: '2027-04-10', cabin: 'economy', travellers: {adults: 1, children: 1, infants: 0}};
const indicative = {estimated_low: 9000, estimated_high: 16000, currency: 'INR', origin: 'PNQ', destination: 'DEL',
  journey_type: 'round_trip', departure_date: '2027-04-05', return_date: '2027-04-10',
  cabin_class: 'economy', passenger_count: 2, estimation_source: 'groq_indicative'};

test('the indicative result renders a rupee range, route, dates, travel party and disclosure', () => {
  const html = render(FlightResults, {state: {status: 'estimate', estimate: indicative}, indicative: true, retry() {}});
  assert.match(html, /SkyLens Indicative Fare Estimate/);
  assert.match(html, /\u20b99,000 – \u20b916,000/);
  assert.match(html, /PNQ → DEL/);
  assert.match(html, /Round Trip.*Economy/);
  assert.match(html, /Departure 5 Apr 2027 · Return 10 Apr 2027/);
  assert.match(html, /Estimated total for 2 travellers/);
  assert.match(html, /AI-generated indicative estimate\. Not a live airline quote or guaranteed ticket price\. Actual fares may differ\./);
  assert.doesNotMatch(html, /Live Fare Quote|ML Estimated Fare|Non-stop|Available seats/);
});

test('loading and retry affordances never fill the estimate area with invented prices', () => {
  const renderState = state => render(FlightResults, {state, indicative: true, retry() {}});
  const loading = renderState({status: 'loading'});
  assert.match(loading, /role="status".*Generating an indicative fare estimate/);
  const outage = renderState({status: 'error', message: 'Backend unavailable', retryable: true});
  assert.match(outage, /role="alert".*Backend unavailable.*Try again/);
  const auth = renderState({status: 'error', message: 'API key was rejected', retryable: false});
  assert.doesNotMatch(auth, /Try again/);
  const disabled = render(FlightResults, {state: {status: 'idle'}, indicative: true, unavailable: true, retry() {}});
  assert.match(disabled, /Fare estimate temporarily unavailable\. Please try again\./);
  for (const html of [loading, outage, auth, disabled]) assert.doesNotMatch(html, /\u20b9|indicative-price|Groq Free plan/);
});

test('a backend outage leaves a manual retry and the next request can recover', async context => {
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/flights/estimate');
    assert.deepEqual(JSON.parse(options.body), indicativeQuery);
    if (++calls === 1) throw new TypeError('Connection refused');
    return Response.json(indicative);
  });
  const error = await requestFlightSearch(indicativeQuery, true);
  assert.equal(error.status, 'error');
  assert.equal(error.retryable, true);
  assert.equal(error.message, 'Fare estimate temporarily unavailable. Please try again.');
  assert.equal(calls, 1);
  assert.deepEqual(await requestFlightSearch(indicativeQuery, true), {status: 'estimate', estimate: indicative});
  assert.equal(calls, 2);
});

test('wrong currency, source, or journey is withheld and provider retry choices are honored', async context => {
  for (const change of [{currency: 'USD'}, {estimation_source: 'ml_estimate'}, {estimated_high: null}, {passenger_count: 1}]) {
    const mock = context.mock.method(globalThis, 'fetch', async () => Response.json({...indicative, ...change}));
    const error = await requestFlightSearch(indicativeQuery, true);
    assert.equal(error.status, 'error');
    mock.mock.restore();
  }
  context.mock.method(globalThis, 'fetch', async () => Response.json({detail: {code: 'quota', message: 'Free plan allowance reached',
    retryable: false}}, {status: 429}));
  assert.deepEqual(await requestFlightSearch(indicativeQuery, true),
    {status: 'error', message: 'Fare estimate temporarily unavailable. Please try again.', retryable: false});
});

test('fare formatting retains original currencies and requires exact traveller total basis', () => {
  assert.match(formatFare(fixtureFare), /\u20b91,234\.50/);
  assert.match(formatFare({...fixtureFare, currency: 'USD'}), /^USD\s1,234\.50$/);
  for (const change of [{currency: ''}, {currency: 'XXX'}, {amount: 'NaN'}, {basis: undefined}]) {
    assert.equal(formatFare({...fixtureFare, ...change}), null);
  }
});

test('live quotes keep provenance, each itinerary and fare, and sort only comparable prices', () => {
  const lower = {...fixtureResult, id: 'lower', fare: {...fixtureFare, amount: '998'},
    legs: [{...fixtureLeg, departure: '2027-04-05T07:00:00+05:30', duration_minutes: 100}]};
  for (const criterion of ['price', 'duration', 'departure']) {
    assert.equal(sortResults([fixtureResult, lower], criterion)[0].id, 'lower');
  }
  const usd = {...lower, fare: {...lower.fare, currency: 'USD'}};
  assert.equal(sortResults([fixtureResult, usd], 'price')[0].id, 'quote');
  const html = render(FlightResults, {state: {status: 'success', results: [fixtureResult, usd], query: fixtureLeg}, retry() {}});
  assert.match(html, /2 results/);
  assert.match(html, /Live Fare Quote/);
  assert.match(html, /Total for 2 travellers/);
  assert.match(html, /original currencies/);
  assert.doesNotMatch(html, /Lowest fare/);
});

test('research metadata stays outside fares and unavailable states have no price', () => {
  const estimate = {...fixtureResult, source: 'ml_estimate'};
  const html = render(FlightResults, {state: {status: 'success', results: [estimate], query: fixtureLeg}, retry() {}});
  assert.match(html, /ML Estimated Fare/);
  assert.doesNotMatch(html, /Live Fare Quote|Non-stop/);
  for (const state of [{status: 'idle'}, {status: 'loading'}, {status: 'success', results: []},
    {status: 'error', message: 'Provider timed out', retryable: true}]) {
    const rendered = render(FlightResults, {state, unavailable: true, retry() {}});
    assert.doesNotMatch(rendered, /\u20b9|result-price/);
  }
});

test('default overview disables customer prediction and has no raw amount or price card', () => {
  const html = render(views.ResearchOverview, {counts: {}, eligibleAirports: 0, eligibleProfiles: 0, onResearch() {}});
  assert.match(html, /Fare prediction is temporarily unavailable because the training data&#x27;s price definition has not yet been verified\./);
  assert.match(html, /disabled=""[^>]*>Customer fare prediction unavailable/);
  assert.match(html, /Independent evaluation for the intended customer prediction scope/);
  assert.match(html, /Open research tools/);
  assert.doesNotMatch(html, /₹|class="fare"|ESTIMATED RECORDED FARE|12,345|54,757/);
});

test('raw values remain ordinary research diagnostics without conversion', () => {
  const html = render(views.ResearchOutput, {result, explanation, busy: false});
  assert.match(html, /<table class="research-output-table">/);
  assert.match(html, /12,345\.68/);
  assert.match(html, /unverified model-output units/);
  assert.match(html, /Not an actual fare, ticket price, booking quote or verified INR amount/);
  assert.match(html, /No currency conversion has been applied/);
  assert.doesNotMatch(html, /₹|class="fare"|Estimated recorded fare/i);
  assert.equal(views.validResearchOutput(result, explanation), true);
});

for (const changes of [{currency: 'INR'}, {currency: undefined}, {research_only: false},
  {unit: 'INR'}, {unit_verification: 'verified'}, {output_kind: 'ticket_price'}, {estimate: NaN},
  {interval: {lower: 1, upper: 2}}]) {
  test(`unsafe result withheld: ${JSON.stringify(changes)}`, () => {
    const html = render(views.ResearchOutput, {result: {...result, ...changes}, explanation, busy: false});
    assert.match(html, /Research output withheld/);
    assert.doesNotMatch(html, /12,345|₹|research-output-table/);
  });
}

test('SHAP remains usable in unverified units and cannot claim rupee impacts', () => {
  const html = render(views.ResearchOutput, {result, explanation, busy: false});
  assert.match(html, /SHAP RESEARCH EXPLANATION/);
  assert.match(html, /do not represent rupee increases or savings/);
  assert.match(html, /All contributions and additive check/);
  assert.match(html, /345\.68/);
  const unsafe = render(views.ResearchOutput, {result, explanation: {...explanation, currency: 'INR'}, busy: false});
  assert.match(unsafe, /Research output withheld/);
  assert.doesNotMatch(unsafe, /345\.68|₹/);
});

test('empty and loading states do not invent an amount', () => {
  for (const busy of [true, false]) {
    const html = render(views.ResearchOutput, {result: null, explanation: null, busy});
    assert.doesNotMatch(html, /12,345|54,757|₹|class="fare"/);
  }
});

test('acquisition review exposes empty templates without enabling customer predictions', () => {
  const review = {reviewed_at_utc: '2026-11-15T00:00:00Z', verified_one_way_observations: 0,
    verified_round_trip_observations: 0, approved_sources: 0, customer_fare_prediction_available: false,
    training_automatically_enabled: false};
  const html = render(acquisition.AcquisitionReview, {review});
  assert.match(html, /Download empty quote CSV/);
  assert.match(html, /Verified one-way observations/);
  assert.match(html, /Importing records does not enable customer predictions/);
  assert.doesNotMatch(html, /₹|54,757|customer-ready/);
  const unsafe = render(acquisition.AcquisitionReview, {review: {...review, customer_fare_prediction_available: true}});
  assert.match(unsafe, /Acquisition review withheld/);
  assert.doesNotMatch(unsafe, /Download empty quote CSV/);
});

test('acquisition review rejects missing, negative and fabricated count flags', () => {
  const base = {reviewed_at_utc: '2026-11-15T00:00:00Z', verified_one_way_observations: 0,
    verified_round_trip_observations: 0, approved_sources: 0, customer_fare_prediction_available: false,
    training_automatically_enabled: false};
  for (const changes of [{approved_sources: -1}, {verified_one_way_observations: '10'},
    {training_automatically_enabled: true}, {reviewed_at_utc: 'unverified'}]) {
    assert.equal(acquisition.validReview({...base, ...changes}), false);
  }
});

test('route filters are directional and normalize typed IATA codes', () => {
  const route = {origin: 'DEL', destination: 'BOM'};
  assert.equal(directory.matchesRoute(route, ' del ', 'bo'), true);
  assert.equal(directory.matchesRoute(route, 'BOM', 'DEL'), false);
  assert.equal(directory.matchesRoute(route, '', 'BOM'), true);
});
