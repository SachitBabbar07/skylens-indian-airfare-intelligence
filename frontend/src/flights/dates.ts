const timeZone = 'Asia/Kolkata';

export function indiaToday() {
  const parts = new Intl.DateTimeFormat('en', {timeZone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts();
  const field = (name: string) => parts.find(part => part.type === name)?.value;
  return `${field('year')}-${field('month')}-${field('day')}`;
}

export function flightTime(iso: string) {
  return new Intl.DateTimeFormat('en-IN', {timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).format(new Date(iso));
}

export function flightDate(iso: string) {
  return new Intl.DateTimeFormat('en-IN', {timeZone, weekday: 'short', day: 'numeric', month: 'short'}).format(new Date(iso));
}
