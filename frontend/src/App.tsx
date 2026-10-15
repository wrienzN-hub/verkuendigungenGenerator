import { useEffect, useState } from 'react';
import { ArrowRight, BookOpen, CalendarDays, Church, ChevronRight, Sprout } from 'lucide-react';
import SaintsPage from './SaintsPage';

export default function App() {
  const [route, setRoute] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash);
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const isSaints = route === '#/heilige';
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
            <span>
              Verkündigungen<small>PFARRE EBERNDORF</small>
            </span>
          </a>
          <nav aria-label="Hauptnavigation">
            <a
              href="#/"
              className={!isSaints ? 'active' : ''}
              aria-current={!isSaints ? 'page' : undefined}
            >
              <CalendarDays size={17} />
              Übersicht
            </a>
            <a
              href="#/heilige"
              className={isSaints ? 'active' : ''}
              aria-current={isSaints ? 'page' : undefined}
            >
              <BookOpen size={17} />
              Heilige
            </a>
          </nav>
          <span className="diocese">
            <span className="online-dot" />
            Diözese Gurk
          </span>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="page-shell">
        <div className="breadcrumb">
          Pfarrverwaltung <ChevronRight size={13} />
          <span>{isSaints ? 'Heilige & Gedenktage' : 'Übersicht'}</span>
        </div>
        {isSaints ? (
          <SaintsPage />
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
              <a className="button primary" href="#/heilige">
                Heilige verwalten <ArrowRight size={17} />
              </a>
              <div className="hero-ornament" aria-hidden="true">
                <Church size={170} strokeWidth={0.7} />
              </div>
            </section>
            <div className="home-grid">
              <section className="home-card">
                <span className="icon-box">
                  <CalendarDays size={22} />
                </span>
                <span className="muted-label">IN VORBEREITUNG</span>
                <h2>Eine Woche. Eine Verkündigung.</h2>
                <p>
                  Hier wirst du eine liturgische Woche auswählen, Gottesdienste ergänzen und deine
                  Verkündigung als PDF erstellen können.
                </p>
                <span className="coming-label">Die Wochenauswahl folgt im nächsten Schritt.</span>
              </section>
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
        <span>Verkündigungen · Pfarre Eberndorf</span>
        <span>Mit Sorgfalt durch das Kirchenjahr.</span>
      </footer>
    </>
  );
}
