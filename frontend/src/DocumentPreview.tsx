import { formatDate, showText } from './DocumentFields';
import type { Payload } from './documentTypes';

export default function DocumentPreview({ payload }: { payload: Payload }) {
  return (
    <section className="list-panel document-section">
      <h2>Inhaltsvorschau</h2>
      <p className="field-help">
        Die Vorschau zeigt deine Texte. Das fertige PDF übernimmt das Layout der gewählten
        Word-Vorlage.
      </p>
      <div className="document-preview">
        <h2>Abkündigung · {showText(payload.parish.name)}</h2>
        <p>
          {formatDate(payload.period.start)}–{formatDate(payload.period.end)}
        </p>
        {payload.days
          .filter((d) => d.enabled)
          .map((day) => (
            <section key={day.id}>
              <h3>
                {new Date(day.date + 'T12:00:00').toLocaleDateString('de-AT', { weekday: 'long' })},{' '}
                {formatDate(day.date)}
              </h3>
              {day.celebrations
                .filter((c) => c.enabled)
                .map((c) => (
                  <p key={c.id}>
                    <strong>{showText(c.title)}</strong>
                  </p>
                ))}
              {day.notices
                .filter((n) => n.enabled)
                .map((n) => (
                  <p key={n.id}>{showText(n.text)}</p>
                ))}
              {day.services
                .filter((s) => s.enabled)
                .map((service) => (
                  <div key={service.id} className="preview-service">
                    <p>
                      <strong>
                        {[service.time, showText(service.location), showText(service.title)]
                          .filter(Boolean)
                          .join(' · ')}
                      </strong>
                    </p>
                    {service.intentions
                      .filter((i) => i.enabled && showText(i.text))
                      .map((i) => (
                        <p key={i.id}>
                          {[i.symbol, showText(i.text), i.reference].filter(Boolean).join(' ')}
                        </p>
                      ))}
                    {service.notices
                      .filter((n) => n.enabled)
                      .map((n) => (
                        <p key={n.id}>{showText(n.text)}</p>
                      ))}
                  </div>
                ))}
            </section>
          ))}
        {payload.announcements
          .filter((a) => a.enabled)
          .map((a) => (
            <section key={a.id}>
              <h3>{showText(a.title)}</h3>
              {a.paragraphs.map((p, index) => (
                <p key={index}>{showText(p)}</p>
              ))}
            </section>
          ))}
        {payload.eternal_light.enabled && showText(payload.eternal_light.dedication) && (
          <p>
            <strong>Ewiges Licht:</strong> {showText(payload.eternal_light.dedication)}
          </p>
        )}
        {payload.office_hours.map((h, index) => (
          <p key={index}>
            Kanzleistunde ·{' '}
            {
              (
                {
                  monday: 'Montag',
                  tuesday: 'Dienstag',
                  wednesday: 'Mittwoch',
                  thursday: 'Donnerstag',
                  friday: 'Freitag',
                  saturday: 'Samstag',
                  sunday: 'Sonntag',
                } as Record<string, string>
              )[h.weekday]
            }{' '}
            {h.from}–{h.until}
          </p>
        ))}
        {payload.contact.persons.map((p, index) => (
          <p key={index}>
            {p.name} {p.phone}
          </p>
        ))}
        <p>
          {payload.contact.email} {payload.contact.website}
        </p>
      </div>
    </section>
  );
}
