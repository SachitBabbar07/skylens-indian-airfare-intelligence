export const FARE_UNAVAILABLE_MESSAGE = "Fare prediction is temporarily unavailable because the training data's price definition has not yet been verified.";
export const UNIT_LABEL = 'unverified model-output units';
export const MISSING_EVIDENCE = [
  'Documented target currency',
  'Whether taxes and mandatory fees are included',
  'Whether the target is a total fare or base fare',
  'Per-passenger versus complete-booking price basis',
  'Genuine one-way, return or other booking type',
  'Original source documentation establishing those meanings',
  'Independent evaluation for the intended customer prediction scope',
];

export type ResearchResult = {
  estimate: number;
  currency: null;
  unit: 'source fare units';
  research_only: true;
  unit_verification: 'unverified';
  output_kind: 'unverified_research_model_output';
  historical_support: number;
  interval: null;
  interval_status: string;
};
export type ResearchExplanation = {
  estimate: number;
  baseline: number;
  currency: null;
  unit: 'source fare units';
  research_only: true;
  unit_verification: 'unverified';
  additive_error: number;
  contributions: {feature: string; value: string | number; contribution: number}[];
};

// Only a reviewed future release can add customer estimation. Neither model
// metadata nor a claimed currency/capability flag can enable it in this release.
export function CustomerStatus() {
  return <section className="customer-status panel" aria-labelledby="customer-status-title">
    <span className="small-label">CUSTOMER FARE ESTIMATION / UNAVAILABLE</span>
    <h2 id="customer-status-title">Price definition awaiting verification</h2>
    <p className="status-message">{FARE_UNAVAILABLE_MESSAGE}</p>
    <p className="muted">Required before customer use:</p>
    <ul className="evidence-list">{MISSING_EVIDENCE.map(item => <li key={item}>{item}</li>)}</ul>
    <button className="unavailable-button" disabled>Customer fare prediction unavailable</button>
  </section>;
}

export function ResearchOverview({counts, eligibleAirports, eligibleProfiles, onResearch}: {
  counts: Record<string, number>; eligibleAirports?: number; eligibleProfiles?: number; onResearch: () => void;
}) {
  return <>
    <CustomerStatus/>
    <section className="research-summary">
      <div><span className="small-label">AVAILABLE NOW / RESEARCH</span>
        <h2>Inspect the evidence and the models</h2>
        <p className="muted">Explore dataset coverage, saved evaluation results and feature contributions.
          Raw outputs describe a historical training target whose monetary meaning is unverified.</p>
        <button className="secondary" onClick={onResearch}>Open research tools <span aria-hidden="true">↗</span></button>
      </div>
      <div className="research-facts">
        {[
          ['Observed historical airport endpoints', counts.fare_airports],
          ['Observed directional routes', counts.fare_routes],
          ['Selected-model research-eligible airports', eligibleAirports],
          ['Selected-model eligible profiles', eligibleProfiles],
        ].map(([label, value]) => <div key={String(label)}><strong>{typeof value === 'number' ? value.toLocaleString('en-IN') : '—'}</strong><span>{label}</span></div>)}
      </div>
    </section>
  </>;
}

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const unverified = (v: ResearchResult | ResearchExplanation) => v.currency === null &&
  v.unit === 'source fare units' && v.research_only === true && v.unit_verification === 'unverified';
export function validResearchOutput(result: ResearchResult, explanation: ResearchExplanation) {
  return unverified(result) && unverified(explanation) && result.output_kind === 'unverified_research_model_output' &&
    result.interval === null && finite(result.estimate) && finite(result.historical_support) &&
    finite(explanation.estimate) && Math.abs(result.estimate - explanation.estimate) < 1e-6 &&
    finite(explanation.baseline) && finite(explanation.additive_error) && Array.isArray(explanation.contributions) &&
    explanation.contributions.every(v => finite(v.contribution));
}
const fmt = (n: number) => new Intl.NumberFormat('en-IN', {maximumFractionDigits: 2}).format(n);
const label = (name: string) => name.replaceAll('_', ' ');

export function ResearchOutput({result, explanation, busy}: {
  result: ResearchResult | null; explanation: ResearchExplanation | null; busy: boolean;
}) {
  if (busy) return <section className="panel result" role="status"><h2>Reading research artifacts</h2><p>Computing raw output and native SHAP contributions.</p></section>;
  if (!result || !explanation) return <section className="panel result"><span className="small-label">RESEARCH OUTPUTS</span>
    <h2>Inspect a historical profile</h2><p className="muted">An acknowledged research analysis reveals raw model output and SHAP contributions in {UNIT_LABEL}.</p>
    <p className="muted">These values cannot be interpreted as actual fares, ticket prices, booking quotes or INR amounts.</p></section>;
  if (!validResearchOutput(result, explanation)) return <section className="panel result" role="alert"><h2>Research output withheld</h2>
    <p>The response does not satisfy the unverified research contract. No monetary interpretation is available.</p></section>;
  return <section className="result-column">
    <div className="panel result"><span className="small-label">RESEARCH ONLY / RAW MODEL OUTPUT</span>
      <h2>Unverified training-target output</h2>
      <p className="muted">Not an actual fare, ticket price, booking quote or verified INR amount. No currency conversion has been applied.</p>
      <table className="research-output-table"><caption>Numerical research diagnostics</caption><tbody>
        <tr><th scope="row">Raw model output</th><td>{fmt(result.estimate)}<small>{UNIT_LABEL}</small></td></tr>
        <tr><th scope="row">Model baseline</th><td>{fmt(explanation.baseline)}<small>{UNIT_LABEL}</small></td></tr>
        <tr><th scope="row">Historical profile support</th><td>{result.historical_support} training observations</td></tr>
        <tr><th scope="row">Prediction interval</th><td>Withheld: accepted input range lacks independent holdout validation.</td></tr>
      </tbody></table>
    </div>
    <div className="panel explanation"><span className="small-label">SHAP RESEARCH EXPLANATION</span>
      <h3>Model associations, not causes</h3>
      <p className="muted">All contributions use {UNIT_LABEL}. Positive and negative contributions move the raw output relative to its baseline; they do not represent rupee increases or savings.</p>
      {explanation.contributions.slice(0, 6).map(v => <div key={v.feature} className="factor">
        <div><span>{label(v.feature)}</span><b className={v.contribution >= 0 ? 'positive' : 'negative'}>{v.contribution >= 0 ? '+' : '−'}{fmt(Math.abs(v.contribution))}</b></div>
        <div className="bar-track"><div className={v.contribution >= 0 ? 'bar positive-bg' : 'bar negative-bg'}
          style={{width: `${Math.max(1, Math.abs(v.contribution) / Math.max(1, ...explanation.contributions.map(v => Math.abs(v.contribution))) * 100)}%`}}/></div>
      </div>)}
      <details><summary>All contributions and additive check</summary>
        <div className="contributions-scroll"><table><caption>SHAP contributions · {UNIT_LABEL}</caption><thead><tr><th>Input</th><th>Contribution</th></tr></thead>
          <tbody>{explanation.contributions.map(v => <tr key={v.feature}><td>{label(v.feature)}<small>{typeof v.value === 'number' ? fmt(v.value) : v.value}</small></td><td>{fmt(v.contribution)}</td></tr>)}</tbody></table></div>
        <p className="fine">Baseline + contributions = {fmt(result.estimate)} {UNIT_LABEL}. Additive error: {explanation.additive_error.toExponential(1)}.</p>
      </details>
    </div>
  </section>;
}
