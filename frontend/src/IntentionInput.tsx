import RichInput from './RichInput';
import type { Bilingual, TextMark } from './documentTypes';

export function intentionText(text: Bilingual) {
  let value = '';
  const marks: TextMark[] = [];
  for (const language of ['de', 'sl'] as const) {
    if (!text[language]) continue;
    if (value) value += '\n';
    const offset = Array.from(value).length;
    marks.push(
      ...(text[`${language}_marks`] ?? []).map((m) => ({
        ...m,
        start: m.start + offset,
        end: m.end + offset,
      })),
    );
    value += text[language];
  }
  return { value, marks };
}
export default function IntentionInput({
  value,
  onChange,
}: {
  value: Bilingual;
  onChange: (text: Bilingual) => void;
}) {
  const text = intentionText(value);
  return (
    <RichInput
      label="Messintention / Namen"
      multiline
      value={text.value}
      marks={text.marks}
      onChange={(de, de_marks) => onChange({ de, sl: '', de_marks, sl_marks: [] })}
    />
  );
}
