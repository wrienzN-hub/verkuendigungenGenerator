import { useEffect, useRef, useState } from 'react';
import { X, BookOpen, Save, Info } from 'lucide-react';
import { updateSaint } from './api';
import { formatDate, observances, ranks } from './labels';
import type { Saint, SaintPatch } from './types';

export default function SaintEditor({
  saint,
  onClose,
  onSaved,
}: {
  saint: Saint;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial: SaintPatch = {
    name: saint.name,
    name_sl: saint.name_sl,
    rank_code: saint.rank_code,
    observance_status: saint.observance_status,
    disabled: saint.disabled,
    applicability_note: saint.applicability_note,
  };
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const close = () => {
    if (
      !busy &&
      (JSON.stringify(initial) === JSON.stringify(form) ||
        window.confirm('Ungespeicherte Änderungen verwerfen?'))
    )
      onClose();
  };
  const field = <K extends keyof SaintPatch>(key: K, value: SaintPatch[K]) =>
    setForm((f) => ({ ...f, [key]: value }));
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await updateSaint(saint.id, {
        ...form,
        name: form.name.trim(),
        name_sl: form.name_sl?.trim() || null,
      });
      onSaved();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };
  return (
    <dialog
      ref={dialog}
      className="editor-dialog"
      aria-labelledby="editor-title"
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === dialog.current) close();
      }}
    >
      <form onSubmit={save}>
        <div className="dialog-header">
          <div>
            <span className="eyebrow">EINTRAG BEARBEITEN</span>
            <h2 id="editor-title">{saint.name}</h2>
            <p>
              {formatDate(saint.celebration_date)} <span>·</span> Kirchenjahr{' '}
              {saint.liturgical_year}
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={close}
            disabled={busy}
            aria-label="Schließen"
          >
            <X size={20} />
          </button>
        </div>
        <div className="dialog-body">
          <fieldset disabled={busy}>
            <legend className="sr-only">Angaben zur Feier</legend>
            <div className="form-grid">
              <label className="full">
                Name · Deutsch
                <input
                  autoFocus
                  required
                  maxLength={500}
                  value={form.name}
                  onChange={(e) => field('name', e.target.value)}
                />
              </label>
              <label className="full">
                Name · Slowenisch <span className="optional">optional</span>
                <input
                  maxLength={500}
                  value={form.name_sl || ''}
                  onChange={(e) => field('name_sl', e.target.value)}
                  placeholder="Slowenische Bezeichnung ergänzen"
                />
              </label>
              <label>
                Liturgischer Rang
                <select
                  aria-label="Liturgischer Rang"
                  value={form.rank_code || ''}
                  onChange={(e) => field('rank_code', e.target.value || null)}
                >
                  <option value="">Nicht angegeben</option>
                  {Object.entries(ranks).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Liturgische Verfügbarkeit
                <select
                  aria-label="Liturgische Verfügbarkeit"
                  value={form.observance_status}
                  onChange={(e) => field('observance_status', e.target.value)}
                >
                  {Object.entries(observances).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="full">
                Örtliche Bedingungen <span className="optional">optional</span>
                <textarea
                  maxLength={5000}
                  rows={2}
                  value={form.applicability_note || ''}
                  onChange={(e) => field('applicability_note', e.target.value || null)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={!form.disabled}
                  onChange={(e) => field('disabled', !e.target.checked)}
                />
                <span>Für Verkündigungen aktiviert</span>
              </label>
            </div>
          </fieldset>
          <p className="info-note">
            <Info size={16} />
            Entfallene und örtlich bedingte Feiern werden durch Aktivieren allein nicht für die
            Wochenauswahl freigegeben.
          </p>
          <details className="source-details">
            <summary>
              <BookOpen size={16} />
              Originaltext & Quelle
            </summary>
            <p>{saint.source_text}</p>
            <small>{saint.source_reference}</small>
            <p className="source-note">
              Der Originaltext und das Datum bleiben zur Nachvollziehbarkeit erhalten.
            </p>
          </details>
          {error && (
            <div role="alert" className="error-box">
              {error}
            </div>
          )}
        </div>
        <div className="dialog-footer">
          <button type="button" className="button secondary" disabled={busy} onClick={close}>
            Abbrechen
          </button>
          <button type="submit" className="button primary" disabled={busy || !form.name.trim()}>
            <Save size={16} />
            {busy ? 'Wird gespeichert …' : 'Änderungen speichern'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
