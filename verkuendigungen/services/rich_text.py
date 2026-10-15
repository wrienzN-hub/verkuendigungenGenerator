"""Plain text plus validated, Unicode-codepoint-based bold/underline ranges. No HTML."""


class FormattedText(str):
    def __new__(cls, value='', marks=()):
        result = super().__new__(cls, value)
        result.marks = list(marks)
        return result


def join_text(parts, separator=''):
    output, marks = '', []
    for index, part in enumerate(parts):
        if index:
            output += separator
        for start, end, bold, underline in getattr(part, 'marks', []):
            marks.append((len(output) + start, len(output) + end, bold, underline))
        output += str(part)
    return FormattedText(output, marks)


def bilingual(value):
    parts = []
    for language in ['de', 'sl']:
        original = getattr(value, language)
        stripped = original.strip()
        if not stripped:
            continue
        left = len(original) - len(original.lstrip())
        marks = []
        for mark in getattr(value, language + '_marks', []):
            start, end = max(0, mark.start - left), min(len(stripped), mark.end - left)
            if start < end:
                marks.append((start, end, mark.bold, mark.underline))
        parts.append(FormattedText(stripped, marks))
    return join_text(parts, ' | ')


def bold_label(label, value):
    return join_text([FormattedText(label, [(0, len(label), True, False)]), ' ', value])
