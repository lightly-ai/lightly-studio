import * as monaco from 'monaco-editor';

export interface ParserErrorLike {
    message: string;
    token?: {
        startLine?: number;
        startColumn?: number;
        endLine?: number;
        endColumn?: number;
        image?: string;
    };
}

/** Converts a Chevrotain parser error (as surfaced by Langium) into a Monaco
 * marker. Coordinate systems differ: Chevrotain reports the last character of
 * a token via an inclusive `endColumn`, while Monaco's `endColumn` is
 * exclusive — the conversion lives here so callers can stay agnostic. */
export function parserErrorToMarker(err: ParserErrorLike): monaco.editor.IMarkerData {
    const token = err.token;
    const startLine = token?.startLine ?? 1;
    const startColumn = token?.startColumn ?? 1;
    const endLine = token?.endLine ?? startLine;
    // Chevrotain's endColumn is the column of the last character; Monaco's
    // endColumn is exclusive, so add 1.
    const endColumn = (token?.endColumn ?? startColumn) + 1;
    return {
        severity: monaco.MarkerSeverity.Error,
        message: err.message,
        startLineNumber: startLine,
        startColumn,
        endLineNumber: endLine,
        endColumn
    };
}
