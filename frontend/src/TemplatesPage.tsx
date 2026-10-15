import { useEffect, useState, type FormEvent } from 'react';
import { Download, FileText, Upload } from 'lucide-react';
import { request } from './api';

type Template = {
  id: number;
  parish_name: string;
  name: string;
  source_filename: string;
  file_size: number;
  created_at: string;
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [parish, setParish] = useState('');
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [filter, setFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  useEffect(() => {
    request<Template[]>('/api/v1/templates')
      .then(setTemplates)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const parishes = [...new Set(templates.map((item) => item.parish_name))];
  const shown = templates.filter((item) => !filter || item.parish_name === filter);
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const form = event.currentTarget;
    setBusy(true);
    setError('');
    setSuccess('');
    const body = new FormData();
    body.append('parish_name', parish);
    body.append('name', name);
    body.append('file', file);
    try {
      const saved = await request<Template>('/api/v1/templates', { method: 'POST', body });
      setTemplates((items) =>
        [...items, saved].sort(
          (a, b) =>
            a.parish_name.localeCompare(b.parish_name, 'de') || a.name.localeCompare(b.name, 'de'),
        ),
      );
      setFilter('');
      setName('');
      setFile(null);
      form.reset();
      setSuccess(`„${saved.name}“ wurde für ${saved.parish_name} gespeichert.`);
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
          <div className="eyebrow">DOKUMENTE VORBEREITEN</div>
          <h1>Word-Vorlagen</h1>
          <p>Eigene Vorlagen für Eberndorf, Edling und weitere Pfarren verwalten.</p>
        </div>
        <span className="source-pill">
          <FileText size={15} /> DOCX
        </span>
      </section>
      <section className="list-panel template-upload">
        <h2>Vorlage hinzufügen</h2>
        <p>
          Pro Pfarre können mehrere Vorlagen mit unterschiedlichen Namen hinterlegt werden. Die
          Originaldatei bleibt erhalten.
        </p>
        <form onSubmit={upload} className="form-grid">
          <label>
            Pfarre
            <input
              required
              maxLength={120}
              list="template-parishes"
              placeholder="z. B. Eberndorf"
              value={parish}
              onChange={(e) => setParish(e.target.value)}
              disabled={busy}
            />
          </label>
          <datalist id="template-parishes">
            {parishes.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
          <label>
            Vorlagenname
            <input
              required
              maxLength={120}
              placeholder="z. B. Wöchentliche Verkündigungen"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
            />
          </label>
          <label className="full">
            Word-Datei (.docx, maximal 25 MB)
            <input
              required
              type="file"
              accept=".docx"
              disabled={busy}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <div className="full">
            <button
              className="button primary"
              disabled={busy || !file || !parish.trim() || !name.trim()}
            >
              <Upload size={16} />
              {busy ? 'Wird hochgeladen …' : 'Vorlage hochladen'}
            </button>
          </div>
        </form>
        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
        {success && (
          <div className="success-box" role="status">
            {success}
          </div>
        )}
      </section>
      <section className="list-panel">
        <div className="panel-title">
          <h2>
            Gespeicherte Vorlagen <span className="count-badge">{shown.length}</span>
          </h2>
        </div>
        <div className="filters">
          <label>
            Pfarre
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">Alle Pfarren</option>
              {parishes.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
        </div>
        {loading ? (
          <p className="template-empty" role="status">
            Vorlagen werden geladen …
          </p>
        ) : shown.length === 0 ? (
          <p className="template-empty">
            Noch keine Vorlagen vorhanden. Lade oben die erste Word-Vorlage hoch.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="templates-table">
              <thead>
                <tr>
                  <th>Pfarre</th>
                  <th>Vorlage</th>
                  <th>Datei</th>
                  <th>Hinzugefügt</th>
                  <th>
                    <span className="sr-only">Aktion</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((item) => (
                  <tr key={item.id}>
                    <td>{item.parish_name}</td>
                    <td className="name-cell">{item.name}</td>
                    <td>
                      {item.source_filename}
                      <br />
                      <small>{Math.max(1, Math.round(item.file_size / 1024))} KB</small>
                    </td>
                    <td>{new Date(item.created_at).toLocaleDateString('de-AT')}</td>
                    <td>
                      <a
                        className="button secondary"
                        href={`/api/v1/templates/${item.id}/source`}
                        aria-label={`${item.name} für ${item.parish_name} herunterladen`}
                      >
                        <Download size={15} /> Word
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="info-note">
        Die Vorlagen stehen für die spätere Dokumenterstellung bereit. Das automatische Befüllen und
        die PDF-Erstellung folgen in einem nächsten Schritt.
      </p>
    </>
  );
}
