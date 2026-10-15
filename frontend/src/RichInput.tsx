import { useEffect, useRef, useState } from 'react';
import { Bold, Underline } from 'lucide-react';
import type { TextMark } from './documentTypes';

function read(element: HTMLElement, defaultBold: boolean) {
  let value = '';
  const marks: TextMark[] = [];
  function append(text: string, bold: boolean, underline: boolean) {
    text = text.replaceAll('\u00a0', ' ');
    const start = Array.from(value).length;
    value += text;
    if (text && (bold !== defaultBold || underline)) {
      const end = Array.from(value).length;
      const previous = marks.at(-1);
      if (previous?.end === start && previous.bold === bold && !!previous.underline === underline)
        previous.end = end;
      else marks.push({ start, end, bold, ...(underline ? { underline: true } : {}) });
    }
  }
  function walk(node: Node, bold: boolean, underline: boolean) {
    if (node.nodeType === Node.TEXT_NODE) {
      append(node.textContent ?? '', bold, underline);
      return;
    }
    if (!(node instanceof HTMLElement)) return;
    if (node.tagName === 'BR') {
      if (
        node.parentElement &&
        ['DIV', 'P'].includes(node.parentElement.tagName) &&
        node.parentElement.childNodes.length === 1 &&
        node.parentElement !== element
      )
        return;
      append('\n', bold, underline);
      return;
    }
    if ((node.tagName === 'DIV' || node.tagName === 'P') && (value || node.previousSibling))
      append('\n', bold, underline);
    if (node.tagName === 'B' || node.tagName === 'STRONG') bold = true;
    const weight = node.style.fontWeight;
    if (weight) bold = weight === 'bold' || Number(weight) >= 600;
    if (
      node.tagName === 'U' ||
      node.style.textDecoration.includes('underline') ||
      node.style.textDecorationLine.includes('underline')
    )
      underline = true;
    if (node.style.textDecoration === 'none' || node.style.textDecorationLine === 'none')
      underline = false;
    node.childNodes.forEach((child) => walk(child, bold, underline));
  }
  element.childNodes.forEach((node) => walk(node, defaultBold, false));
  if (value === '\n' && element.innerText.trim() === '') return { value: '', marks: [] };
  return { value, marks };
}

function write(element: HTMLElement, value: string, marks: TextMark[]) {
  const chars = Array.from(value);
  const bounds = [...new Set([0, chars.length, ...marks.flatMap((m) => [m.start, m.end])])].sort(
    (a, b) => a - b,
  );
  const nodes: Node[] = [];
  for (let i = 0; i < bounds.length - 1; i++) {
    const start = bounds[i],
      end = bounds[i + 1];
    const mark = marks.find((m) => m.start <= start && m.end >= end);
    const text = document.createTextNode(chars.slice(start, end).join(''));
    if (mark) {
      const span = document.createElement('span');
      span.style.fontWeight = mark.bold ? 'bold' : 'normal';
      span.style.textDecoration = mark.underline ? 'underline' : 'none';
      span.append(text);
      nodes.push(span);
    } else nodes.push(text);
  }
  element.replaceChildren(...nodes);
}

export default function RichInput({
  label,
  value,
  marks = [],
  defaultBold = false,
  multiline = false,
  onChange,
}: {
  label: string;
  value: string;
  marks?: TextMark[];
  defaultBold?: boolean;
  multiline?: boolean;
  onChange: (value: string, marks: TextMark[]) => void;
}) {
  const editor = useRef<HTMLDivElement>(null);
  const last = useRef('');
  const [underlined, setUnderlined] = useState(false);
  const [pressed, setPressed] = useState(defaultBold);
  const serialized = JSON.stringify({ value, marks });
  useEffect(() => {
    const element = editor.current!;
    if (serialized !== last.current) {
      write(element, value, marks);
      last.current = serialized;
    }
  }, [serialized, value, marks]);
  function update() {
    const result = read(editor.current!, defaultBold);
    const chars = Array.from(result.value);
    if (chars.length > 10000) {
      result.value = chars.slice(0, 10000).join('');
      result.marks = result.marks
        .filter((m) => m.start < 10000)
        .map((m) => ({ ...m, end: Math.min(m.end, 10000) }));
      write(editor.current!, result.value, result.marks);
    }
    last.current = JSON.stringify(result);
    onChange(result.value, result.marks);
    setPressed(document.queryCommandState('bold'));
    setUnderlined(document.queryCommandState('underline'));
  }
  function toggle(command = 'bold') {
    if (editor.current?.closest('fieldset[disabled]')) return;
    editor.current?.focus();
    document.execCommand(command);
    update();
  }
  return (
    <div className="rich-field">
      <div className="rich-label">{label}</div>
      <div className="rich-toolbar">
        <button
          type="button"
          className="rich-bold"
          aria-label={`${label}: Fett`}
          aria-pressed={pressed}
          title="Text markieren und fett umschalten (Strg+B)"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => toggle()}
        >
          <Bold size={15} />
          <span>Fett</span>
        </button>
        <button
          type="button"
          className="rich-bold"
          aria-label={`${label}: Unterstreichen`}
          aria-pressed={underlined}
          title="Unterstreichen (Strg+U)"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => toggle('underline')}
        >
          <Underline size={15} />
          <span>Unterstreichen</span>
        </button>
        <span>Strg+B / Strg+U</span>
      </div>
      <div
        ref={editor}
        contentEditable
        suppressContentEditableWarning
        role="textbox"
        aria-label={label}
        aria-multiline={multiline}
        className={`rich-input ${multiline ? 'multiline' : ''}`}
        style={{ fontWeight: defaultBold ? 700 : 400 }}
        onInput={update}
        onKeyDown={(event) => {
          if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'u') {
            event.preventDefault();
            toggle('underline');
          }
          if (!multiline && event.key === 'Enter') event.preventDefault();
        }}
        onBeforeInput={(event) => {
          if (editor.current?.closest('fieldset[disabled]')) event.preventDefault();
        }}
        onFocus={() => {
          if (editor.current?.closest('fieldset[disabled]')) editor.current.blur();
        }}
        onKeyUp={() => {
          setPressed(document.queryCommandState('bold'));
          setUnderlined(document.queryCommandState('underline'));
        }}
        onMouseUp={() => {
          setPressed(document.queryCommandState('bold'));
          setUnderlined(document.queryCommandState('underline'));
        }}
        onPaste={(event) => {
          event.preventDefault();
          if (editor.current?.closest('fieldset[disabled]')) return;
          const plain = event.clipboardData.getData('text/plain').replace(/\r\n?/g, '\n');
          document.execCommand(
            'insertText',
            false,
            multiline ? plain : plain.replaceAll('\n', ' '),
          );
        }}
      />
    </div>
  );
}
