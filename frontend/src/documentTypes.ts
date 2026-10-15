export type TextMark = { start: number; end: number; bold: boolean; underline?: boolean };
export type Bilingual = { de: string; sl: string; de_marks?: TextMark[]; sl_marks?: TextMark[] };
export type Notice = {
  id: string;
  enabled: boolean;
  text: Bilingual;
  source_event_id?: number | null;
};
export type Intention = Notice & { symbol: string; reference: string | null };
export type Celebration = {
  id: string;
  enabled: boolean;
  source_celebration_id: number | null;
  title: Bilingual;
  rank: string | null;
};
export type Service = {
  id: string;
  enabled: boolean;
  time: string | null;
  location: Bilingual;
  title: Bilingual;
  intentions: Intention[];
  notices: Notice[];
};
export type DocumentDay = {
  services_revision?: number;
  id: string;
  date: string;
  enabled: boolean;
  celebrations: Celebration[];
  services: Service[];
  notices: Notice[];
};
export type Payload = {
  schema_version: number;
  template_id: number;
  template_version: string;
  parish: { id: string; name: Bilingual };
  selection: { liturgical_year: string; season: string; week: number | null; week_id: string };
  period: { start: string; end: string };
  days: DocumentDay[];
  announcements: { id: string; enabled: boolean; title: Bilingual; paragraphs: Bilingual[] }[];
  eternal_light: { enabled: boolean; dedication: Bilingual };
  office_hours: { weekday: string; from: string; until: string }[];
  contact: { persons: { name: string; phone: string }[]; email: string; website: string };
};
export type SavedDocument = {
  id: number;
  revision: number;
  payload: Payload;
  has_pdf: boolean;
  has_docx: boolean;
  created_at: string;
  updated_at: string;
};
export type DocumentSummary = {
  id: number;
  revision: number;
  parish_name: string;
  start: string;
  end: string;
  has_docx: boolean;
  updated_at: string;
};
export type DocumentOptions = {
  years: string[];
  templates: {
    id: number;
    parish_name: string;
    name: string;
    source_filename: string;
    supported: boolean;
  }[];
  preview_available: boolean;
};
