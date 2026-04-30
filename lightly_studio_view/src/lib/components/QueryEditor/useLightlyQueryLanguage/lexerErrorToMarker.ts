import * as monaco from 'monaco-editor';

export interface LexerErrorLike {
    message: string;
    line?: number;
    column?: number;
    length?: number;
}

/** Converts a Chevrotain lexer error (as surfaced by Langium) into a Monaco
 * marker. Lexer errors are always single-line and carry an explicit `length`,
 * so the end position is derived as `column + length` (Monaco's exclusive
 * endColumn semantics line up with this directly). */
export function lexerErrorToMarker(err: LexerErrorLike): monaco.editor.IMarkerData {
    const startLine = err.line ?? 1;
    const startColumn = err.column ?? 1;
    const length = err.length ?? 1;
    return {
        severity: monaco.MarkerSeverity.Error,
        message: err.message,
        startLineNumber: startLine,
        startColumn,
        endLineNumber: startLine,
        endColumn: startColumn + length
    };
}
