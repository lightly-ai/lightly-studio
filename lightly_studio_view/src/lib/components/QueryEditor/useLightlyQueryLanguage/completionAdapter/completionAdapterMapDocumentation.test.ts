import { describe, expect, it } from 'vitest';

describe('mapDocumentation', () => {
    it('returns undefined for empty documentation', async () => {
        const { mapDocumentation } = await import('./completionAdapterMapDocumentation');
        expect(mapDocumentation(undefined)).toBeUndefined();
    });

    it('passes through plain string documentation', async () => {
        const { mapDocumentation } = await import('./completionAdapterMapDocumentation');
        expect(mapDocumentation('plain doc')).toBe('plain doc');
    });

    it('maps MarkupContent to Monaco markdown shape', async () => {
        const { mapDocumentation } = await import('./completionAdapterMapDocumentation');
        expect(mapDocumentation({ kind: 'markdown', value: '**bold**' })).toEqual({
            value: '**bold**'
        });
    });
});
