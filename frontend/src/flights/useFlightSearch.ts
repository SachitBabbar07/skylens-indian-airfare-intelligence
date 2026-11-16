import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import type {FareResult, FlightQuery, SearchState} from './types';

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
      const response = await api<{results: FareResult[]}>('/flights/search', query);
      if (!Array.isArray(response.results)) throw new Error('The fare response could not be read. Try again.');
      setState({status: 'success', results: response.results, query});
    } catch (error) {
      const retryable = error instanceof ApiError
        ? !['unconfigured', 'quota', 'authentication', 'unsupported'].includes(error.code ?? '') && error.status !== 422
        : true;
      setState({status: 'error', message: error instanceof Error ? error.message : 'Flight search failed.', retryable});
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
