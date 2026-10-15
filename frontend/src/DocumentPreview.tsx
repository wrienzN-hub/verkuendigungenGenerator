import { lazy, Suspense } from 'react';
const WordPages = lazy(() => import('./WordPages'));

export default function DocumentPreview({
  url,
  onRefresh,
  loading,
}: {
  url: string | null;
  onRefresh: () => void;
  loading: boolean;
}) {
  return (
    <section className="list-panel document-section">
      <div className="document-selection-footer">
        <div>
          <h2>Dokumentvorschau</h2>
          <p className="field-help">
            Das tatsächliche Layout der Word-Datei mit Logo, Tabellen und Seitenumbrüchen. Zum
            Aktualisieren wird der Entwurf gespeichert.
          </p>
        </div>
        <button type="button" className="button secondary" onClick={onRefresh}>
          {loading ? 'Vorschau wird erstellt …' : 'Vorschau aktualisieren'}
        </button>
      </div>
      {url ? (
        <Suspense fallback={<p role="status">Seitenbetrachter wird geladen …</p>}>
          <WordPages key={url} url={url} />
        </Suspense>
      ) : loading ? (
        <p role="status">Die Word-Datei wird für die Vorschau gerendert …</p>
      ) : (
        <p>
          Die Vorschau wurde noch nicht geladen. Das Word-Dokument kannst du unabhängig davon
          erstellen.
        </p>
      )}
    </section>
  );
}
