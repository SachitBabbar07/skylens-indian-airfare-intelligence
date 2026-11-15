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
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
// Explicit software fixtures, never training data or displayed sample fares.
const result = {estimate: 12345.6789, currency: null, unit: 'source fare units', research_only: true,
  output_kind: 'unverified_research_model_output', unit_verification: 'unverified', historical_support: 50,
  interval: null, interval_status: 'withheld_unvalidated_serving_domain'};
const explanation = {estimate: 12345.6789, baseline: 12000, currency: null, unit: 'source fare units',
  research_only: true, unit_verification: 'unverified', additive_error: 0,
  contributions: [{feature: 'software_fixture', value: 1, contribution: 345.6789}]};

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
