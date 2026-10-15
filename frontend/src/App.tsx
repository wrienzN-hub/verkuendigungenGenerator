import { useEffect, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  Church,
  ChevronRight,
  Sprout,
  FileText,
} from 'lucide-react';
import SaintsPage from './SaintsPage';
import TemplatesPage from './TemplatesPage';
import DocumentsPage from './DocumentsPage';
import SettingsPage from './SettingsPage';
import DocumentArchivePage from './DocumentArchivePage';

export default function App() {
  const [route, setRoute] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash);
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const isSaints = route === '#/heilige';
  const isTemplates = route === '#/vorlagen';
  const isDocuments = route === '#/erstellen' || route.startsWith('#/erstellen/');
  const isArchive = route === '#/verkuendigungen';
  const isSettings = route === '#/einstellungen';
  return (
    <>
      <a className="skip-link" href="#main">
        Zum Inhalt
      </a>
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#/" aria-label="Verkündigungen Startseite">
            <span className="brand-mark">
              <Church size={25} />
            </span>
            <span>Verkündigungen</span>
          </a>
          <nav aria-label="Hauptnavigation">
            <a
              href="#/"
              className={
                !isSaints && !isTemplates && !isDocuments && !isSettings && !isArchive
                  ? 'active'
                  : ''
              }
              aria-current={
                !isSaints && !isTemplates && !isDocuments && !isSettings && !isArchive
                  ? 'page'
                  : undefined
              }
            >
              <CalendarDays size={17} />
              Übersicht
            </a>
            <a
              href="#/erstellen"
              className={isDocuments ? 'active' : ''}
              aria-current={isDocuments ? 'page' : undefined}
            >
              <FileText size={17} />
              Erstellen
            </a>
            <a
              href="#/heilige"
              className={isSaints ? 'active' : ''}
              aria-current={isSaints ? 'page' : undefined}
            >
              <BookOpen size={17} />
              Heilige
            </a>
            <a
              href="#/vorlagen"
              className={isTemplates ? 'active' : ''}
              aria-current={isTemplates ? 'page' : undefined}
            >
              <FileText size={17} />
              Vorlagen
            </a>
            <a
              href="#/einstellungen"
              className={isSettings ? 'active' : ''}
              aria-current={isSettings ? 'page' : undefined}
            >
              Einstellungen
            </a>
            <a
              href="#/verkuendigungen"
              className={isArchive ? 'active' : ''}
              aria-current={isArchive ? 'page' : undefined}
            >
              Verkündigungen
            </a>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="page-shell">
        <div className="breadcrumb">
          Pfarrverwaltung <ChevronRight size={13} />
          <span>
            {isSaints
              ? 'Heilige & Gedenktage'
              : isTemplates
              ? 'Word-Vorlagen'
              : isDocuments
              ? 'Verkündigung erstellen'
              : isSettings
              ? 'Default-Einstellungen'
              : isArchive
              ? 'Verkündigungen'
              : 'Übersicht'}
          </span>
        </div>
        {isSaints ? (
          <SaintsPage />
        ) : isArchive ? (
          <DocumentArchivePage />
        ) : isSettings ? (
          <SettingsPage />
        ) : isDocuments ? (
          <DocumentsPage documentId={Number(route.split('/')[2]) || undefined} />
        ) : isTemplates ? (
          <TemplatesPage />
        ) : (
          <>
            <section className="home-hero">
              <div className="eyebrow">
                <Sprout size={15} />
                GUT VORBEREITET DURCH DAS KIRCHENJAHR
              </div>
              <h1>
                Raum für das,
                <br />
                was die Gemeinde verbindet.
              </h1>
              <p>
                Verkündigungen vorbereiten und den liturgischen Kalender im Blick behalten. Alles an
                einem Ort.
              </p>
              <a className="button primary" href="#/erstellen">
                Verkündigung erstellen <ArrowRight size={17} />
              </a>
              <div className="hero-ornament" aria-hidden="true">
                <Church size={170} strokeWidth={0.7} />
              </div>
            </section>
            <div className="home-grid">
              <a className="home-card linked-card" href="#/erstellen">
                <span className="icon-box">
                  <CalendarDays size={22} />
                </span>
                <span className="muted-label">ABKÜNDIGUNGEN ERSTELLEN</span>
                <h2>Eine Woche. Eine Verkündigung.</h2>
                <p>
                  Eine liturgische Woche auswählen, Gottesdienste und Intentionen ergänzen und die
                  Verkündigung als bearbeitbare Word-Datei erstellen.
                </p>
                <span className="text-link">
                  Zur Erstellung <ArrowRight size={16} />
                </span>
              </a>
              <a className="home-card linked-card" href="#/heilige">
                <span className="icon-box">
                  <BookOpen size={22} />
                </span>
                <span className="muted-label">KALENDER VERWALTEN</span>
                <h2>Heilige & Gedenktage</h2>
                <p>
                  Einträge aus dem Directorium durchsuchen, Bezeichnungen bearbeiten und festlegen,
                  was für deine Verkündigungen verfügbar ist.
                </p>
                <span className="text-link">
                  Zur Verwaltung <ArrowRight size={16} />
                </span>
              </a>
            </div>
          </>
        )}
      </main>
      <footer className="site-footer">
        <span>Verkündigungen · Pfarrverwaltung</span>
        <span>Mit Sorgfalt durch das Kirchenjahr.</span>
      </footer>
    </>
  );
}
