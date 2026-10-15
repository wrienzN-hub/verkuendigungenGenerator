import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
import { request } from './api';
import { emptyText, newId, RemoveButton, TextFields } from './DocumentFields';
import type { DocumentOptions, Payload, Service } from './documentTypes';

type Defaults = {
  services: (Service & { weekday: number })[];
  office_hours: Payload['office_hours'];
  contact: Payload['contact'];
};
const empty = (): Defaults => ({
  services: [],
  office_hours: [],
  contact: { persons: [], email: '', website: '' },
});
const weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];

export default function SettingsPage() {
  const [parishes, setParishes] = useState<string[]>([]);
  const [parish, setParish] = useState('');
  const [settings, setSettings] = useState<Defaults>(empty);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadedFor, setLoadedFor] = useState('');
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => {
    request<DocumentOptions>('/api/v1/documents/options')
      .then((o) => {
        const names = [...new Set(o.templates.map((t) => t.parish_name))];
        setParishes(names);
        setParish(names[0] ?? '');
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);
  useEffect(() => {
    if (!parish) return;
    const controller = new AbortController();
    setLoading(true);
    setLoadedFor('');
    setSettings(empty());
    setError('');
    setMessage('');
    request<Defaults>(`/api/v1/settings?parish=${encodeURIComponent(parish)}`, {
      signal: controller.signal,
    })
      .then((result) => {
        setSettings(result);
        setLoadedFor(parish);
        setDirty(false);
      })
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [parish]);
  useEffect(() => {
    const listener = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener('beforeunload', listener);
    return () => window.removeEventListener('beforeunload', listener);
  }, [dirty]);
  const edit = (change: (copy: Defaults) => void) => {
    setSettings((s) => {
      const copy = structuredClone(s);
      change(copy);
      return copy;
    });
    setDirty(true);
    setMessage('');
  };
  async function save() {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await request(`/api/v1/settings?parish=${encodeURIComponent(parish)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      setDirty(false);
      setMessage(`Vorgaben für ${parish} gespeichert. Neue Wochen übernehmen diese Einstellungen.`);
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
          <div className="eyebrow">WIEDERKEHRENDES VORBEREITEN</div>
          <h1>Default-Einstellungen</h1>
          <p>Gottesdienstzeiten und Kontaktdaten pro Pfarre einmal hinterlegen.</p>
        </div>
      </section>
      <section className="list-panel document-section">
        <label>
          Pfarre
          <select
            value={parish}
            disabled={busy}
            onChange={(e) => {
              if (
                !dirty ||
                window.confirm('Ungespeicherte Einstellungen verwerfen und die Pfarre wechseln?')
              )
                setParish(e.target.value);
            }}
          >
            {parishes.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </label>
        <p className="field-help">
          Beim Laden einer neuen Woche werden alle aktiven Vorgaben für die jeweiligen Wochentage
          übernommen – auch für beide Sonntage. Gespeicherte Entwürfe bleiben unverändert.
        </p>
      </section>
      {loading ? (
        <p role="status">Einstellungen werden geladen …</p>
      ) : (
        <fieldset className="creator-fieldset" disabled={busy || loadedFor !== parish}>
          <section className="list-panel document-section">
            <h2>Regelmäßige Gottesdienste</h2>
            {settings.services.map((service, index) => (
              <section className="service-editor" key={service.id}>
                <div className="document-item-bar">
                  <label className="inline-check">
                    <input
                      type="checkbox"
                      checked={service.enabled}
                      onChange={(e) =>
                        edit((s) => {
                          s.services[index].enabled = e.target.checked;
                        })
                      }
                    />
                    Automatisch übernehmen
                  </label>
                  <RemoveButton
                    label="Vorgabe entfernen"
                    onClick={() =>
                      edit((s) => {
                        s.services.splice(index, 1);
                      })
                    }
                  />
                </div>
                <div className="bilingual-fields">
                  <label>
                    Wochentag
                    <select
                      value={service.weekday}
                      onChange={(e) =>
                        edit((s) => {
                          s.services[index].weekday = Number(e.target.value);
                        })
                      }
                    >
                      {weekdays.map((label, value) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Uhrzeit
                    <input
                      type="time"
                      value={service.time ?? ''}
                      onChange={(e) =>
                        edit((s) => {
                          s.services[index].time = e.target.value || null;
                        })
                      }
                    />
                  </label>
                </div>
                <TextFields
                  label="Gottesdienst"
                  value={service.title}
                  onChange={(value) =>
                    edit((s) => {
                      s.services[index].title = value;
                    })
                  }
                />
                <TextFields
                  label="Ort"
                  value={service.location}
                  onChange={(value) =>
                    edit((s) => {
                      s.services[index].location = value;
                    })
                  }
                />
              </section>
            ))}
            <button
              className="button secondary"
              type="button"
              onClick={() =>
                edit((s) => {
                  s.services.push({
                    id: newId(),
                    weekday: 6,
                    enabled: true,
                    time: '09:15',
                    title: { de: 'Heilige Messe', sl: 'Sveta maša' },
                    location: emptyText(),
                    intentions: [],
                    notices: [],
                  });
                })
              }
            >
              + Gottesdienst-Vorgabe hinzufügen
            </button>
          </section>
          <section className="list-panel document-section">
            <h2>Kanzleistunden</h2>
            {settings.office_hours.map((hours, index) => (
              <div className="office-row" key={index}>
                <label>
                  Wochentag
                  <select
                    value={hours.weekday}
                    onChange={(e) =>
                      edit((s) => {
                        s.office_hours[index].weekday = e.target.value;
                      })
                    }
                  >
                    {[
                      'monday',
                      'tuesday',
                      'wednesday',
                      'thursday',
                      'friday',
                      'saturday',
                      'sunday',
                    ].map((value, i) => (
                      <option key={value} value={value}>
                        {weekdays[i]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Von
                  <input
                    type="time"
                    value={hours.from}
                    onChange={(e) =>
                      edit((s) => {
                        s.office_hours[index].from = e.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Bis
                  <input
                    type="time"
                    value={hours.until}
                    onChange={(e) =>
                      edit((s) => {
                        s.office_hours[index].until = e.target.value;
                      })
                    }
                  />
                </label>
                <RemoveButton
                  label="Kanzleistunde entfernen"
                  onClick={() =>
                    edit((s) => {
                      s.office_hours.splice(index, 1);
                    })
                  }
                />
              </div>
            ))}
            <button
              className="button secondary"
              type="button"
              onClick={() =>
                edit((s) => {
                  s.office_hours.push({ weekday: 'tuesday', from: '09:00', until: '12:00' });
                })
              }
            >
              + Kanzleistunde hinzufügen
            </button>
          </section>
          <section className="list-panel document-section">
            <h2>Kontakt</h2>
            {settings.contact.persons.map((person, index) => (
              <div className="contact-person" key={index}>
                <label>
                  Name
                  <input
                    maxLength={200}
                    value={person.name}
                    onChange={(e) =>
                      edit((s) => {
                        s.contact.persons[index].name = e.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Telefon
                  <input
                    maxLength={100}
                    value={person.phone}
                    onChange={(e) =>
                      edit((s) => {
                        s.contact.persons[index].phone = e.target.value;
                      })
                    }
                  />
                </label>
                <RemoveButton
                  label="Kontaktperson entfernen"
                  onClick={() =>
                    edit((s) => {
                      s.contact.persons.splice(index, 1);
                    })
                  }
                />
              </div>
            ))}
            <button
              className="button secondary"
              type="button"
              onClick={() =>
                edit((s) => {
                  s.contact.persons.push({ name: '', phone: '' });
                })
              }
            >
              + Kontaktperson hinzufügen
            </button>
            <div className="bilingual-fields">
              <label>
                E-Mail
                <input
                  maxLength={200}
                  value={settings.contact.email}
                  onChange={(e) =>
                    edit((s) => {
                      s.contact.email = e.target.value;
                    })
                  }
                />
              </label>
              <label>
                Website
                <input
                  maxLength={300}
                  value={settings.contact.website}
                  onChange={(e) =>
                    edit((s) => {
                      s.contact.website = e.target.value;
                    })
                  }
                />
              </label>
            </div>
          </section>
          <button
            type="button"
            className="button primary"
            onClick={() => void save()}
            disabled={!parish}
          >
            <Save size={16} />
            {busy ? 'Wird gespeichert …' : 'Einstellungen speichern'}
          </button>
          <p className="field-help">
            {dirty
              ? 'Ungespeicherte Änderungen'
              : 'Die Werte können später in jeder Verkündigung individuell angepasst werden.'}
          </p>
        </fieldset>
      )}
      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="success-box" role="status">
          {message}
        </div>
      )}
    </>
  );
}
