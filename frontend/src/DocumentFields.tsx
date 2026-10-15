import { Trash2 } from 'lucide-react';
import type { Bilingual, Notice } from './documentTypes';

export const emptyText = (): Bilingual => ({ de: '', sl: '' });
export const newId = () => crypto.randomUUID();
export const newNotice = (): Notice => ({ id: newId(), enabled: true, text: emptyText() });
export const showText = (text: Bilingual) => [text.de, text.sl].filter(Boolean).join(' | ');
export const formatDate = (date: string) =>
  new Date(date + 'T12:00:00').toLocaleDateString('de-AT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });

export function TextFields({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string;
  value: Bilingual;
  onChange: (value: Bilingual) => void;
  multiline?: boolean;
}) {
  return (
    <div className="bilingual-fields">
      {(['de', 'sl'] as const).map((language) => (
        <label key={language}>
          {label} · {language === 'de' ? 'Deutsch' : 'Slowenisch'}
          {multiline ? (
            <textarea
              rows={3}
              maxLength={10000}
              value={value[language]}
              onChange={(e) => onChange({ ...value, [language]: e.target.value })}
            />
          ) : (
            <input
              maxLength={10000}
              value={value[language]}
              onChange={(e) => onChange({ ...value, [language]: e.target.value })}
            />
          )}
        </label>
      ))}
    </div>
  );
}

export function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      className="icon-button remove-item"
      aria-label={label}
      title={label}
      onClick={onClick}
    >
      <Trash2 size={16} />
    </button>
  );
}

export function NoticeFields({
  notices,
  onChange,
  label = 'Hinweis',
}: {
  notices: Notice[];
  onChange: (notices: Notice[]) => void;
  label?: string;
}) {
  return (
    <div className="notice-fields">
      {notices.map((notice, index) => (
        <div key={notice.id} className="document-item">
          <div className="document-item-bar">
            <label className="inline-check">
              <input
                type="checkbox"
                checked={notice.enabled}
                onChange={(e) =>
                  onChange(
                    notices.map((n, i) => (i === index ? { ...n, enabled: e.target.checked } : n)),
                  )
                }
              />
              {label} ausgeben
            </label>
            <RemoveButton
              label={`${label} entfernen`}
              onClick={() => onChange(notices.filter((_, i) => i !== index))}
            />
          </div>
          <TextFields
            label={label}
            multiline
            value={notice.text}
            onChange={(text) => onChange(notices.map((n, i) => (i === index ? { ...n, text } : n)))}
          />
        </div>
      ))}
      <button
        className="button secondary"
        type="button"
        onClick={() => onChange([...notices, newNotice()])}
      >
        + {label} hinzufügen
      </button>
    </div>
  );
}
