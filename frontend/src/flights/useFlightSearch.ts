import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import {type FareResult, type FlightQuery, type SearchState} from './types';

export async function requestFlightSearch(query: FlightQuery): Promise<SearchState> {
  try {
    const response = await api<{results: FareResult[]}>('/flights/estimate', query);
    if (!Array.isArray(response.results) || response.results.some(result =>
      result?.source !== 'ml_estimate' && result?.source !== 'live_quote')) {
      throw new Error('The fare response could not be read.');
    }
    return {status: 'success', results: response.results, query};
  } catch (error) {
    const retryable = error instanceof ApiError
      ? error.retryable ?? (error.code !== 'no_fare_evidence' && error.status !== 422)
      : true;
    const message = error instanceof ApiError ? error.message : 'SkyLens could not retrieve a fare.';
    return {status: 'error', message, retryable, query};
  }
}

export function useFlightSearch() {
  const [state, setState] = useState<SearchState>({status: 'idle'});
  const active = useRef(false);
  const lastQuery = useRef<FlightQuery | null>(null);

  const search = useCallback(async (query: FlightQuery) => {
    if (active.current) return;
    active.current = true;
    lastQuery.current = query;
    setState({status: 'loading'});
    try {
      setState(await requestFlightSearch(query));
    } finally {
      active.current = false;
    }
  }, []);

  return {
    state, search,
    clear: () => {if (!active.current) {lastQuery.current = null; setState({status: 'idle'});}},
    retry: () => {if (lastQuery.current) void search(lastQuery.current);},
  };
}
