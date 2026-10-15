import { useEffect, useRef, useState } from 'react';
import { CalendarDays, Plus, Save, Trash2, Pencil, X } from 'lucide-react';
import { request } from './api';
import { emptyText, formatDate, showText } from './DocumentFields';
import RichInput from './RichInput';
import type { DocumentOptions } from './documentTypes';
import type { EventInput, EventRecord } from './eventTypes';

type Week = {
  id: string;
  label: string;
  start: string;
  end: string;
  season: string;
  season_label: string;
};
const blank = (): EventInput => ({ name: '', parishes: [], weeks: [], text: emptyText() });

function EventEditor({
  item,
  options,
  onClose,
  onSaved,
}: {
  item: EventRecord | null;
  options: DocumentOptions;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = useRef<EventInput>(
    item
      ? { name: item.name, parishes: item.parishes, weeks: item.weeks, text: item.text }
      : blank(),
  );
  const [form, setForm] = useState(initial.current);
  const [year, setYear] = useState(item?.weeks[0]?.year ?? options.years[0] ?? '');
  const [weekSearch, setWeekSearch] = useState('');
  const [season, setSeason] = useState('');
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  useEffect(() => {
    if (!year) return;
    const controller = new AbortController();
    setWeeks([]);
    request<Week[]>(`/api/v1/documents/weeks?year=${encodeURIComponent(year)}`, {
      signal: controller.signal,
    })
      .then(setWeeks)
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message);
      });
    return () => controller.abort();
  }, [year]);
  const dirty = JSON.stringify(form) !== JSON.stringify(initial.current);
  useEffect(() => {
    const listener = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener('beforeunload', listener);
    return () => window.removeEventListener('beforeunload', listener);
  }, [dirty]);
  function close() {
    if (!busy && (!dirty || window.confirm('Ungespeicherte Änderungen verwerfen?'))) onClose();
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await request(item ? `/api/v1/events/${item.id}` : '/api/v1/events', {
        method: item ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, ...(item ? { revision: item.revision } : {}) }),
      });
      onSaved();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  const parishes = [...new Set([...options.templates.map((t) => t.parish_name), ...form.parishes])];
  return (
    <dialog
      ref={dialog}
      className="editor-dialog"
      aria-labelledby="event-editor-title"
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === dialog.current) close();
      }}
    >
      <form onSubmit={(e) => void save(e)}>
        <div className="dialog-header">
          <div>
            <span className="eyebrow">TERMINE VERWALTEN</span>
            <h2 id="event-editor-title">{item ? 'Termin bearbeiten' : 'Neuer Termin'}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Schließen"
            disabled={busy}
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <div className="dialog-body">
          <fieldset className="creator-fieldset" disabled={busy}>
            <label>
              Interner Name
              <input
                autoFocus
                required
                maxLength={200}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </label>
            <p className="field-help">
              Zum Beispiel Firmvorbereitungen. Dieser Name erscheint nur in der Verwaltung.
            </p>
            <fieldset>
              <legend>Pfarren</legend>
              {parishes.map((p) => (
                <label className="inline-check" key={p}>
                  <input
                    type="checkbox"
                    checked={form.parishes.includes(p)}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        parishes: e.target.checked
                          ? [...form.parishes, p]
                          : form.parishes.filter((v) => v !== p),
                      })
                    }
                  />
                  {p}
                </label>
              ))}
            </fieldset>
            <RichInput
              label="Inhalt der Verkündigung"
              multiline
              value={form.text.de}
              marks={form.text.de_marks}
              onChange={(de, de_marks) => setForm({ ...form, text: { de, de_marks, sl: '' } })}
            />
            <p className="field-help">
              Den gesamten Inhalt hier eingeben – auch beide Sprachen. Einzelne Wörter können fett
              formatiert werden.
            </p>
            <fieldset>
              <legend>Wochen zuordnen</legend>
              <label>
                Kirchenjahr
                <select value={year} onChange={(e) => setYear(e.target.value)}>
                  {options.years.map((y) => (
                    <option key={y}>{y}</option>
                  ))}
                </select>
              </label>
              <p className="field-help">
                Mehrere Wochen und Kirchenjahre sind möglich. Ohne Zuordnung bleibt der Termin als
                Entwurf gespeichert.
              </p>
              <div className="bilingual-fields">
                <label>
                  Wochen suchen
                  <input
                    type="search"
                    value={weekSearch}
                    onChange={(e) => setWeekSearch(e.target.value)}
                    placeholder="Advent, 29.11., 2026 …"
                  />
                </label>
                <label>
                  Liturgische Zeit
                  <select
                    aria-label="Liturgische Zeit"
                    value={season}
                    onChange={(e) => setSeason(e.target.value)}
                  >
                    <option value="">Alle Zeiten</option>
                    {[...new Set(weeks.map((w) => w.season))].map((s) => (
                      <option key={s} value={s}>
                        {weeks.find((w) => w.season === s)?.season_label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="event-week-list">
                {weeks
                  .filter(
                    (w) =>
                      (!season || w.season === season) &&
                      `${w.label} ${w.season_label} ${formatDate(w.start)} ${formatDate(w.end)}`
                        .toLocaleLowerCase('de')
                        .includes(weekSearch.toLocaleLowerCase('de')),
                  )
                  .map((w) => (
                    <label className="inline-check" key={w.id}>
                      <input
                        type="checkbox"
                        checked={form.weeks.some((v) => v.year === year && v.week_id === w.id)}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            weeks: e.target.checked
                              ? [...form.weeks, { year, week_id: w.id }]
                              : form.weeks.filter((v) => v.year !== year || v.week_id !== w.id),
                          })
                        }
                      />
                      {w.season_label}: {w.label} · {formatDate(w.start)} – {formatDate(w.end)}
                    </label>
                  ))}
              </div>
              <p>{form.weeks.length} Woche(n) ausgewählt</p>
              {form.weeks
                .filter((w) => w.year !== year)
                .map((w) => (
                  <div key={w.year + w.week_id}>
                    {w.year} · {w.week_id}
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Wochenzuordnung entfernen"
                      onClick={() => setForm({ ...form, weeks: form.weeks.filter((v) => v !== w) })}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
            </fieldset>
          </fieldset>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
        </div>
        <div className="dialog-footer">
          <button type="button" className="button secondary" disabled={busy} onClick={close}>
            Abbrechen
          </button>
          <button
            className="button primary"
            disabled={busy || !form.name.trim() || !form.parishes.length || !form.text.de.trim()}
          >
            <Save size={16} />
            {busy ? 'Wird gespeichert …' : 'Speichern'}
          </button>
        </div>
      </form>
    </dialog>
  );
}

export default function EventsPage() {
  const [options, setOptions] = useState<DocumentOptions | null>(null);
  const [items, setItems] = useState<EventRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [parish, setParish] = useState('');
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<EventRecord | null | undefined>(undefined);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    request<DocumentOptions>('/api/v1/documents/options')
      .then(setOptions)
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      const query = new URLSearchParams({ limit: '10', offset: String(offset), search, parish });
      request<{ items: EventRecord[]; total: number }>(`/api/v1/events?${query}`, {
        signal: controller.signal,
      })
        .then((r) => {
          if (offset && offset >= r.total) {
            setOffset(Math.max(0, Math.floor((r.total - 1) / 10) * 10));
            return;
          }
          setItems(r.items);
          setTotal(r.total);
        })
        .catch((e: Error) => {
          if (e.name !== 'AbortError') setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [offset, search, parish, reload]);
  async function remove(item: EventRecord) {
    if (
      !window.confirm(
        `Termin „${item.name}“ löschen? Bereits gespeicherte Verkündigungen bleiben erhalten.`,
      )
    )
      return;
    setBusy(true);
    try {
      await request(`/api/v1/events/${item.id}?revision=${item.revision}`, { method: 'DELETE' });
      setReload((r) => r + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const parishes = [...new Set(options?.templates.map((t) => t.parish_name) ?? [])];
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">INHALTE VORBEREITEN</div>
          <h1>Termine</h1>
          <p>Inhalte für eine oder mehrere Pfarren und Wochen verwalten.</p>
        </div>
        <button className="button primary" disabled={!options} onClick={() => setEditing(null)}>
          <Plus size={16} />
          Neuer Termin
        </button>
      </section>
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      <section className="list-panel">
        <div className="panel-title">
          <h2>
            <CalendarDays size={18} />
            Gespeicherte Termine <span className="count-badge">{total}</span>
          </h2>
        </div>
        <div className="filters">
          <label>
            Suche
            <input
              type="search"
              maxLength={200}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setOffset(0);
              }}
            />
          </label>
          <label>
            Pfarre filtern
            <select
              value={parish}
              onChange={(e) => {
                setParish(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">Alle Pfarren</option>
              {parishes.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
        </div>
        {loading ? (
          <p role="status">Termine werden geladen …</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Interner Name</th>
                  <th>Inhalt</th>
                  <th>Pfarren</th>
                  <th>Wochen</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{showText(item.text).slice(0, 120)}</td>
                    <td>{item.parishes.join(', ')}</td>
                    <td>
                      {item.weeks.length
                        ? item.weeks.map((w) => (
                            <div key={w.year + w.week_id}>
                              {w.year} · {formatDate(w.week_id.split(':').at(-1) ?? '')}
                            </div>
                          ))
                        : 'Keine Zuordnung'}
                    </td>
                    <td>
                      <div className="history-actions">
                        <button className="button secondary" onClick={() => setEditing(item)}>
                          <Pencil size={16} />
                          Bearbeiten
                        </button>
                        <button
                          className="icon-button remove-item"
                          aria-label={`Termin ${item.name} löschen`}
                          disabled={busy}
                          onClick={() => void remove(item)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && <p className="template-empty">Keine Termine vorhanden.</p>}
          </div>
        )}
        <div className="history-pagination">
          <button
            className="button secondary"
            disabled={offset === 0}
            onClick={() => setOffset((o) => o - 10)}
          >
            Zurück
          </button>
          <span>
            {total ? offset + 1 : 0}–{Math.min(offset + 10, total)} von {total}
          </span>
          <button
            className="button secondary"
            disabled={offset + 10 >= total}
            onClick={() => setOffset((o) => o + 10)}
          >
            Weiter
          </button>
        </div>
      </section>
      {editing !== undefined && options && (
        <EventEditor
          item={editing}
          options={options}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            setReload((r) => r + 1);
          }}
        />
      )}
    </>
  );
}
