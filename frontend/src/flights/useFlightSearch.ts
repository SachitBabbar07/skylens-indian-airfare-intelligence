import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import {ESTIMATE_UNAVAILABLE, passengerCount, type FareResult, type FlightQuery, type IndicativeEstimate, type SearchState} from './types';

export async function requestFlightSearch(query: FlightQuery, indicative: boolean): Promise<SearchState> {
  try {
    if (indicative) {
      const estimate = await api<IndicativeEstimate | {results: FareResult[]}>('/flights/estimate', query);
      if ('results' in estimate) {
        if (!Array.isArray(estimate.results) || !estimate.results.length || estimate.results.some(result => result.source !== 'ml_estimate')) {
          throw new Error('The model response could not be read. Try again.');
        }
        return {status: 'success', results: estimate.results, query};
      }
      if (estimate.estimation_source !== 'groq_indicative' || estimate.currency !== 'INR' ||
          !Number.isSafeInteger(estimate.estimated_low) || !Number.isSafeInteger(estimate.estimated_high) ||
          estimate.estimated_low <= 0 || estimate.estimated_low >= estimate.estimated_high ||
          estimate.origin !== query.origin || estimate.destination !== query.destination ||
          estimate.journey_type !== query.journey || estimate.cabin_class !== query.cabin ||
          estimate.departure_date !== query.departure_date || estimate.return_date !== (query.return_date ?? null) ||
          estimate.airline !== (query.airline ?? null) || (query.airline ? !estimate.airline_name : estimate.airline_name !== null) ||
          !Number.isFinite(Date.parse(estimate.estimated_at)) ||
          estimate.passenger_count !== passengerCount(query.travellers)) {
        throw new Error('The estimate response could not be read. Try again.');
      }
      return {status: 'estimate', estimate};
    }
    const response = await api<{results: FareResult[]}>('/flights/search', query);
    if (!Array.isArray(response.results)) throw new Error('The fare response could not be read. Try again.');
    return {status: 'success', results: response.results, query};
  } catch (error) {
    const retryable = error instanceof ApiError
      ? error.retryable ?? (!['unconfigured', 'quota', 'authentication', 'unsupported'].includes(error.code ?? '') && error.status !== 422)
      : true;
    let message = indicative ? ESTIMATE_UNAVAILABLE : error instanceof Error ? error.message : 'Flight search failed.';
    if (indicative && error instanceof ApiError) {
      if (error.code === 'no_estimate') message = 'A useful fare range is unavailable for this trip. Try a different date or airline.';
      if (error.code === 'busy' || error.code === 'rate_limit') message = 'Fare searches are busy. Wait a moment and try again.';
      if (error.code === 'quota') message = 'The estimate service has reached its limit. Try again later.';
    }
    return {status: 'error', message, retryable};
  }
}

export function useFlightSearch(indicative: boolean) {
  const [state, setState] = useState<SearchState>({status: 'idle'});
  const active = useRef(false);
  const lastQuery = useRef<FlightQuery | null>(null);

  const search = useCallback(async (query: FlightQuery) => {
    if (active.current) return;
    active.current = true;
    lastQuery.current = query;
    setState({status: 'loading'});
    try {
      setState(await requestFlightSearch(query, indicative));
    } finally {
      active.current = false;
    }
  }, [indicative]);

  return {
    state, search,
    clear: () => {if (!active.current) {lastQuery.current = null; setState({status: 'idle'});}},
    retry: () => {if (lastQuery.current) void search(lastQuery.current);},
  };
}
