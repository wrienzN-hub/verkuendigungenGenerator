import type { Bilingual } from './documentTypes';
export type EventWeek = { year: string; week_id: string };
export type EventInput = { name: string; parishes: string[]; weeks: EventWeek[]; text: Bilingual };
export type EventRecord = EventInput & {
  id: number;
  revision: number;
  created_at: string;
  updated_at: string;
};
