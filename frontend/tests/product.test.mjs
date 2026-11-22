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
const {FlightResults} = await server.ssrLoadModule('/src/flights/FlightResults.tsx');
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

const comparisonQuery = {origin: 'PNQ', destination: 'DEL', journey: 'round_trip', departure_date: '2027-04-05',
  return_date: '2027-04-10', cabin: 'economy', travellers: {adults: 1, children: 1, infants: 0}};

// Mock endpoint responses exercise the Flights contract without contacting a fare provider.
const marketEstimate = {estimated_low: '6120.50', estimated_median: '6500', estimated_high: '7980', currency: 'INR',
  origin: 'PNQ', destination: 'DEL', journey_type: 'round_trip', departure_date: '2027-04-05',
  return_date: '2027-04-10', cabin_class: 'economy', passenger_count: 2,
  estimation_method: 'market_reference', coverage_status: 'unsupported',
  source_status: {model: 'unsupported', market: 'available'}, price_scope: 'party_total', taxes: 'unknown',
  fees: 'unknown', observation_count: 9, range_kind: 'interquartile', stop_profile: [0, 1],
  disclaimer: 'Indicative range. Tax and fee inclusion is unknown.'};
const modelEstimate = {...marketEstimate, estimation_method: 'historical_ml', coverage_status: 'validated',
  source_status: {model: 'available', market: 'not_requested'}, estimated_low: '1234.50', estimated_median: '1234.50',
  estimated_high: '1234.50', observation_count: 0, range_kind: 'point', stop_profile: null, taxes: 'included', fees: 'included',
  disclaimer: 'Historical estimate for the travelling party.'};
const unavailableEstimate = {...marketEstimate, estimated_low: null, estimated_median: null, estimated_high: null,
  currency: null, estimation_method: 'unavailable', range_kind: 'unavailable', stop_profile: null, source_status: {model: 'unsupported', market: 'no_observations'},
  price_scope: null, taxes: null, fees: null, observation_count: 0, disclaimer: 'No comparable fares for these travel dates.'};

test('an unsupported prediction stays in SkyLens and displays neither a price nor a booking link', async context => {
  const query = {origin: 'DEL', destination: 'IXC', journey: 'one_way', departure_date: '2026-11-25',
    cabin: 'economy', airline: 'indigo', travellers: {adults: 1, children: 0, infants: 0}};
  context.mock.method(globalThis, 'fetch', async url => {
    assert.equal(url, '/flights/estimate');
    return Response.json({detail: {code: 'no_fare_evidence', message: 'No validated model covers this itinerary.'}}, {status: 503});
  });
  const state = await requestFlightSearch(query);
  const html = render(FlightResults, {state, airlines: [{id: 'indigo', name: 'IndiGo'}], retry() {}});
  assert.match(html, /DEL → IXC/);
  assert.match(html, /25 Nov 2026/);
  assert.match(html, /IndiGo/);
  assert.match(html, /No validated model covers this itinerary/);
  assert.doesNotMatch(html, /₹|estimate-amount|href=|Google Flights|Try again/);
});

test('airline preferences remain available for predictions', () => {
  const html = render(FlightSearchForm, {airports: [], busy: false,
    airlines: [{id: 'indigo', name: 'IndiGo'}, {id: 'star_air', name: 'Star Air'}]});
  assert.match(html, /Airline preference.*Any airline.*IndiGo.*Star Air/);
});

test('a backend outage can recover on manual retry and show a labelled model estimate', async context => {
  let calls = 0;
  context.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/flights/estimate');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), comparisonQuery);
    if (++calls === 1) throw new TypeError('Connection refused');
    return Response.json(modelEstimate);
  });
  const error = await requestFlightSearch(comparisonQuery);
  assert.equal(error.status, 'error');
  assert.equal(error.retryable, true);
  const html = render(FlightResults, {state: error, retry() {}});
  assert.match(html, /Try again/);
  assert.doesNotMatch(html, /₹|estimate-amount|href=/);
  const recovered = await requestFlightSearch(comparisonQuery);
  assert.equal(recovered.status, 'success');
  const recoveredHtml = render(FlightResults, {state: recovered, retry() {}});
  assert.match(recoveredHtml, /Historical ML estimate/);
  assert.equal(recoveredHtml.match(/₹1,234\.50/g)?.length, 1);
  assert.doesNotMatch(recoveredHtml, /Market-based|Non-stop|booking link|href=/);
  assert.equal(calls, 2);
});

