import { useEffect, useRef, useState } from 'react';
import { BookOpen, Check, FileText, Upload, X, ExternalLink } from 'lucide-react';
import { request } from './api';

type ImportRun = {
  id: number;
  source_file: string;
  liturgical_year: string;
  has_source: boolean;
  report: { celebrations: number };
};
type ImportResult = {
  already_imported: boolean;
  liturgical_year?: string;
  import_run_id: number;
  celebrations: number;
  calendar_days: number;
  start: string;
  end: string;
};
const MAX_SIZE = 25 * 1024 * 1024;

export default function DirectoriumUpload({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (year: string) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ImportResult | null>(null);
  const [runs, setRuns] = useState<ImportRun[]>([]);
  const [historyError, setHistoryError] = useState(false);
  useEffect(() => {
    dialog.current?.showModal();
    const controller = new AbortController();
    request<ImportRun[]>('/api/v1/imports', { signal: controller.signal })
      .then(setRuns)
      .catch((e) => {
        if (e.name !== 'AbortError') setHistoryError(true);
      });
    return () => controller.abort();
  }, []);
  const select = (next: File | null) => {
    setError('');
    setResult(null);
    if (next && (!next.name.toLowerCase().endsWith('.pdf') || next.size > MAX_SIZE)) {
      setFile(null);
      setError('Bitte eine PDF-Datei mit höchstens 25 MB auswählen.');
      return;
    }
    setFile(next);
  };
  const upload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError('');
    const body = new FormData();
    body.append('file', file);
    try {
      setResult(
        await request<ImportResult>('/api/v1/imports/directorium', { method: 'POST', body }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const finish = () => {
    if (busy) return;
    if (result) {
      const year =
        result.liturgical_year ||
        runs.find((r) => r.id === result.import_run_id)?.liturgical_year ||
        `${result.start.slice(0, 4)}/${String(Number(result.start.slice(0, 4)) + 1).slice(-2)}`;
      onImported(year);
    } else onClose();
  };
  return (
    <dialog
      ref={dialog}
      className="editor-dialog upload-dialog"
      aria-labelledby="upload-title"
      onCancel={(e) => {
        e.preventDefault();
        finish();
      }}
      onClick={(e) => {
        if (e.target === dialog.current) finish();
      }}
    >
      <form onSubmit={upload}>
        <div className="dialog-header">
          <div>
            <span className="eyebrow">KALENDER ERGÄNZEN</span>
            <h2 id="upload-title">Directorium hochladen</h2>
            <p>Ein neues Kirchenjahr aus einer PDF-Datei importieren.</p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={finish}
            disabled={busy}
            aria-label="Schließen"
          >
            <X size={20} />
          </button>
        </div>
        <div className="dialog-body">
          {result ? (
            <div className="upload-result" role="status">
              <span className="icon-box">
                <Check size={25} />
              </span>
              <h3>
                {result.already_imported
                  ? 'Dieses Directorium ist bereits vorhanden.'
                  : 'Directorium erfolgreich importiert.'}
              </h3>
              <p>
                {result.celebrations} Einträge für {result.calendar_days} Kalendertage sind
                verfügbar.
              </p>
              <small>Bereits vorhandene Änderungen bleiben erhalten.</small>
            </div>
          ) : (
            <>
              <input
                ref={input}
                id="directorium-file"
                type="file"
                accept=".pdf,application/pdf"
                className="sr-only"
                disabled={busy}
                onChange={(e) => select(e.target.files?.[0] || null)}
              />
              <label
                className={`upload-dropzone ${busy ? 'upload-busy' : ''}`}
                htmlFor="directorium-file"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (!busy) select(e.dataTransfer.files[0] || null);
                }}
              >
                {file ? <FileText size={32} /> : <Upload size={32} />}
                <strong>{file ? file.name : 'PDF auswählen oder hier ablegen'}</strong>
                <span>
                  {file
                    ? `${(file.size / 1024 / 1024).toLocaleString('de-AT', {
                        maximumFractionDigits: 1,
                      })} MB · Andere Datei auswählen`
                    : 'Directorium der Diözese Gurk · bis zu 25 MB'}
                </span>
              </label>
              <p className="upload-description">
                Das Kirchenjahr wird automatisch erkannt. Unterstützt werden PDFs mit lesbarem Text
                und Monats-/Tagesabschnitten wie im vorhandenen Gurker Directorium.
              </p>
              <p className="upload-description">
                Vorhandene Kirchenjahre werden nicht überschrieben. Die Originaldatei bleibt
                gespeichert.
              </p>
              {busy && (
                <p className="upload-progress" role="status">
                  <span className="spinner" />
                  PDF wird gelesen und importiert …
                </p>
              )}
            </>
          )}
          {error && (
            <div role="alert" className="error-box">
              {error}
            </div>
          )}
          <div className="import-history">
            <h3>
              <BookOpen size={16} />
              Vorhandene Directorien
            </h3>
            {historyError ? (
              <p>Die vorhandenen Directorien konnten nicht geladen werden.</p>
            ) : runs.length ? (
              runs.map((run) => (
                <div className="import-history-row" key={run.id}>
                  <div>
                    <strong>{run.liturgical_year}</strong>
                    <span>{run.source_file}</span>
                    <small>{run.report.celebrations} Einträge</small>
                  </div>
                  {run.has_source && (
                    <a
                      href={`/api/v1/imports/${run.id}/source`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-link"
                      aria-label={`Original-PDF ${run.liturgical_year} öffnen`}
                    >
                      <ExternalLink size={16} />
                      PDF
                    </a>
                  )}
                </div>
              ))
            ) : (
              <p>Noch keine Directorien vorhanden.</p>
            )}
          </div>
        </div>
        <div className="dialog-footer">
          {result ? (
            <button type="button" className="button primary" onClick={finish}>
              Einträge anzeigen
            </button>
          ) : (
            <>
              <button type="button" className="button secondary" disabled={busy} onClick={finish}>
                Abbrechen
              </button>
              <button type="submit" className="button primary" disabled={busy || !file}>
                <Upload size={16} />
                {busy ? 'Import läuft …' : 'Directorium importieren'}
              </button>
            </>
          )}
        </div>
      </form>
    </dialog>
  );
}
