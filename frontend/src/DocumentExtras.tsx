import type { Payload } from './documentTypes';
import { emptyText, newId, RemoveButton, TextFields } from './DocumentFields';

const weekdays = [
  ['monday', 'Montag'],
  ['tuesday', 'Dienstag'],
  ['wednesday', 'Mittwoch'],
  ['thursday', 'Donnerstag'],
  ['friday', 'Freitag'],
  ['saturday', 'Samstag'],
  ['sunday', 'Sonntag'],
];

export default function DocumentExtras({
  payload,
  edit,
  mode,
}: {
  payload: Payload;
  mode: 'extras' | 'contacts';
  edit: (change: (payload: Payload) => void) => void;
}) {
  return (
    <div className="document-extras">
      {mode === 'extras' && (
        <details className="list-panel document-section config-panel">
          <summary>Termine und Ankündigungen</summary>
          {payload.announcements.map((item, index) => (
            <details className="document-item config-panel" key={item.id}>
              <summary>{item.title.de || item.title.sl || `Termin ${index + 1}`}</summary>
              <div className="document-item-bar">
                <label className="inline-check">
                  <input
                    type="checkbox"
                    checked={item.enabled}
                    onChange={(e) =>
                      edit((p) => {
                        p.announcements[index].enabled = e.target.checked;
                      })
                    }
                  />
                  Ankündigung ausgeben
                </label>
                <RemoveButton
                  label="Ankündigung entfernen"
                  onClick={() =>
                    edit((p) => {
                      p.announcements.splice(index, 1);
                    })
                  }
                />
              </div>
              <TextFields
                label="Überschrift"
                rich
                defaultBold
                value={item.title}
                onChange={(value) =>
                  edit((p) => {
                    p.announcements[index].title = value;
                  })
                }
              />
              {item.paragraphs.map((paragraph, paragraphIndex) => (
                <div className="announcement-paragraph" key={paragraphIndex}>
                  <TextFields
                    label={`Absatz ${paragraphIndex + 1}`}
                    rich
                    multiline
                    value={paragraph}
                    onChange={(value) =>
                      edit((p) => {
                        p.announcements[index].paragraphs[paragraphIndex] = value;
                      })
                    }
                  />
                  <RemoveButton
                    label="Absatz entfernen"
                    onClick={() =>
                      edit((p) => {
                        p.announcements[index].paragraphs.splice(paragraphIndex, 1);
                      })
                    }
                  />
                </div>
              ))}
              <button
                className="button secondary"
                type="button"
                onClick={() =>
                  edit((p) => {
                    p.announcements[index].paragraphs.push(emptyText());
                  })
                }
              >
                + Absatz
              </button>
            </details>
          ))}
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              edit((p) => {
                p.announcements.push({
                  id: newId(),
                  enabled: true,
                  title: emptyText(),
                  paragraphs: [emptyText()],
                });
              })
            }
          >
            + Ankündigung hinzufügen
          </button>
        </details>
      )}
      {mode === 'extras' && (
        <details className="list-panel document-section config-panel">
          <summary>Ewiges Licht</summary>
          <label className="inline-check">
            <input
              type="checkbox"
              checked={payload.eternal_light.enabled}
              onChange={(e) =>
                edit((p) => {
                  p.eternal_light.enabled = e.target.checked;
                })
              }
            />
            Widmung ausgeben
          </label>
          <TextFields
            label="Widmung"
            rich
            value={payload.eternal_light.dedication}
            onChange={(value) =>
              edit((p) => {
                p.eternal_light.dedication = value;
              })
            }
          />
        </details>
      )}
      {mode === 'contacts' && (
        <details className="list-panel document-section config-panel">
          <summary>Kanzleistunden</summary>
          {payload.office_hours.map((hours, index) => (
            <div className="office-row" key={index}>
              <label>
                Wochentag
                <select
                  value={hours.weekday}
                  onChange={(e) =>
                    edit((p) => {
                      p.office_hours[index].weekday = e.target.value;
                    })
                  }
                >
                  {weekdays.map(([value, label]) => (
                    <option value={value} key={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Von
                <input
                  type="time"
                  required
                  value={hours.from}
                  onChange={(e) =>
                    edit((p) => {
                      p.office_hours[index].from = e.target.value;
                    })
                  }
                />
              </label>
              <label>
                Bis
                <input
                  type="time"
                  required
                  value={hours.until}
                  onChange={(e) =>
                    edit((p) => {
                      p.office_hours[index].until = e.target.value;
                    })
                  }
                />
              </label>
              <RemoveButton
                label="Kanzleistunde entfernen"
                onClick={() =>
                  edit((p) => {
                    p.office_hours.splice(index, 1);
                  })
                }
              />
            </div>
          ))}
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              edit((p) => {
                p.office_hours.push({ weekday: 'tuesday', from: '09:00', until: '12:00' });
              })
            }
          >
            + Kanzleistunde hinzufügen
          </button>
        </details>
      )}
      {mode === 'contacts' && (
        <details className="list-panel document-section config-panel">
          <summary>Kontakt</summary>
          <TextFields
            label="Pfarrname"
            value={payload.parish.name}
            onChange={(value) =>
              edit((p) => {
                p.parish.name = value;
              })
            }
          />
          {payload.contact.persons.map((person, index) => (
            <div className="contact-person" key={index}>
              <label>
                Name
                <input
                  maxLength={200}
                  value={person.name}
                  onChange={(e) =>
                    edit((p) => {
                      p.contact.persons[index].name = e.target.value;
                    })
                  }
                />
              </label>
              <label>
                Telefon
                <input
                  type="tel"
                  maxLength={100}
                  value={person.phone}
                  onChange={(e) =>
                    edit((p) => {
                      p.contact.persons[index].phone = e.target.value;
                    })
                  }
                />
              </label>
              <RemoveButton
                label="Kontaktperson entfernen"
                onClick={() =>
                  edit((p) => {
                    p.contact.persons.splice(index, 1);
                  })
                }
              />
            </div>
          ))}
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              edit((p) => {
                p.contact.persons.push({ name: '', phone: '' });
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
                value={payload.contact.email}
                onChange={(e) =>
                  edit((p) => {
                    p.contact.email = e.target.value;
                  })
                }
              />
            </label>
            <label>
              Website
              <input
                maxLength={300}
                value={payload.contact.website}
                onChange={(e) =>
                  edit((p) => {
                    p.contact.website = e.target.value;
                  })
                }
              />
            </label>
          </div>
        </details>
      )}
    </div>
  );
}
