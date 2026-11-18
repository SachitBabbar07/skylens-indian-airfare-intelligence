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
const {FlightSearchForm} = await server.ssrLoadModule('/src/flights/FlightSearchForm.tsx');
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

test('a trip with no fare source offers an exact-date comparison without an invented price', async context => {
  const query = {origin: 'DEL', destination: 'IXC', journey: 'one_way', departure_date: '2026-11-25',
    cabin: 'economy', airline: 'indigo', travellers: {adults: 1, children: 0, infants: 0}};
  const fetch = context.mock.method(globalThis, 'fetch', async () => {throw new Error('No fare source');});
  const state = await requestFlightSearch(query, {live_quotes: null, ml_estimates: null, indicative_estimates: {}});
  assert.equal(fetch.mock.callCount(), 0, 'A legacy Groq capability must not trigger a customer estimate');
  const html = render(FlightResults, {state, airlines: [{id: 'indigo', name: 'IndiGo'}], retry() {}});
  assert.match(html, /DEL → IXC/);
  assert.match(html, /25 Nov 2026/);
  assert.match(html, /IndiGo/);
  assert.match(html, /Check current fares/);
  const href = new URL(html.match(/href="([^"]+)"/)[1].replaceAll('&amp;', '&'));
  assert.equal(href.origin + href.pathname, 'https://www.google.com/travel/flights/search');
  assert.equal(href.searchParams.get('curr'), 'INR');
  // The tfs value comes from this exact itinerary with the IndiGo filter set in Google Flights.
  assert.equal(href.searchParams.get('tfs'), 'CBwQAhoiEgoyMDI2LTExLTI1MgI2RWoHCAESA0RFTHIHCAESA0lYQ0ABSAFwAYIBCwj___________8BmAEC');
  assert.doesNotMatch(html, /₹|result-price|indicative-price/);
});

const comparisonQuery = {origin: 'PNQ', destination: 'DEL', journey: 'round_trip', departure_date: '2027-04-05',
  return_date: '2027-04-10', cabin: 'economy', travellers: {adults: 1, children: 1, infants: 0}};

test('airline preferences are available for external fare comparison', () => {
  const html = render(FlightSearchForm, {airports: [], busy: false,
    airlines: [{id: 'indigo', name: 'IndiGo'}, {id: 'star_air', name: 'Star Air'}]});
  assert.match(html, /Airline preference.*Any airline.*IndiGo.*Star Air/);
});

test('a fare source outage leaves a comparison link, and a manual retry can recover', async context => {
  let calls = 0;
  const quote = {...fixtureResult, travellers: comparisonQuery.travellers, journey: 'round_trip',
    legs: [fixtureLeg, {...fixtureLeg, origin: 'DEL', destination: 'PNQ', departure: '2027-04-10T08:00:00+05:30',
      arrival: '2027-04-10T10:00:00+05:30'}]};
  context.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/flights/search');
    assert.deepEqual(JSON.parse(options.body), comparisonQuery);
    if (++calls === 1) throw new TypeError('Connection refused');
    return Response.json({results: [quote]});
  });
  const capabilities = {live_quotes: {}};
  const error = await requestFlightSearch(comparisonQuery, capabilities);
  assert.equal(error.status, 'error');
  assert.equal(error.retryable, true);
  const html = render(FlightResults, {state: error, retry() {}});
  assert.match(html, /Check current fares/);
  assert.match(html, /Try again/);
  assert.doesNotMatch(html, /₹|result-price/);
  assert.equal(calls, 1);
  assert.deepEqual(await requestFlightSearch(comparisonQuery, capabilities),
    {status: 'success', results: [quote], query: comparisonQuery});
  assert.equal(calls, 2);
});

test('unrecognized estimate payloads never reach the price card', async context => {
  context.mock.method(globalThis, 'fetch', async () => Response.json({
    estimation_source: 'groq_indicative', estimated_low: 2000, estimated_high: 2500,
  }));
  assert.equal((await requestFlightSearch(comparisonQuery, {live_quotes: {}})).status, 'error');
});

test('a covered trained-model result still reaches the labelled price card', async context => {
  const model = {id: 'model-fixture', source: 'ml_estimate', source_name: 'Software fixture', fare: fixtureFare,
    retrieved_at: fixtureResult.retrieved_at, journey: comparisonQuery.journey, cabin: comparisonQuery.cabin,
    travellers: comparisonQuery.travellers};
  context.mock.method(globalThis, 'fetch', async url => {
    assert.equal(url, '/flights/search');
    return Response.json({results: [model]});
  });
  assert.deepEqual(await requestFlightSearch(comparisonQuery, {ml_estimates: {}}),
    {status: 'success', results: [model], query: comparisonQuery});
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
  for (const state of [{status: 'idle'}, {status: 'loading'}, {status: 'success', results: [], query: comparisonQuery},
    {status: 'error', message: 'Provider timed out', retryable: true, query: comparisonQuery}]) {
    const rendered = render(FlightResults, {state, retry() {}});
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
