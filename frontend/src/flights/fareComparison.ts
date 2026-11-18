import type {Cabin, FlightQuery} from './types';

const googleCabin: Record<Cabin, number> = {economy: 1, premium_economy: 2, business: 3, first: 4};
const airlineDesignators: Record<string, string> = {
  air_india: 'AI', air_india_express: 'IX', akasa_air: 'QP', alliance_air: '9I', fly91: 'IC',
  indiaone_air: 'I7', indigo: '6E', spicejet: 'SG', star_air: 'S5',
};

// Google Flights share links use a base64url-encoded search message (tfs).
// The values we encode are short ASCII strings and integers below 128, so a
// single byte holds each field length and value used by SkyLens.
const integer = (field: number, value: number) => [field * 8, value];
const bytes = (field: number, value: number[]) => [field * 8 + 2, value.length, ...value];
const ascii = (value: string) => Array.from(value, char => char.charCodeAt(0));
const airport = (field: number, code: string) => bytes(field, [...integer(1, 1), ...bytes(2, ascii(code))]);
const leg = (from: string, to: string, date: string, airline: string | undefined) => bytes(3, [
  ...bytes(2, ascii(date)), ...(airline ? bytes(6, ascii(airline)) : []),
  ...airport(13, from), ...airport(14, to),
]);

export function fareComparisonUrl(query: FlightQuery): string {
  const returnDate = query.journey === 'round_trip' ? query.return_date : undefined;
  const airline = query.airline && Object.hasOwn(airlineDesignators, query.airline)
    ? airlineDesignators[query.airline] : undefined;
  const {adults, children, infants} = query.travellers;
  const tfs = [
    ...integer(1, 28), ...integer(2, 2),
    ...leg(query.origin, query.destination, query.departure_date, airline),
    ...(returnDate ? leg(query.destination, query.origin, returnDate, airline) : []),
    ...Array.from({length: adults}, () => integer(8, 1)).flat(),
    ...Array.from({length: children}, () => integer(8, 2)).flat(),
    ...Array.from({length: infants}, () => integer(8, 3)).flat(), // Infants on lap
    ...integer(9, googleCabin[query.cabin]), ...integer(14, 1),
    // Defaults copied from the public share link. Fields 16 and 19 have multibyte tags.
    130, 1, 11, 8, ...Array<number>(9).fill(255), 1, 152, 1, returnDate ? 1 : 2,
  ];
  const encoded = btoa(String.fromCharCode(...tfs)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
  const url = new URL('https://www.google.com/travel/flights/search');
  url.search = new URLSearchParams({tfs: encoded, hl: 'en', gl: 'IN', curr: 'INR'}).toString();
  return url.toString();
}
