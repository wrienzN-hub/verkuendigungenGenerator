import { useEffect, useRef, useState } from 'react';
import { Download, FilePlus2, Trash2, X } from 'lucide-react';
import { request } from './api';
import { formatDate } from './DocumentFields';
import type { DocumentSummary } from './documentTypes';

export default function DocumentArchivePage() {
  const [items, setItems] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState<DocumentSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    request<{ items: DocumentSummary[]; total: number }>(
      `/api/v1/documents?limit=10&offset=${offset}`,
      { signal: controller.signal },
    )
      .then((result) => {
        if (offset && offset >= result.total) {
          setOffset(Math.max(0, Math.floor((result.total - 1) / 10) * 10));
          return;
        }
        setItems(result.items);
        setTotal(result.total);
      })
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [offset, reload]);
  useEffect(() => {
    if (pending) dialog.current?.showModal();
    else dialog.current?.close();
  }, [pending]);
  async function remove() {
    if (!pending) return;
    setDeleting(true);
    setError('');
    try {
      await request(`/api/v1/documents/${pending.id}?revision=${pending.revision}`, {
        method: 'DELETE',
      });
      try {
        const cached = JSON.parse(
          localStorage.getItem('verkuendigungen-document-draft-v1') || 'null',
        );
        if (cached?.id === pending.id) localStorage.removeItem('verkuendigungen-document-draft-v1');
      } catch {
        /* Storage can be unavailable. */
      }
      setMessage(
        `Verkündigung für ${pending.parish_name} vom ${formatDate(pending.start)} wurde gelöscht.`,
      );
      setPending(null);
      setReload((value) => value + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  }
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">GESPEICHERTE DOKUMENTE</div>
          <h1>Verkündigungen</h1>
          <p>
            Entwürfe öffnen, Word-Dateien herunterladen und nicht mehr benötigte Verkündigungen
            löschen.
          </p>
        </div>
        <a className="button primary" href="#/erstellen">
          <FilePlus2 size={16} />
          Neue Verkündigung
        </a>
      </section>
      {error && !pending && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="success-box" role="status">
          {message}
        </div>
      )}
      <section className="list-panel document-history">
        <div className="panel-title">
          <h2>
            Alle Verkündigungen <span className="count-badge">{total}</span>
          </h2>
        </div>
        {loading ? (
          <p className="template-empty" role="status">
            Verkündigungen werden geladen …
          </p>
        ) : items.length === 0 ? (
          <p className="template-empty">Noch keine Verkündigungen gespeichert.</p>
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Pfarre</th>
                    <th>Zeitraum</th>
                    <th>Stand</th>
                    <th>Aktionen</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.parish_name}</td>
                      <td>
                        {formatDate(item.start)}–{formatDate(item.end)}
                      </td>
                      <td>{item.has_docx ? 'Word erstellt' : 'Entwurf'}</td>
                      <td>
                        <div className="history-actions">
                          <a className="button secondary" href={`#/erstellen/${item.id}`}>
                            Öffnen
                          </a>
                          {item.has_docx && (
                            <a
                              className="button secondary"
                              href={`/api/v1/documents/${item.id}/docx`}
                            >
                              <Download size={15} />
                              Word
                            </a>
                          )}
                          <button
                            type="button"
                            className="icon-button remove-item"
                            aria-label={`Verkündigung #${item.id} löschen`}
                            onClick={() => {
                              setError('');
                              setPending(item);
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
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
                disabled={offset === 0}
                onClick={() => setOffset((value) => value - 10)}
              >
                Zurück
              </button>
              <span>
                {offset + 1}–{Math.min(offset + 10, total)} von {total}
              </span>
              <button
                className="button secondary"
                disabled={offset + 10 >= total}
                onClick={() => setOffset((value) => value + 10)}
              >
                Weiter
              </button>
            </div>
          </>
        )}
      </section>
      <dialog
        ref={dialog}
        className="editor-dialog"
        aria-labelledby="delete-document-title"
        onCancel={(event) => {
          event.preventDefault();
          if (!deleting) setPending(null);
        }}
      >
        <div className="dialog-header">
          <h2 id="delete-document-title">Verkündigung löschen?</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Schließen"
            disabled={deleting}
            onClick={() => setPending(null)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="dialog-body">
          <p>
            {pending?.parish_name} · {pending && formatDate(pending.start)}–
            {pending && formatDate(pending.end)}
          </p>
          <p>Der Entwurf und seine erstellten Dateien werden dauerhaft gelöscht.</p>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
        </div>
        <div className="dialog-footer">
          <button className="button secondary" disabled={deleting} onClick={() => setPending(null)}>
            Abbrechen
          </button>
          <button className="button danger" disabled={deleting} onClick={() => void remove()}>
            {deleting ? 'Wird gelöscht …' : 'Verkündigung löschen'}
          </button>
        </div>
      </dialog>
    </>
  );
}
