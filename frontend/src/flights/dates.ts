const timeZone = 'Asia/Kolkata';

export function indiaToday() {
  const parts = new Intl.DateTimeFormat('en', {timeZone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts();
  const field = (name: string) => parts.find(part => part.type === name)?.value;
  return `${field('year')}-${field('month')}-${field('day')}`;
}

const travelDate = new Intl.DateTimeFormat('en-IN', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});
export function flightDate(date: string) {
  return travelDate.format(new Date(`${date}T00:00:00Z`));
}
