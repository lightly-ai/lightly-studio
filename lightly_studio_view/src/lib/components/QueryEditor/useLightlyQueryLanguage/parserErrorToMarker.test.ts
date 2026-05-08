import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({
    MarkerSeverity: { Error: 8 }
}));

import { parserErrorToMarker } from './parserErrorToMarker';

describe('parserErrorToMarker', () => {
    it('maps token coordinates to a Monaco marker, adding 1 to endColumn', () => {
        expect(
            parserErrorToMarker({
                message: 'expected expression',
                token: { startLine: 3, startColumn: 4, endLine: 3, endColumn: 9 }
            })
        ).toEqual({
            severity: 8,
            message: 'expected expression',
            startLineNumber: 3,
            startColumn: 4,
            endLineNumber: 3,
            endColumn: 10
        });
    });

    it('falls back to (1, 1) when no token is present', () => {
        expect(parserErrorToMarker({ message: 'mystery' })).toEqual({
            severity: 8,
            message: 'mystery',
            startLineNumber: 1,
            startColumn: 1,
            endLineNumber: 1,
            endColumn: 2
        });
    });

    it('falls back endLine to startLine when only startLine is given', () => {
        const marker = parserErrorToMarker({
            message: 'x',
            token: { startLine: 5, startColumn: 2 }
        });
        expect(marker.startLineNumber).toBe(5);
        expect(marker.endLineNumber).toBe(5);
    });

    it('preserves multi-line ranges from the token', () => {
        const marker = parserErrorToMarker({
            message: 'x',
            token: { startLine: 2, startColumn: 3, endLine: 4, endColumn: 1 }
        });
        expect(marker.startLineNumber).toBe(2);
        expect(marker.endLineNumber).toBe(4);
        expect(marker.endColumn).toBe(2);
    });

    it('falls back endColumn to startColumn + 1 when token has no endColumn', () => {
        const marker = parserErrorToMarker({
            message: 'x',
            token: { startLine: 1, startColumn: 6 }
        });
        expect(marker.endColumn).toBe(7);
    });
});
