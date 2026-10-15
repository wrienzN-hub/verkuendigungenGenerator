import { useEffect, useState } from 'react';
import {
  BookOpen,
  Check,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  Filter,
  Pencil,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { request, updateSaint } from './api';
import { formatDate, months, observances, ranks } from './labels';
import type { FilterOptions, Saint, SaintPage, LiturgicalWeek } from './types';
import SaintEditor from './SaintEditor';
import DirectoriumUpload from './DirectoriumUpload';

const emptyFilters = {
  search: '',
  year: '',
  month: '',
  rank: '',
  disabled: '',
  observance_status: '',
  season: '',
  liturgical_week: '',
};
export default function SaintsPage() {
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [data, setData] = useState<SaintPage | null>(null);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [editing, setEditing] = useState<Saint | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [weeks, setWeeks] = useState<LiturgicalWeek[]>([]);
  const [weeksLoading, setWeeksLoading] = useState(false);
  const [weeksError, setWeeksError] = useState('');
  const filter = (key: keyof typeof filters, value: string) => {
    setFilters((f) => ({
      ...f,
      [key]: value,
      ...(key === 'year' ? { season: '', liturgical_week: '' } : {}),
      ...(key === 'season' ? { liturgical_week: '' } : {}),
      ...(key === 'liturgical_week' && value ? { month: '' } : {}),
    }));
    setPage(0);
  };
  useEffect(() => {
    const controller = new AbortController();
    setWeeks([]);
    setWeeksError('');
    if (!filters.year) {
      setWeeksLoading(false);
      return;
    }
    setWeeksLoading(true);
    request<LiturgicalWeek[]>(`/api/v1/saints/weeks?year=${encodeURIComponent(filters.year)}`, {
      signal: controller.signal,
    })
      .then((value) => {
        setWeeks(value);
        setWeeksLoading(false);
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setWeeksLoading(false);
          setWeeksError('Die liturgischen Wochen konnten nicht geladen werden.');
        }
      });
    return () => controller.abort();
  }, [filters.year, refresh]);
  useEffect(() => {
    const controller = new AbortController();
    request<FilterOptions>('/api/v1/saints/filters', { signal: controller.signal })
      .then(setOptions)
      .catch((e) => {
        if (e.name !== 'AbortError')
          setError('Die API ist nicht erreichbar. Bitte prüfen, ob der Backend-Server läuft.');
      });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ limit: String(size), offset: String(page * size) });
      Object.entries(filters).forEach(([key, value]) => {
        if (value && key !== 'season') params.set(key, value);
      });
      request<SaintPage>(`/api/v1/saints/page?${params}`, { signal: controller.signal })
        .then((result) => {
          if (result.total > 0 && page * size >= result.total) {
            setPage(Math.ceil(result.total / size) - 1);
            return;
          }
          if (result.total === 0 && page > 0) {
            setPage(0);
            return;
          }
          setData(result);
          setLoading(false);
        })
        .catch((e) => {
          if (e.name !== 'AbortError') {
            setError(
              'Die Einträge konnten nicht geladen werden. Bitte prüfe die Verbindung zur API.',
            );
            setLoading(false);
          }
        });
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [filters, page, size, refresh]);
  const toggle = async (saint: Saint) => {
    setBusyId(saint.id);
    setError('');
    setNotice('');
    try {
      await updateSaint(saint.id, { disabled: !saint.disabled });
      setNotice(`${saint.name} wurde ${saint.disabled ? 'aktiviert' : 'deaktiviert'}.`);
      setRefresh((n) => n + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };
  const pages = Math.max(1, Math.ceil((data?.total || 0) / size));
  const hasFilters = Object.values(filters).some(Boolean);
  const seasons = [...new Map(weeks.map((w) => [w.season, w.season_label])).entries()];
  const selectedWeek = weeks.find((w) => w.id === filters.liturgical_week);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">LITURGISCHER KALENDER</div>
          <h1>Heilige & Gedenktage</h1>
          <p>Den Kalender pflegen. Die Verkündigung vorbereiten.</p>
        </div>
        <button className="button primary" onClick={() => setUploading(true)}>
          <BookOpen size={16} />
          Directorium hochladen
        </button>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-icon">
            <BookOpen size={20} />
          </span>
          <div>
            <strong>{options?.total ?? '—'}</strong>
            <span>Einträge im Kalender</span>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon green">
            <CircleCheck size={20} />
          </span>
          <div>
            <strong>{options?.active ?? '—'}</strong>
            <span>Für Verkündigungen aktiviert</span>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon amber">
            <CalendarDays size={20} />
          </span>
          <div>
            <strong>{options?.years.length ?? '—'}</strong>
            <span>Importierte Kirchenjahre</span>
          </div>
        </div>
      </div>
      <section className="list-panel" aria-label="Heilige verwalten">
        <div className="panel-title">
          <div>
            <h2>
              Alle Einträge <span className="count-badge">{data?.total ?? '…'}</span>
            </h2>
            <p>Heilige, Sonntage und Feste aus dem Directorium.</p>
          </div>
          <button
            className={`button secondary compact ${advanced ? 'selected' : ''}`}
            onClick={() => setAdvanced((v) => !v)}
            aria-expanded={advanced}
          >
            <SlidersHorizontal size={15} />
            Weitere Filter
            {filters.observance_status && <span className="filter-dot" />}
          </button>
        </div>
        <div className="filters">
          <label className="search-field">
            <span className="sr-only">Heilige durchsuchen</span>
            <Search size={18} />
            <input
              type="search"
              placeholder="Nach Namen suchen …"
              maxLength={200}
              value={filters.search}
              onChange={(e) => filter('search', e.target.value)}
            />
          </label>
          <label>
            Kirchenjahr
            <select
              aria-label="Kirchenjahr"
              value={filters.year}
              onChange={(e) => filter('year', e.target.value)}
            >
              <option value="">Alle Kirchenjahre</option>
              {options?.years.map((y) => <option key={y}>{y}</option>)}
            </select>
          </label>
          <label>
            Monat
            <select
              aria-label="Monat"
              value={filters.month}
              onChange={(e) => filter('month', e.target.value)}
            >
              <option value="">Alle Monate</option>
              {months.map((m, i) => (
                <option key={m} value={i + 1}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label>
            Rang
            <select
              aria-label="Rang"
              value={filters.rank}
              onChange={(e) => filter('rank', e.target.value)}
            >
              <option value="">Alle Ränge</option>
              {Object.entries(ranks).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Aktivierung
            <select
              aria-label="Aktivierung"
              value={filters.disabled}
              onChange={(e) => filter('disabled', e.target.value)}
            >
              <option value="">Alle Einträge</option>
              <option value="false">Aktiviert</option>
              <option value="true">Deaktiviert</option>
            </select>
          </label>
        </div>
        <div className="liturgical-filters">
          <CalendarDays size={18} />
          <label>
            Liturgische Zeit
            <select
              aria-label="Liturgische Zeit"
              value={filters.season}
              disabled={!filters.year || weeksLoading || !!weeksError}
              onChange={(e) => filter('season', e.target.value)}
            >
              <option value="">
                {!filters.year
                  ? 'Zuerst Kirchenjahr wählen'
                  : weeksLoading
                  ? 'Wochen werden geladen …'
                  : 'Alle liturgischen Zeiten'}
              </option>
              {seasons.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Liturgische Woche
            <select
              aria-label="Liturgische Woche"
              value={filters.liturgical_week}
              disabled={!filters.season || weeksLoading}
              onChange={(e) => filter('liturgical_week', e.target.value)}
            >
              <option value="">Alle Wochen</option>
              {weeks
                .filter((w) => w.season === filters.season)
                .map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.label} · {formatDate(w.start)} – {formatDate(w.end)}
                  </option>
                ))}
            </select>
          </label>
          <span className="week-range">
            {selectedWeek
              ? `${formatDate(selectedWeek.start)} bis ${formatDate(
                  selectedWeek.end,
                )} · Sonntag bis Sonntag`
              : weeksError || 'Wochen laut importiertem Directorium'}
          </span>
        </div>
        {advanced && (
          <div className="advanced-filters">
            <Filter size={16} />
            <label>
              Liturgische Verfügbarkeit
              <select
                aria-label="Liturgische Verfügbarkeit"
                value={filters.observance_status}
                onChange={(e) => filter('observance_status', e.target.value)}
              >
                <option value="">Alle Verfügbarkeiten</option>
                {Object.entries(observances).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {hasFilters && (
          <div className="filter-summary">
            <span>Filter angewendet</span>
            <button
              className="text-button"
              onClick={() => {
                setFilters(emptyFilters);
                setPage(0);
              }}
            >
              <X size={13} />
              Zurücksetzen
            </button>
          </div>
        )}
        {notice && (
          <div className="success-box" role="status">
            <Check size={16} />
            {notice}
            <button
              className="icon-button"
              onClick={() => setNotice('')}
              aria-label="Meldung schließen"
            >
              <X size={15} />
            </button>
          </div>
        )}
        {error && (
          <div className="error-box" role="alert">
            {error}
            <button className="text-button" onClick={() => setRefresh((n) => n + 1)}>
              <RotateCcw size={14} />
              Erneut versuchen
            </button>
          </div>
        )}
        <div className="table-scroll" aria-busy={loading}>
          <table>
            <thead>
              <tr>
                <th>Datum</th>
                <th>Name / Bezeichnung</th>
                <th>Liturgischer Rang</th>
                <th>Verfügbarkeit</th>
                <th>Aktiviert</th>
                <th>
                  <span className="sr-only">Bearbeiten</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }, (_, i) => (
                    <tr key={i} className="skeleton-row">
                      <td>
                        <span />
                      </td>
                      <td>
                        <span />
                      </td>
                      <td>
                        <span />
                      </td>
                      <td>
                        <span />
                      </td>
                      <td>
                        <span />
                      </td>
                      <td />
                    </tr>
                  ))
                : !error &&
                  data?.items.map((s) => (
                    <tr key={s.id} className={s.disabled ? 'disabled-row' : ''}>
                      <td className="date-cell">
                        {formatDate(s.celebration_date)}
                        <small>{s.liturgical_year}</small>
                      </td>
                      <td className="name-cell">
                        <strong>{s.name}</strong>
                        {s.name_sl && <span>{s.name_sl}</span>}
                      </td>
                      <td>
                        <span className={`rank-badge rank-${s.rank_code || 'none'}`}>
                          {s.rank_code && ['H', 'F', 'G', 'g'].includes(s.rank_code) ? (
                            <b>{s.rank_code}</b>
                          ) : null}
                          {s.rank_code ? ranks[s.rank_code] || s.rank_code : 'Nicht angegeben'}
                        </span>
                      </td>
                      <td>
                        <span className={`observance ${s.observance_status}`}>
                          <i />
                          {observances[s.observance_status]}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={!s.disabled}
                          aria-label={`${s.name} ${s.disabled ? 'aktivieren' : 'deaktivieren'}`}
                          className="toggle"
                          disabled={busyId !== null}
                          onClick={() => toggle(s)}
                        >
                          <span />
                        </button>
                      </td>
                      <td>
                        <button
                          className="edit-button"
                          onClick={() => setEditing(s)}
                          aria-label={`${s.name} bearbeiten`}
                          disabled={busyId !== null}
                        >
                          <Pencil size={15} />
                          <span>Bearbeiten</span>
                        </button>
                      </td>
                    </tr>
                  ))}
              {!loading && !error && data?.total === 0 && (
                <tr>
                  <td colSpan={6}>
                    <div className="empty-state">
                      <Search size={30} />
                      <h3>Keine passenden Einträge</h3>
                      <p>Versuche einen anderen Suchbegriff oder passe die Filter an.</p>
                      <button
                        className="button secondary"
                        onClick={() => {
                          setFilters(emptyFilters);
                          setPage(0);
                        }}
                      >
                        Filter zurücksetzen
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <div className="page-info" role="status">
            {loading
              ? 'Einträge werden geladen …'
              : data?.total
              ? `${page * size + 1}–${Math.min((page + 1) * size, data.total)} von ${
                  data.total
                } Einträgen`
              : '0 Einträge'}
            <label>
              <span className="sr-only">Einträge pro Seite</span>
              <select
                value={size}
                onChange={(e) => {
                  setSize(Number(e.target.value));
                  setPage(0);
                }}
              >
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n} pro Seite
                  </option>
                ))}
              </select>
            </label>
          </div>
          <nav aria-label="Seitennavigation">
            <button
              className="page-button"
              disabled={page === 0 || loading}
              onClick={() => setPage((p) => p - 1)}
              aria-label="Vorherige Seite"
            >
              <ChevronLeft size={17} />
            </button>
            {Array.from({ length: pages }, (_, i) => i)
              .filter((i) => i === 0 || i === pages - 1 || Math.abs(i - page) <= 1)
              .map((n, index, all) => (
                <span className="page-number" key={n}>
                  {index > 0 && n - all[index - 1] > 1 && <span className="ellipsis">…</span>}
                  <button
                    className={`page-button ${page === n ? 'current' : ''}`}
                    disabled={loading}
                    aria-label={`Seite ${n + 1}`}
                    aria-current={page === n ? 'page' : undefined}
                    onClick={() => setPage(n)}
                  >
                    {n + 1}
                  </button>
                </span>
              ))}
            <button
              className="page-button"
              disabled={page >= pages - 1 || loading}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Nächste Seite"
            >
              <ChevronRight size={17} />
            </button>
          </nav>
        </div>
      </section>
      <p className="bottom-note">
        <BookOpen size={14} />
        Änderungen gelten für den jeweiligen Eintrag im Kirchenjahr. Der Originaltext bleibt
        erhalten.
      </p>
      {uploading && (
        <DirectoriumUpload
          onClose={() => setUploading(false)}
          onImported={(year) => {
            setUploading(false);
            setFilters({ ...emptyFilters, year });
            setPage(0);
            setRefresh((n) => n + 1);
            setNotice(`Das Directorium für ${year} ist verfügbar.`);
          }}
        />
      )}
      {editing && (
        <SaintEditor
          key={editing.id}
          saint={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setNotice('Die Änderungen wurden gespeichert.');
            setRefresh((n) => n + 1);
          }}
        />
      )}
    </>
  );
}
