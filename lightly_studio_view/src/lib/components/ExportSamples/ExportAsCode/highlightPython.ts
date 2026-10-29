export type PythonTokenKind = 'keyword' | 'string' | 'comment' | 'number' | 'plain';

export interface PythonToken {
    kind: PythonTokenKind;
    text: string;
}

const KEYWORDS = new Set([
    'as',
    'def',
    'for',
    'from',
    'if',
    'import',
    'in',
    'None',
    'True',
    'False',
    'with'
]);

// One alternative per token kind, tried left to right. Strings may carry an f prefix.
const TOKEN_PATTERN =
    /(#[^\n]*)|([fF]?"(?:[^"\\\n]|\\.)*"|[fF]?'(?:[^'\\\n]|\\.)*')|\b(\d+(?:\.\d+)?)\b|\b([A-Za-z_]\w*)\b/g;

/**
 * Splits the short scripts the export dialog generates into tokens to color. Covers comments,
 * strings, numbers and keywords; everything else is plain. Joining the token texts gives the
 * input back.
 */
export function highlightPython(code: string): PythonToken[] {
    const tokens: PythonToken[] = [];
    const pushPlain = (text: string) => {
        if (!text) return;
        const last = tokens.at(-1);
        if (last?.kind === 'plain') last.text += text;
        else tokens.push({ kind: 'plain', text });
    };
    let position = 0;
    for (const match of code.matchAll(TOKEN_PATTERN)) {
        const [text, comment, string, number, word] = match;
        pushPlain(code.slice(position, match.index));
        position = match.index + text.length;
        if (comment) tokens.push({ kind: 'comment', text });
        else if (string) tokens.push({ kind: 'string', text });
        else if (number) tokens.push({ kind: 'number', text });
        else if (word && KEYWORDS.has(word)) tokens.push({ kind: 'keyword', text });
        else pushPlain(text);
    }
    pushPlain(code.slice(position));
    return tokens;
}
