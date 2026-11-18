import {useId, useState} from 'react';
import {cabinNames, passengerCount, type Cabin, type Travellers} from './types';

export function TravellerSelector({party, cabin, cabins, childrenAllowed, infantsAllowed, maximum, disabled, onParty, onCabin}: {
  party: Travellers; cabin: Cabin; cabins: Cabin[]; childrenAllowed: boolean; infantsAllowed: boolean;
  maximum: number; disabled: boolean; onParty: (value: Travellers) => void; onCabin: (value: Cabin) => void;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const total = passengerCount(party);
  function adjust(field: keyof Travellers, delta: number) {
    onParty({...party, [field]: party[field] + delta});
  }
  const counters: {field: keyof Travellers; caption: string; min: number; max: number}[] = [
    {field: 'adults', caption: 'Adults', min: Math.max(1, party.infants), max: maximum},
    ...(childrenAllowed ? [{field: 'children' as const, caption: 'Children', min: 0, max: maximum}] : []),
    ...(infantsAllowed ? [{field: 'infants' as const, caption: 'Infants on lap', min: 0, max: party.adults}] : []),
  ];
  return <div className="traveller-field" onBlur={event => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
  }} onKeyDown={event => {
    if (event.key === 'Escape') {setOpen(false); document.getElementById(`${id}-button`)?.focus();}
  }}>
    <button className="flight-field traveller-trigger" type="button" id={`${id}-button`}
      aria-expanded={open} aria-controls={open ? id : undefined} disabled={disabled} onClick={() => setOpen(value => !value)}>
      <span className="field-label">Travellers &amp; class</span>
      <strong>{total} {total === 1 ? 'traveller' : 'travellers'}</strong>
      <span className="field-detail">{cabinNames[cabin]}</span><span className="traveller-chevron" aria-hidden="true">⌄</span>
    </button>
    {open && <fieldset className="traveller-popover" id={id} disabled={disabled}>
      <legend className="flight-sr-only">Travellers and cabin class</legend>
      {counters.map(({field, caption, min, max}) => <div className="traveller-counter" key={field}>
        <span>{caption}</span><div className="stepper">
          <button type="button" aria-label={`Remove ${field === 'children' ? 'child' : field.slice(0, -1)}`}
            disabled={party[field] <= min} onClick={() => adjust(field, -1)}>−</button>
          <output aria-label={caption} aria-live="polite">{party[field]}</output>
          <button type="button" aria-label={`Add ${field === 'children' ? 'child' : field.slice(0, -1)}`}
            disabled={party[field] >= max || total >= maximum} onClick={() => adjust(field, 1)}>+</button>
        </div>
      </div>)}
      <label className="cabin-select">Cabin class<select value={cabin} onChange={event => onCabin(event.target.value as Cabin)}>
        {cabins.map(item => <option key={item} value={item}>{cabinNames[item]}</option>)}
      </select></label>
      <button className="small-button" type="button" onClick={() => {setOpen(false);document.getElementById(`${id}-button`)?.focus();}}>Done</button>
    </fieldset>}
  </div>;
}
