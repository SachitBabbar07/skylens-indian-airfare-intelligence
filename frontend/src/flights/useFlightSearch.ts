import {useCallback, useRef, useState} from 'react';
import {api, ApiError} from '../api';
import {passengerCount, type FareEstimate, type FlightQuery, type SearchState} from './types';

function validAmount(value: unknown): value is string {
  return typeof value === 'string' && /^\d+(?:\.\d+)?$/.test(value) &&
    Number(value) > 0 && Number(value) <= Number.MAX_SAFE_INTEGER / 100;
}

function matchesEstimate(response: Partial<FareEstimate> | null, query: FlightQuery): response is FareEstimate {
  if (!response || response.origin !== query.origin || response.destination !== query.destination ||
      response.departure_date !== query.departure_date || response.return_date !== (query.return_date ?? null) ||
      response.journey_type !== query.journey || response.cabin_class !== query.cabin ||
      response.passenger_count !== passengerCount(query.travellers) ||
      typeof response.source_status?.model !== 'string' || typeof response.source_status?.market !== 'string' ||
      !['validated', 'unsupported', 'unavailable'].includes(response.coverage_status ?? '') ||
      typeof response.disclaimer !== 'string' || !response.disclaimer.trim()) return false;
  if (response.estimation_method === 'unavailable') {
    return response.estimated_low === null && response.estimated_high === null &&
      response.currency === null && response.price_scope === null;
  }
  const hasSource = response.estimation_method === 'historical_ml'
    ? response.coverage_status === 'validated' && response.source_status.model === 'available'
    : response.estimation_method === 'market_reference' && response.source_status.market === 'available';
  return hasSource && response.currency === 'INR' && response.price_scope === 'party_total' &&
    validAmount(response.estimated_low) && validAmount(response.estimated_high) &&
    Number(response.estimated_low) <= Number(response.estimated_high);
}

export async function requestFlightSearch(query: FlightQuery): Promise<SearchState> {
  try {
    const estimate = await api<Partial<FareEstimate>>('/flights/estimate', query);
    if (!matchesEstimate(estimate, query)) {
      return {status: 'error', message: 'SkyLens could not verify an estimate for this trip.', retryable: true, query};
    }
    return {status: 'success', estimate, query};
  } catch (error) {
    const retryable = error instanceof ApiError
      ? error.retryable ?? (error.code !== 'no_fare_evidence' && error.status !== 422)
      : true;
    const message = error instanceof ApiError ? error.message : 'SkyLens could not retrieve an estimate.';
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
