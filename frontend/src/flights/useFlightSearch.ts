import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import {type FareResult, type FlightQuery, type SearchCapabilities, type SearchState} from './types';

export async function requestFlightSearch(query: FlightQuery, capabilities: SearchCapabilities | null): Promise<SearchState> {
  if (!capabilities?.live_quotes && !capabilities?.ml_estimates) return {status: 'comparison', query};
  try {
    const response = await api<{results: FareResult[]}>('/flights/search', query);
    if (!Array.isArray(response.results) || response.results.some(result =>
      result?.source !== 'live_quote' && result?.source !== 'ml_estimate')) {
      throw new Error('The fare response could not be read. Try again.');
    }
    return {status: 'success', results: response.results, query};
  } catch (error) {
    if (error instanceof ApiError && ['unconfigured', 'unsupported'].includes(error.code ?? '')) {
      return {status: 'comparison', query};
    }
    const retryable = error instanceof ApiError
      ? error.retryable ?? (!['quota', 'authentication'].includes(error.code ?? '') && error.status !== 422)
      : true;
    const message = error instanceof ApiError ? error.message : 'SkyLens could not retrieve fares for this trip.';
    return {status: 'error', message, retryable, query};
  }
}

export function useFlightSearch(capabilities: SearchCapabilities | null) {
  const [state, setState] = useState<SearchState>({status: 'idle'});
  const active = useRef(false);
  const lastQuery = useRef<FlightQuery | null>(null);

  const search = useCallback(async (query: FlightQuery) => {
    if (active.current) return;
    active.current = true;
    lastQuery.current = query;
    setState({status: 'loading'});
    try {
      setState(await requestFlightSearch(query, capabilities));
    } finally {
      active.current = false;
    }
  }, [capabilities]);

  return {
    state, search,
    clear: () => {if (!active.current) {lastQuery.current = null; setState({status: 'idle'});}},
    retry: () => {if (lastQuery.current) void search(lastQuery.current);},
  };
}
