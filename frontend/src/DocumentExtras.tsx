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
}: {
  payload: Payload;
  edit: (change: (payload: Payload) => void) => void;
}) {
  return (
    <div className="document-extras">
      <section className="list-panel document-section">
        <h2>Termine und Ankündigungen</h2>
        {payload.announcements.map((item, index) => (
          <div className="document-item" key={item.id}>
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
          </div>
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
      </section>
      <section className="list-panel document-section">
        <h2>Ewiges Licht</h2>
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
          value={payload.eternal_light.dedication}
          onChange={(value) =>
            edit((p) => {
              p.eternal_light.dedication = value;
            })
          }
        />
      </section>
      <section className="list-panel document-section">
        <h2>Kanzleistunden</h2>
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
      </section>
      <section className="list-panel document-section">
        <h2>Kontakt</h2>
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
      </section>
    </div>
  );
}
