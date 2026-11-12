import { describe, expect, it, vi } from 'vitest';

vi.mock('monaco-editor', () => ({
    MarkerSeverity: { Warning: 4 }
}));

import { createLightlyQueryServices } from '../language/lightly-query-module';
import { findUnknownTagMarkers } from './findUnknownTagMarkers';

const parser = createLightlyQueryServices().LightlyQuery.parser.LangiumParser;

function markersFor(text: string, tagNames: string[] = ['train']) {
    const query = parser.parse(text).value as Parameters<typeof findUnknownTagMarkers>[0]['query'];
    return findUnknownTagMarkers({ query, tagNames: new Set(tagNames) });
}

describe('findUnknownTagMarkers', () => {
    it('marks the quoted name of a tag that does not exist', () => {
        expect(markersFor('width < 5 AND\n  "tran" IN tags')).toEqual([
            {
                severity: 4,
                message: 'Tag "tran" does not exist.',
                startLineNumber: 2,
                startColumn: 3,
                endLineNumber: 2,
                endColumn: 9
            }
        ]);
    });

    it('does not mark a tag that exists', () => {
        expect(markersFor('"train" IN tags')).toEqual([]);
    });

    it('finds unknown tags inside nested expressions', () => {
        const markers = markersFor('NOT ("tran" IN tags) OR ("train" IN tags AND "vla" IN tags)');
        expect(markers.map((marker) => marker.message)).toEqual([
            'Tag "tran" does not exist.',
            'Tag "vla" does not exist.'
        ]);
    });

    it('does not throw for a query with a syntax error', () => {
        expect(() => markersFor('"tran" IN tags AND (')).not.toThrow();
    });
});
