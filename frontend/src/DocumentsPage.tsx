import { useEffect, useState } from 'react';
import { Download, FilePlus2, Save } from 'lucide-react';
import { request } from './api';
import type { LiturgicalWeek } from './types';
import type { DocumentOptions, DocumentSummary, Payload, SavedDocument } from './documentTypes';
import { formatDate } from './DocumentFields';
import DocumentDayEditor from './DocumentDayEditor';
import DocumentExtras from './DocumentExtras';
import DocumentPreview from './DocumentPreview';

type Draft = { payload: Payload; id?: number; revision?: number; hasPdf: boolean; dirty: boolean };
const STORAGE = 'verkuendigungen-document-draft-v1';
function recover(): Draft | null {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE) || 'null');
    return value?.payload?.schema_version === 1 && Array.isArray(value.payload.days) ? value : null;
  } catch {
    return null;
  }
}

export default function DocumentsPage() {
  const [options, setOptions] = useState<DocumentOptions | null>(null);
  const [parish, setParish] = useState('');
  const [template, setTemplate] = useState('');
  const [year, setYear] = useState('');
  const [weeks, setWeeks] = useState<LiturgicalWeek[]>([]);
  const [weekId, setWeekId] = useState('');
  const [weeksLoading, setWeeksLoading] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(recover);
  const [tab, setTab] = useState('days');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [history, setHistory] = useState<DocumentSummary[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyError, setHistoryError] = useState('');
  const [storageError, setStorageError] = useState(false);
  const refreshHistory = (offset = historyOffset) =>
    request<{ items: DocumentSummary[]; total: number }>(
      `/api/v1/documents?limit=10&offset=${offset}`,
    )
      .then((result) => {
        setHistory(result.items);
        setHistoryTotal(result.total);
        setHistoryError('');
      })
      .catch(() => setHistoryError('Gespeicherte Entwürfe konnten nicht geladen werden.'));
  useEffect(() => {
    request<DocumentOptions>('/api/v1/documents/options')
      .then((result) => {
        setOptions(result);
        const first = result.templates.find((t) => t.supported);
        setParish(first?.parish_name ?? '');
        setTemplate(first ? String(first.id) : '');
        setYear(result.years[0] ?? '');
      })
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    void refreshHistory(historyOffset);
  }, [historyOffset]);
  useEffect(() => {
    if (!year) return;
    const controller = new AbortController();
    setWeeksLoading(true);
    setWeeks([]);
    setWeekId('');
    request<LiturgicalWeek[]>(`/api/v1/documents/weeks?year=${encodeURIComponent(year)}`, {
      signal: controller.signal,
    })
      .then((result) => {
        setWeeks(result);
        setWeekId(result[0]?.id ?? '');
      })
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setWeeksLoading(false);
      });
    return () => controller.abort();
  }, [year]);
  useEffect(() => {
    try {
      if (draft) localStorage.setItem(STORAGE, JSON.stringify(draft));
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }, [draft]);
  useEffect(() => {
    const listener = (event: BeforeUnloadEvent) => {
      if (draft?.dirty) event.preventDefault();
    };
    window.addEventListener('beforeunload', listener);
    return () => window.removeEventListener('beforeunload', listener);
  }, [draft?.dirty]);
  const parishes = [...new Set(options?.templates.map((t) => t.parish_name) ?? [])];
  const templates = options?.templates.filter((t) => t.parish_name === parish) ?? [];
  const selectedWeek = weeks.find((week) => week.id === weekId);
  const canReplace = () =>
    !draft?.dirty ||
    window.confirm(
      'Der aktuelle Entwurf hat ungespeicherte Änderungen. Trotzdem einen anderen Entwurf laden?',
    );
  function edit(change: (payload: Payload) => void) {
    setDraft((current) => {
      if (!current) return current;
      const payload = structuredClone(current.payload);
      change(payload);
      return { ...current, payload, dirty: true, hasPdf: false };
    });
    setMessage('');
  }
  async function prepare() {
    if (!canReplace()) return;
    setBusy('load');
    setError('');
    setMessage('');
    try {
      const result = await request<{ payload: Payload; warnings: string[] }>(
        '/api/v1/documents/prepare',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ template_id: Number(template), year, week_id: weekId }),
        },
      );
      setDraft({ payload: result.payload, hasPdf: false, dirty: true });
      setWarnings(result.warnings);
      setTab('days');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }
  async function save(): Promise<SavedDocument> {
    if (!draft) throw new Error('Bitte zuerst eine Woche laden.');
    if (draft.id && !draft.dirty) return request<SavedDocument>(`/api/v1/documents/${draft.id}`);
    const saved = await request<SavedDocument>(
      draft.id ? `/api/v1/documents/${draft.id}` : '/api/v1/documents',
      {
        method: draft.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: draft.payload, revision: draft.revision ?? null }),
      },
    );
    setDraft({
      payload: saved.payload,
      id: saved.id,
      revision: saved.revision,
      hasPdf: saved.has_pdf,
      dirty: false,
    });
    void refreshHistory();
    return saved;
  }
  async function action(generate: boolean) {
    setBusy(generate ? 'generate' : 'save');
    setError('');
    setMessage('');
    try {
      const saved = await save();
      if (generate) {
        await request(`/api/v1/documents/${saved.id}/generate?revision=${saved.revision}`, {
          method: 'POST',
        });
        setDraft((current) => (current ? { ...current, hasPdf: true } : current));
        setMessage('Die Abkündigung wurde erstellt. Du kannst das PDF jetzt herunterladen.');
        void refreshHistory();
      } else setMessage('Der Entwurf wurde gespeichert.');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }
  async function open(id: number) {
    if (!canReplace()) return;
    setBusy('load');
    setError('');
    setMessage('');
    try {
      const saved = await request<SavedDocument>(`/api/v1/documents/${id}`);
      setDraft({
        payload: saved.payload,
        id: saved.id,
        revision: saved.revision,
        hasPdf: saved.has_pdf,
        dirty: false,
      });
      setWarnings([]);
      setTab('days');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">WOCHE FÜR WOCHE VORBEREITET</div>
          <h1>Abkündigung erstellen</h1>
          <p>Vorlage auswählen, die Woche gestalten und als PDF herunterladen.</p>
        </div>
        <span className="source-pill">
          <FilePlus2 size={16} />
          Word → PDF
        </span>
      </section>
      <fieldset className="creator-fieldset" disabled={!!busy}>
        <section className="list-panel document-section">
          <div className="section-step">1 · AUSWAHL</div>
          <h2>Pfarre und liturgische Woche</h2>
          <div className="document-selection">
            <label>
              Pfarre
              <select
                value={parish}
                onChange={(e) => {
                  setParish(e.target.value);
                  const first = options?.templates.find(
                    (t) => t.parish_name === e.target.value && t.supported,
                  );
                  setTemplate(first ? String(first.id) : '');
                }}
              >
                {parishes.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </label>
            <label>
              Word-Vorlage
              <select value={template} onChange={(e) => setTemplate(e.target.value)}>
                <option value="" disabled>
                  Vorlage auswählen
                </option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id} disabled={!t.supported}>
                    {t.name}
                    {!t.supported ? ' · Einrichtung erforderlich' : ''}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Kirchenjahr
              <select value={year} onChange={(e) => setYear(e.target.value)}>
                {options?.years.map((y) => <option key={y}>{y}</option>)}
              </select>
            </label>
            <label>
              Liturgische Woche
              <select
                value={weekId}
                disabled={weeksLoading}
                onChange={(e) => setWeekId(e.target.value)}
              >
                {weeks.length === 0 && (
                  <option value="">
                    {weeksLoading ? 'Wochen werden geladen …' : 'Keine Wochen vorhanden'}
                  </option>
                )}
                {[...new Set(weeks.map((w) => w.season))].map((season) => (
                  <optgroup
                    key={season}
                    label={weeks.find((w) => w.season === season)?.season_label}
                  >
                    {weeks
                      .filter((w) => w.season === season)
                      .map((week) => (
                        <option key={week.id} value={week.id}>
                          {week.label} · {formatDate(week.start)}–{formatDate(week.end)}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
            </label>
          </div>
          <div className="document-selection-footer">
            <p>
              {selectedWeek
                ? `Sonntag bis Sonntag · ${formatDate(selectedWeek.start)}–${formatDate(
                    selectedWeek.end,
                  )} · 8 Tage`
                : 'Bitte ein Directorium importieren, damit Wochen verfügbar sind.'}
            </p>
            <button
              type="button"
              className="button primary"
              onClick={() => void prepare()}
              disabled={!template || !year || !weekId || weeksLoading}
            >
              {busy === 'load' ? 'Wird geladen …' : draft ? 'Neuen Entwurf laden' : 'Woche laden'}
            </button>
          </div>
          <p className="field-help">
            Eine neue Auswahl wird erst beim Laden übernommen.{' '}
            <a href="#/vorlagen">Word-Vorlagen verwalten</a>
          </p>
        </section>
        {warnings.map((warning) => (
          <div key={warning} className="import-warning" role="status">
            {warning}
          </div>
        ))}
        {options && !options.pdf_available && (
          <div className="import-warning">
            Zum Erstellen der PDFs benötigt der Server Microsoft Word (Windows) oder LibreOffice.
            Entwürfe kannst du bereits vorbereiten und speichern.
          </div>
        )}
        {draft && (
          <>
            <section className="document-workspace-heading">
              <div className="section-step">2 · INHALTE BEARBEITEN</div>
              <h2>
                {draft.payload.parish.name.de || draft.payload.parish.name.sl} ·{' '}
                {formatDate(draft.payload.period.start)}–{formatDate(draft.payload.period.end)}
              </h2>
              <p>
                {draft.id ? `Entwurf #${draft.id}` : 'Neuer Entwurf'} ·{' '}
                {draft.dirty ? 'Änderungen noch nicht gespeichert' : 'Gespeichert'}
              </p>
            </section>
            <div className="document-tabs" role="tablist" aria-label="Abkündigung bearbeiten">
              {[
                ['days', 'Gottesdienste & Heilige'],
                ['extras', 'Termine & Kontakt'],
                ['preview', 'Inhaltsvorschau'],
              ].map(([value, label]) => (
                <button
                  type="button"
                  role="tab"
                  id={`tab-${value}`}
                  aria-controls={`panel-${value}`}
                  aria-selected={tab === value}
                  className={tab === value ? 'active' : ''}
                  key={value}
                  onClick={() => setTab(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
              {tab === 'days' && (
                <div className="document-days">
                  {draft.payload.days.map((day, index) => (
                    <DocumentDayEditor
                      key={day.id}
                      day={day}
                      first={index === 0}
                      onChange={(value) =>
                        edit((p) => {
                          p.days[index] = value;
                        })
                      }
                    />
                  ))}
                </div>
              )}
              {tab === 'extras' && <DocumentExtras payload={draft.payload} edit={edit} />}
              {tab === 'preview' && <DocumentPreview payload={draft.payload} />}
            </div>
            <section className="list-panel document-output">
              <div>
                <div className="section-step">3 · AUSGABE</div>
                <h2>Bereit für die Gemeinde</h2>
                <p>
                  {busy === 'generate'
                    ? 'Word wird befüllt und nach PDF konvertiert. Das kann einen Moment dauern …'
                    : 'Speichere den Entwurf oder erstelle die Abkündigung als PDF.'}
                </p>
              </div>
              <div className="document-actions">
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => void action(false)}
                >
                  <Save size={16} />
                  Entwurf speichern
                </button>
                <button type="button" className="button primary" onClick={() => void action(true)}>
                  <FilePlus2 size={16} />
                  {busy === 'generate' ? 'PDF wird erstellt …' : 'Abkündigung erstellen'}
                </button>
              </div>
            </section>
          </>
        )}
      </fieldset>
      {storageError && (
        <div className="import-warning">
          Der Browser konnte die lokale Zwischenablage des Entwurfs nicht speichern. Bitte den
          Entwurf auf dem Server speichern.
        </div>
      )}
      {error && (
        <div className="error-box document-feedback" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="success-box document-feedback" role="status">
          {message}
        </div>
      )}
      {draft?.hasPdf && !draft.dirty && draft.id && (
        <div className="document-download">
          <a className="button primary" href={`/api/v1/documents/${draft.id}/pdf`}>
            <Download size={17} />
            PDF herunterladen
          </a>
        </div>
      )}
      <section className="list-panel document-history">
        <div className="panel-title">
          <h2>
            Gespeicherte Abkündigungen <span className="count-badge">{historyTotal}</span>
          </h2>
        </div>
        {historyError ? (
          <p className="error-box" role="alert">
            {historyError}
          </p>
        ) : history.length === 0 ? (
          <p className="template-empty">Noch keine Entwürfe gespeichert.</p>
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Pfarre</th>
                    <th>Zeitraum</th>
                    <th>Stand</th>
                    <th>Aktion</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td>{item.parish_name}</td>
                      <td>
                        {formatDate(item.start)}–{formatDate(item.end)}
                      </td>
                      <td>{item.has_pdf ? 'PDF erstellt' : 'Entwurf'}</td>
                      <td>
                        <div className="history-actions">
                          <button
                            type="button"
                            className="button secondary"
                            disabled={!!busy}
                            onClick={() => void open(item.id)}
                          >
                            Öffnen
                          </button>
                          {item.has_pdf && (
                            <a
                              className="button secondary"
                              href={`/api/v1/documents/${item.id}/pdf`}
                            >
                              PDF
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="history-pagination">
              <button
                className="button secondary"
                disabled={historyOffset === 0 || !!busy}
                onClick={() => setHistoryOffset((offset) => offset - 10)}
              >
                Zurück
              </button>
              <span>
                {historyOffset + 1}–{Math.min(historyOffset + 10, historyTotal)} von {historyTotal}
              </span>
              <button
                className="button secondary"
                disabled={historyOffset + 10 >= historyTotal || !!busy}
                onClick={() => setHistoryOffset((offset) => offset + 10)}
              >
                Weiter
              </button>
            </div>
          </>
        )}
      </section>
    </>
  );
}
