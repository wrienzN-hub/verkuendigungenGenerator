export type Saint = {
  id: number;
  name: string;
  name_sl: string | null;
  celebration_date: string;
  liturgical_year: string;
  rank_code: string | null;
  observance_status: string;
  disabled: boolean;
  applicability_note: string | null;
  source_text: string;
  source_reference: string;
};
export type SaintPage = { items: Saint[]; total: number; limit: number; offset: number };
export type LiturgicalWeek = {
  id: string;
  season: string;
  season_label: string;
  week: number | null;
  label: string;
  start: string;
  end: string;
};
export type FilterOptions = {
  years: string[];
  total: number;
  active: number;
};
export type SaintPatch = Pick<
  Saint,
  'name' | 'name_sl' | 'rank_code' | 'observance_status' | 'disabled' | 'applicability_note'
>;
