import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import {ESTIMATE_UNAVAILABLE, passengerCount, type FareResult, type FlightQuery, type IndicativeEstimate, type SearchState} from './types';

export async function requestFlightSearch(query: FlightQuery, indicative: boolean): Promise<SearchState> {
  try {
    if (indicative) {
      const estimate = await api<IndicativeEstimate>('/flights/estimate', query);
      if (estimate.estimation_source !== 'groq_indicative' || estimate.currency !== 'INR' ||
          !Number.isSafeInteger(estimate.estimated_low) || !Number.isSafeInteger(estimate.estimated_high) ||
          estimate.estimated_low <= 0 || estimate.estimated_low >= estimate.estimated_high ||
          estimate.origin !== query.origin || estimate.destination !== query.destination ||
          estimate.journey_type !== query.journey || estimate.cabin_class !== query.cabin ||
          estimate.departure_date !== query.departure_date || estimate.return_date !== (query.return_date ?? null) ||
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
    const message = indicative ? ESTIMATE_UNAVAILABLE : error instanceof Error ? error.message : 'Flight search failed.';
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
