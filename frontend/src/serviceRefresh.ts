import { request } from './api';
import type { Payload, Service } from './documentTypes';
export type ServiceDraft = {
  payload: Payload;
  id?: number;
  revision?: number;
  hasDocx: boolean;
  dirty: boolean;
  serviceChanges?: string[];
};
export type ServiceDay = { date: string; services: Service[]; revision: number };
export async function freshServices(payload: Payload) {
  const query = new URLSearchParams({
    parish: payload.parish.id,
    start: payload.period.start,
    end: payload.period.end,
  });
  return (
    await request<{ items: ServiceDay[] }>(`/api/v1/services?${query}`, { cache: 'no-store' })
  ).items;
}
export function mergeServices(draft: ServiceDraft, rows: ServiceDay[], force = false) {
  const changed = new Set(
    draft.serviceChanges ?? (draft.dirty ? draft.payload.days.map((d) => d.date) : []),
  );
  let modified = false,
    conflict = false;
  const days = draft.payload.days.map((day) => {
    const row = rows.find((r) => r.date === day.date);
    if (!row || !row.revision || row.revision < (day.services_revision ?? 0)) return day;
    if (!force && changed.has(day.date)) {
      if (row.revision !== (day.services_revision ?? 0)) conflict = true;
      return day;
    }
    if (
      JSON.stringify(day.services) === JSON.stringify(row.services) &&
      day.services_revision === row.revision
    )
      return day;
    modified = true;
    return { ...day, services: row.services, services_revision: row.revision };
  });
  return {
    conflict,
    draft: modified
      ? {
          ...draft,
          payload: { ...draft.payload, days },
          dirty: true,
          hasDocx: false,
          serviceChanges: force ? [] : draft.serviceChanges,
        }
      : force
      ? { ...draft, serviceChanges: [] }
      : draft,
  };
}
