import { useEffect, useRef, useState } from 'react';
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = workerUrl;

export default function WordPages({ url }: { url: string }) {
  const container = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false;
    const element = container.current!;
    element.replaceChildren();
    setLoading(true);
    setError('');
    const task = getDocument({ url });
    void (async () => {
      try {
        const document = await task.promise;
        for (let number = 1; number <= document.numPages; number++) {
          if (cancelled) return;
          const page = await document.getPage(number);
          if (cancelled) return;
          const viewport = page.getViewport({ scale: 1.5 });
          const canvas = documentElement('canvas');
          canvas.width = Math.ceil(viewport.width);
          canvas.height = Math.ceil(viewport.height);
          canvas.setAttribute('role', 'img');
          canvas.setAttribute('aria-label', `Dokumentseite ${number}`);
          const figure = documentElement('figure');
          const caption = documentElement('figcaption');
          caption.textContent = `Seite ${number} von ${document.numPages}`;
          figure.append(canvas, caption);
          element.append(figure);
          await page.render({ canvas, viewport }).promise;
          page.cleanup();
        }
      } catch {
        if (!cancelled)
          setError(
            'Die Dokumentseiten konnten nicht angezeigt werden. Bitte die Vorschau erneut laden.',
          );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      void task.destroy().catch(() => {});
    };
  }, [url]);
  return (
    <>
      {loading && <p role="status">Dokumentseiten werden geladen …</p>}
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      <div
        className="word-pages"
        ref={container}
        aria-label="Gerenderte Dokumentseiten"
        aria-busy={loading}
      />
    </>
  );
}

function documentElement<K extends keyof HTMLElementTagNameMap>(tag: K): HTMLElementTagNameMap[K] {
  return window.document.createElement(tag);
}