test('a market summary displays one whole-party range, trip context and source disclosure', async context => {
  context.mock.method(globalThis, 'fetch', async () => Response.json(marketEstimate));
  const state = await requestFlightSearch(comparisonQuery);
  const html = render(FlightResults, {state, retry() {}});
  assert.match(html, /SkyLens estimated fare/);
  assert.match(html, /₹6,120\.50 – ₹7,980/);
  assert.match(html, /Total for 2 travellers/);
  assert.match(html, /Median ₹6,500/);
  assert.match(html, /Nonstop \/ 1 stop/);
  assert.match(html, /Market-based indicative estimate/);
  for (const value of ['PNQ → DEL', 'Round trip', 'Economy', '5 Apr 2027', '10 Apr 2027', marketEstimate.disclaimer]) {
    assert.ok(html.includes(value), value);
  }
  assert.doesNotMatch(html, /Historical ML estimate|Kiwi|Sort by|Lowest fare|flight number|href=/i);
});

test('a single comparable observation displays one amount and only its outbound date', async context => {
  const oneWay = {...comparisonQuery, journey: 'one_way', return_date: undefined};
  const response = {...marketEstimate, estimated_low: null, estimated_median: '120.75', range_kind: 'limited_sample',
    estimated_high: null, stop_profile: [0], journey_type: 'one_way', return_date: null, observation_count: 1};
  context.mock.method(globalThis, 'fetch', async () => Response.json(response));
  const html = render(FlightResults, {state: await requestFlightSearch(oneWay), retry() {}});
  assert.equal(html.match(/₹120\.75/g)?.length, 1);
  assert.match(html, /One way/);
  assert.doesNotMatch(html, /10 Apr 2027| – /);
});

test('legacy individual offers and unrecognized numerical sources do not reach the price card', async context => {
  const responses = [{results: [{id: 'quote', source: 'live_quote', source_name: 'Kiwi.com', legs: [],
    fare: {amount: '6880', currency: 'INR', basis: 'party_total'}}]},
    {...marketEstimate, estimation_method: 'groq_indicative'}];
  context.mock.method(globalThis, 'fetch', async () => Response.json(responses.shift()));
  for (let index = 0; index < 2; index++) {
    const state = await requestFlightSearch(comparisonQuery);
    assert.equal(state.status, 'error');
    assert.doesNotMatch(render(FlightResults, {state, retry() {}}), /₹|Kiwi|6,880/);
  }
});

test('unusable amounts, currency, trip scope and unsupported model outputs are withheld', async context => {
  const changes = [{estimated_median: null}, {estimated_median: '8000'}, {stop_profile: [0]},
    {range_kind: 'limited_sample'}, {estimated_low: '-1'}, {estimated_high: '6000'}, {estimated_low: 'NaN'},
    {estimated_low: 6120.50}, {currency: 'XXX'}, {currency: 'USD'}, {currency: null},
    {price_scope: 'per_adult'}, {price_scope: undefined}, {passenger_count: 1}, {origin: 'DEL'},
    {destination: 'IXC'}, {journey_type: 'one_way'}, {return_date: null}, {departure_date: '2027-04-02'},
    {cabin_class: 'business'}, {estimation_method: 'historical_ml', coverage_status: 'unsupported'},
    {source_status: {model: 'unsupported', market: 'invalid_response'}},
    {estimation_method: 'historical_ml', coverage_status: 'validated',
      source_status: {model: 'invalid_response', market: 'available'}},
    {source_status: null}, {disclaimer: ''}];
  let change;
  context.mock.method(globalThis, 'fetch', async () => Response.json({...marketEstimate, ...change}));
  for (change of changes) {
    const state = await requestFlightSearch(comparisonQuery);
    assert.equal(state.status, 'error', JSON.stringify(change));
    assert.doesNotMatch(render(FlightResults, {state, retry() {}}), /₹|estimate-amount/);
  }
});

test('an unavailable estimate shows the trip and reason without inventing a fare', async context => {
  context.mock.method(globalThis, 'fetch', async () => Response.json(unavailableEstimate));
  const state = await requestFlightSearch(comparisonQuery);
  const html = render(FlightResults, {state, retry() {}});
  assert.match(html, /PNQ → DEL/);
  assert.match(html, /No comparable fares for these travel dates/);
  assert.doesNotMatch(html, /Try again|href=/);
  for (const empty of [state, {status: 'idle'}, {status: 'loading'},
    {status: 'error', message: 'The fare source timed out.', retryable: true, query: comparisonQuery}]) {
    assert.doesNotMatch(render(FlightResults, {state: empty, retry() {}}), /₹|estimate-amount/);
  }
});

test('research overview keeps historical predictions disabled and identifies the market fallback', () => {
  const html = render(views.ResearchOverview, {counts: {}, eligibleAirports: 0, eligibleProfiles: 0, onResearch() {}});
  assert.match(html, /historical training target.*unverified/i);
  assert.match(html, /disabled=""[^>]*>Historical ML fare prediction unavailable/);
  assert.match(html, /comparable market observations/);
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
