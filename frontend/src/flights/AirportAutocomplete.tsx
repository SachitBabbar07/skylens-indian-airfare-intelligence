import {useId, useState} from 'react';
import type {Airport} from './types';

export function findAirports(airports: Airport[], query: string, excludedCode?: string) {
  const needle = query.trim().toLocaleLowerCase('en-IN');
  const matches = airports.filter(airport => airport.code !== excludedCode &&
    [airport.code, airport.city, airport.name].some(value => value.toLowerCase().includes(needle)));
  const score = (airport: Airport) => {
    if (!needle) return airport.has_historical_evidence ? 0 : 1;
    if (airport.code.toLowerCase() === needle) return 0;
    if (airport.city.toLowerCase().startsWith(needle)) return 1;
    if (airport.code.toLowerCase().startsWith(needle)) return 2;
    return 3;
  };
  return matches.sort((a, b) => score(a) - score(b) || (a.city || a.name).localeCompare(b.city || b.name)).slice(0, 8);
}

export function AirportAutocomplete({label, value, airports, excludedCode, disabled, onChange}: {
  label: string; value: Airport | null; airports: Airport[]; excludedCode?: string; disabled: boolean;
  onChange: (airport: Airport | null) => void;
}) {
  const id = useId();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const matches = open ? findAirports(airports, query, excludedCode) : [];
  const selectedLabel = value ? `${value.city || value.name} (${value.code})` : '';
  const choose = (airport: Airport) => {
    onChange(airport);
    setQuery('');
    setOpen(false);
  };
  return <div className="flight-field airport-field">
    <label htmlFor={id}>{label}</label>
    <input id={id} role="combobox" autoComplete="off" spellCheck={false} maxLength={100}
      aria-autocomplete="list" aria-expanded={open} aria-controls={open ? `${id}-list` : undefined}
      aria-activedescendant={open && matches[active] ? `${id}-${active}` : undefined}
      aria-describedby={value && !open ? `${id}-description` : undefined} disabled={disabled}
      placeholder="City or airport" value={open ? query : selectedLabel || query}
      onFocus={() => {setQuery(value ? '' : query); setOpen(true); setActive(0);}}
      onClick={() => {if (!open) {setOpen(true); setActive(0);}}}
      onBlur={() => {setOpen(false); if (value) setQuery('');}}
      onChange={event => {setQuery(event.target.value);setOpen(true);setActive(0);onChange(null);}}
      onKeyDown={event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          const next = active + (event.key === 'ArrowDown' ? 1 : -1);
          setActive(open ? Math.max(0, Math.min(matches.length - 1, next)) : 0);
          setOpen(true);
        } else if (event.key === 'Escape') {
          setOpen(false);
          if (value) setQuery('');
        } else if (event.key === 'Enter' && open) {
          event.preventDefault();
          if (matches[active]) choose(matches[active]);
        }
      }}/>
    {value && !open && <span id={`${id}-description`} className="field-detail" title={value.name}>{value.name}</span>}
    {open && <div className="airport-options">
      <ul id={`${id}-list`} role="listbox" aria-label={`${label} airports`}>
        {matches.map((airport, index) => <li id={`${id}-${index}`} key={airport.code} role="option"
          aria-selected={active === index} onPointerDown={event => event.preventDefault()}
          onClick={() => choose(airport)}>
          <span><strong>{[airport.city, airport.state].filter(Boolean).join(', ') || airport.name}</strong>
            <small>{airport.name}</small></span><span className="iata-code">{airport.code}</span>
        </li>)}
      </ul>
      {!matches.length && <p role="status">No matching Indian airports.</p>}
    </div>}
  </div>;
}
