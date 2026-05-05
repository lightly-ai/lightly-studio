import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({
    MarkerSeverity: { Error: 8 }
}));

import { lexerErrorToMarker } from './lexerErrorToMarker';

describe('lexerErrorToMarker', () => {
    it('maps line/column/length to a Monaco marker', () => {
        expect(
            lexerErrorToMarker({
                message: 'unexpected character',
                line: 2,
                column: 5,
                length: 3
            })
        ).toEqual({
            severity: 8,
            message: 'unexpected character',
            startLineNumber: 2,
            startColumn: 5,
            endLineNumber: 2,
            endColumn: 8
        });
    });

    it('falls back to (1, 1) and length 1 when coordinates are missing', () => {
        expect(lexerErrorToMarker({ message: 'oops' })).toEqual({
            severity: 8,
            message: 'oops',
            startLineNumber: 1,
            startColumn: 1,
            endLineNumber: 1,
            endColumn: 2
        });
    });

    it('uses line for both start and end (lexer errors are single-line)', () => {
        const marker = lexerErrorToMarker({ message: 'x', line: 7, column: 3, length: 2 });
        expect(marker.startLineNumber).toBe(7);
        expect(marker.endLineNumber).toBe(7);
    });

    it('treats endColumn as start + length (exclusive)', () => {
        const marker = lexerErrorToMarker({ message: 'x', line: 1, column: 4, length: 5 });
        expect(marker.endColumn).toBe(9);
    });
});
