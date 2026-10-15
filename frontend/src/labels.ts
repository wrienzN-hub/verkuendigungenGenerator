export const ranks: Record<string, string> = {
  H: 'Hochfest',
  F: 'Fest',
  G: 'Gebotener Gedenktag',
  g: 'Nichtgebotener Gedenktag',
  sunday: 'Sonntag',
  privileged_weekday: 'Besonderer Wochentag',
  triduum: 'Österliche Tage',
  octave: 'Oktavtag',
  commemoration: 'Gedenkfeier',
};
export const observances: Record<string, string> = {
  observed: 'Angesetzt',
  optional: 'Frei wählbar',
  commemoration_only: 'Nur Kommemoration',
  suppressed: 'Entfällt',
  conditional: 'Örtlich bedingt',
};
export const months = [
  'Jänner',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
];
export function formatDate(value: string) {
  return new Intl.DateTimeFormat('de-AT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T12:00:00Z`));
}
