interface QuotedMetricRangeParams {
    text: string;
    offset: number;
    position: { lineNumber: number; column: number };
}

/** Include both quotes when replacing an evaluation metric, including partial input. */
export function getQuotedMetricRange({ text, offset, position }: QuotedMetricRangeParams) {
    const tokens = /#[^\r\n]*|"(?:[^"\\\r\n]|\\.)*"?|'(?:[^'\\\r\n]|\\.)*'?/g;
    for (const match of text.matchAll(tokens)) {
        const start = match.index;
        const end = start + match[0].length;
        if (match[0].startsWith('#') || offset <= start || offset > end) continue;
        if (!/(?:\b(?:AND|OR|NOT)|\()\s*$/i.test(text.slice(0, start))) return undefined;
        return {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: position.column - (offset - start),
            endColumn: position.column + (end - offset)
        };
    }
    return undefined;
}
