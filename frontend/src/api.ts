import type { Saint, SaintPatch } from './types';

export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : `Die Anfrage konnte nicht verarbeitet werden (${response.status}).`,
    );
  }
  return response.json();
}
export function updateSaint(id: number, values: Partial<SaintPatch>) {
  return request<Saint>(`/api/v1/saints/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  });
}
