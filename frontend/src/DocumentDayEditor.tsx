import type { DocumentDay } from './documentTypes';
import {
  emptyText,
  formatDate,
  newId,
  newNotice,
  NoticeFields,
  RemoveButton,
  TextFields,
} from './DocumentFields';

export default function DocumentDayEditor({
  day,
  onChange,
  first,
}: {
  day: DocumentDay;
  onChange: (day: DocumentDay) => void;
  first: boolean;
}) {
  const edit = (change: (copy: DocumentDay) => void) => {
    const copy = structuredClone(day);
    change(copy);
    onChange(copy);
  };
  return (
    <details className={`document-day ${day.enabled ? '' : 'day-disabled'}`} open={first}>
      <summary>
        <span>
          {new Date(day.date + 'T12:00:00').toLocaleDateString('de-AT', { weekday: 'long' })},{' '}
          {formatDate(day.date)}
        </span>
        <small>
          {day.services.length} Gottesdienste · {day.celebrations.filter((c) => c.enabled).length}{' '}
          Feiern
        </small>
      </summary>
      <div className="document-day-body">
        <label className="inline-check">
          <input
            type="checkbox"
            checked={day.enabled}
            onChange={(e) =>
              edit((d) => {
                d.enabled = e.target.checked;
              })
            }
          />
          Diesen Tag ausgeben
        </label>
        <h3>Heilige und Gedenktage</h3>
        <p className="field-help">
          Aus dem Directorium übernommen. Wahlweise Gedenktage sind zunächst ausgeschaltet. Texte
          und Auswahl gelten nur für diesen Entwurf.
        </p>
        {day.celebrations.map((celebration, index) => (
          <div className="document-item" key={celebration.id}>
            <div className="document-item-bar">
              <label className="inline-check">
                <input
                  type="checkbox"
                  checked={celebration.enabled}
                  onChange={(e) =>
                    edit((d) => {
                      d.celebrations[index].enabled = e.target.checked;
                    })
                  }
                />
                Feier ausgeben
              </label>
              <RemoveButton
                label="Feier entfernen"
                onClick={() =>
                  edit((d) => {
                    d.celebrations.splice(index, 1);
                  })
                }
              />
            </div>
            <TextFields
              label="Bezeichnung"
              value={celebration.title}
              onChange={(value) =>
                edit((d) => {
                  d.celebrations[index].title = value;
                })
              }
            />
          </div>
        ))}
        <button
          className="button secondary"
          type="button"
          onClick={() =>
            edit((d) => {
              d.celebrations.push({
                id: newId(),
                enabled: true,
                source_celebration_id: null,
                title: emptyText(),
                rank: null,
              });
            })
          }
        >
          + Feier ergänzen
        </button>
        <h3>Gottesdienste</h3>
        {day.services.map((service, index) => (
          <section key={service.id} className="service-editor">
            <div className="document-item-bar">
              <h4>Gottesdienst {index + 1}</h4>
              <RemoveButton
                label="Gottesdienst entfernen"
                onClick={() =>
                  edit((d) => {
                    d.services.splice(index, 1);
                  })
                }
              />
            </div>
            <div className="service-meta">
              <label className="inline-check">
                <input
                  type="checkbox"
                  checked={service.enabled}
                  onChange={(e) =>
                    edit((d) => {
                      d.services[index].enabled = e.target.checked;
                    })
                  }
                />
                Ausgeben
              </label>
              <label>
                Uhrzeit
                <input
                  type="time"
                  value={service.time ?? ''}
                  onChange={(e) =>
                    edit((d) => {
                      d.services[index].time = e.target.value || null;
                    })
                  }
                />
              </label>
            </div>
            <TextFields
              label="Ort"
              value={service.location}
              onChange={(value) =>
                edit((d) => {
                  d.services[index].location = value;
                })
              }
            />
            <TextFields
              label="Gottesdienst"
              value={service.title}
              onChange={(value) =>
                edit((d) => {
                  d.services[index].title = value;
                })
              }
            />
            <h4>Messintentionen</h4>
            {service.intentions.map((intention, intentionIndex) => (
              <div className="document-item" key={intention.id}>
                <div className="document-item-bar">
                  <label className="inline-check">
                    <input
                      type="checkbox"
                      checked={intention.enabled}
                      onChange={(e) =>
                        edit((d) => {
                          d.services[index].intentions[intentionIndex].enabled = e.target.checked;
                        })
                      }
                    />
                    Intention ausgeben
                  </label>
                  <RemoveButton
                    label="Intention entfernen"
                    onClick={() =>
                      edit((d) => {
                        d.services[index].intentions.splice(intentionIndex, 1);
                      })
                    }
                  />
                </div>
                <TextFields
                  label="Intention"
                  multiline
                  value={intention.text}
                  onChange={(value) =>
                    edit((d) => {
                      d.services[index].intentions[intentionIndex].text = value;
                    })
                  }
                />
                <div className="bilingual-fields">
                  <label>
                    Zeichen
                    <input
                      maxLength={10}
                      value={intention.symbol}
                      onChange={(e) =>
                        edit((d) => {
                          d.services[index].intentions[intentionIndex].symbol = e.target.value;
                        })
                      }
                    />
                  </label>
                  <label>
                    Referenz (optional)
                    <input
                      maxLength={100}
                      placeholder="z. B. 614/25"
                      value={intention.reference ?? ''}
                      onChange={(e) =>
                        edit((d) => {
                          d.services[index].intentions[intentionIndex].reference =
                            e.target.value || null;
                        })
                      }
                    />
                  </label>
                </div>
              </div>
            ))}
            <button
              className="button secondary"
              type="button"
              onClick={() =>
                edit((d) => {
                  d.services[index].intentions.push({
                    ...newNotice(),
                    symbol: '+',
                    reference: null,
                  });
                })
              }
            >
              + Intention hinzufügen
            </button>
            <h4>Hinweise zum Gottesdienst</h4>
            <NoticeFields
              notices={service.notices}
              onChange={(value) =>
                edit((d) => {
                  d.services[index].notices = value;
                })
              }
            />
          </section>
        ))}
        <button
          type="button"
          className="button secondary"
          onClick={() =>
            edit((d) => {
              d.services.push({
                id: newId(),
                enabled: true,
                time: null,
                location: emptyText(),
                title: { de: 'Heilige Messe', sl: 'Sveta maša' },
                intentions: [],
                notices: [],
              });
            })
          }
        >
          + Gottesdienst hinzufügen
        </button>
        <h3>Hinweise zum Tag</h3>
        <NoticeFields notices={day.notices} onChange={(notices) => onChange({ ...day, notices })} />
      </div>
    </details>
  );
}
