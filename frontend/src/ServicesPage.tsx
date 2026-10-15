import { useEffect, useRef, useState } from 'react';
import { Save, RefreshCw } from 'lucide-react';
import { request } from './api';
import type { DocumentDay, DocumentOptions, Service } from './documentTypes';
import DocumentDayEditor from './DocumentDayEditor';

type Saved = { services: Service[]; revision: number };
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`;
};
export default function ServicesPage() {
  const [parishes, setParishes] = useState<string[]>([]);
  const [parish, setParish] = useState('');
  const [date, setDate] = useState(today);
  const [day, setDay] = useState<DocumentDay | null>(null);
  const [revision, setRevision] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const live = useRef({ day, revision, dirty, busy, parish, date });
  live.current = { day, revision, dirty, busy, parish, date };
  useEffect(() => {
    request<DocumentOptions>('/api/v1/documents/options')
      .then((o) => {
        const names = [...new Set(o.templates.map((t) => t.parish_name))];
        setParishes(names);
        setParish(names[0] ?? '');
      })
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!parish || !date) return;
    const controller = new AbortController();
    setLoading(true);
    setDay(null);
    setError('');
    setMessage('');
    request<Saved>(`/api/v1/services/${date}?parish=${encodeURIComponent(parish)}`, {
      signal: controller.signal,
      cache: 'no-store',
    })
      .then((r) => {
        setRevision(r.revision);
        setDay({
          id: 'day-' + date,
          date,
          enabled: true,
          celebrations: [],
          notices: [],
          services: r.services,
        });
        setDirty(false);
      })
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [parish, date]);
  useEffect(() => {
    const f = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener('beforeunload', f);
    return () => window.removeEventListener('beforeunload', f);
  }, [dirty]);
  async function refresh(force = false) {
    const initial = live.current;
    if (!initial.parish || !initial.day || initial.busy) return;
    if (
      force &&
      initial.dirty &&
      !window.confirm('Ungespeicherte Gottesdienste verwerfen und neu laden?')
    )
      return;
    const r = await request<Saved>(
      `/api/v1/services/${initial.date}?parish=${encodeURIComponent(initial.parish)}`,
      { cache: 'no-store' },
    );
    const current = live.current;
    if (
      current.parish !== initial.parish ||
      current.date !== initial.date ||
      !current.day ||
      current.busy
    )
      return;
    if (current.dirty && !force) {
      if (r.revision !== current.revision)
        setError(
          'Die Gottesdienste wurden andernorts geändert. Deine Eingaben bleiben erhalten. Bitte neu laden.',
        );
      return;
    }
    if (r.revision !== current.revision || force) {
      setRevision(r.revision);
      setDay({ ...current.day, services: r.services });
      setDirty(false);
      setError('');
    }
  }
  useEffect(() => {
    const update = () => {
      if (document.visibilityState === 'visible')
        void refresh().catch((e: Error) => setError(e.message));
    };
    window.addEventListener('focus', update);
    document.addEventListener('visibilitychange', update);
    return () => {
      window.removeEventListener('focus', update);
      document.removeEventListener('visibilitychange', update);
    };
  }, []);
  function changeSelection(action: () => void) {
    if (!dirty || window.confirm('Ungespeicherte Gottesdienste verwerfen?')) action();
  }
  async function save() {
    if (!day) return;
    setBusy(true);
    setError('');
    try {
      const r = await request<Saved>(
        `/api/v1/services/${date}?parish=${encodeURIComponent(parish)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ services: day.services, revision }),
        },
      );
      setRevision(r.revision);
      setDay({ ...day, services: r.services });
      setDirty(false);
      setMessage(
        'Gottesdienste gespeichert. Neu geladene Wochen übernehmen diese Angaben für dieses Datum.',
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">EINMAL PRO DATUM PFLEGEN</div>
          <h1>Gottesdienste</h1>
          <p>
            Gottesdienste und Intentionen pro Pfarre und Datum. Der gemeinsame Sonntag benachbarter
            Verkündigungen wird automatisch wiederverwendet.
          </p>
        </div>
      </section>
      <section className="list-panel document-section">
        <div className="bilingual-fields">
          <label>
            Pfarre
            <select
              disabled={busy}
              value={parish}
              onChange={(e) => changeSelection(() => setParish(e.target.value))}
            >
              {parishes.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <label>
            Datum
            <input
              type="date"
              disabled={busy}
              value={date}
              onChange={(e) => {
                if (e.target.value) changeSelection(() => setDate(e.target.value));
              }}
            />
          </label>
        </div>
      </section>
      {loading ? (
        <p role="status">Gottesdienste werden geladen …</p>
      ) : (
        day && (
          <fieldset className="creator-fieldset" disabled={busy}>
            <DocumentDayEditor
              key={parish + date}
              servicesOnly
              day={day}
              onChange={(d) => {
                setDay(d);
                setDirty(true);
                setMessage('');
              }}
            />
            <button
              type="button"
              className="button secondary"
              onClick={() => void refresh(true).catch((e: Error) => setError(e.message))}
            >
              <RefreshCw size={16} />
              Gottesdienste neu laden
            </button>
            <button className="button primary" onClick={() => void save()} disabled={!dirty}>
              <Save size={16} />
              {busy ? 'Wird gespeichert …' : 'Gottesdienste speichern'}
            </button>
          </fieldset>
        )
      )}
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="success-box" role="status">
          {message}
        </div>
      )}
    </>
  );
}
