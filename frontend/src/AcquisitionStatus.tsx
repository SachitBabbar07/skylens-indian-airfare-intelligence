import {useEffect, useState} from 'react';

type Review = {reviewed_at_utc: string; verified_one_way_observations: number;
  verified_round_trip_observations: number; approved_sources: number;
  customer_fare_prediction_available: false; training_automatically_enabled: false};

export function validReview(value: Review) {
  return value.customer_fare_prediction_available === false && value.training_automatically_enabled === false &&
    typeof value.reviewed_at_utc === 'string' && Number.isFinite(Date.parse(value.reviewed_at_utc)) &&
    [value.verified_one_way_observations, value.verified_round_trip_observations, value.approved_sources]
      .every(v => Number.isInteger(v) && v >= 0);
}

export function AcquisitionReview({review}: {review: Review}) {
  if (!validReview(review)) return <p role="alert">Acquisition review withheld: invalid evidence status.</p>;
  return <section className="acquisition-panel panel" aria-labelledby="acquisition-title">
    <span className="small-label">DATA ACQUISITION REVIEW / {review.reviewed_at_utc.slice(0, 10)}</span>
    <h2 id="acquisition-title">Verified data intake</h2>
    <dl className="acquisition-counts">
      <div><dt>Verified one-way observations</dt><dd>{review.verified_one_way_observations}</dd></div>
      <div><dt>Verified return observations</dt><dd>{review.verified_round_trip_observations}</dd></div>
      <div><dt>Approved collection sources</dt><dd>{review.approved_sources}</dd></div>
    </dl>
    <p className="muted">Collection needs documented source permission and price evidence. Downloaded templates contain no observations. Importing records does not enable customer predictions.</p>
    <div className="acquisition-links"><a href="/acquisition/template.csv" download>Download empty quote CSV</a>
      <a href="/acquisition/schema" target="_blank" rel="noreferrer">Quote and source-permission schema ↗</a></div>
  </section>;
}

export function AcquisitionStatus() {
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    fetch('/acquisition/status').then(async response => {
      if (!response.ok) throw new Error('Unavailable');
      const value = await response.json();
      if (!validReview(value)) throw new Error('Invalid review');
      if (live) setReview(value);
    }).catch(() => {if (live) setError(true);});
    return () => {live = false;};
  }, []);
  return review ? <AcquisitionReview review={review}/> : <p className="muted" role="status">{
    error ? 'Acquisition review unavailable. Customer prediction remains disabled.' : 'Loading acquisition review…'}</p>;
}
