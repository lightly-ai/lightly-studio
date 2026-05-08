import { describe, expect, it } from 'vitest';

describe('enrichWithSchemaDocs', () => {
    it('keeps explicit documentation untouched', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');
        const item = { label: 'width', documentation: { value: 'custom' } };
        expect(enrichWithSchemaDocs(item as never, 'image')).toBe(item);
    });

    it('enriches known keyword when docs are missing', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');
        const result = enrichWithSchemaDocs({ label: 'AND' } as never, 'image');
        expect(result.detail).toBe('Boolean AND. Combines two conditions.');
        expect(result.documentation).toEqual({ value: 'Boolean AND. Combines two conditions.' });
    });

    it('enriches known field with scope/type metadata when docs are missing', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');
        const result = enrichWithSchemaDocs({ label: 'fps' } as never, 'video');
        expect(result.detail).toBe('(field) Video.fps: float');
        expect(result.documentation).toEqual({
            value: 'Frames per second. Equality only (`==`, `!=`).'
        });
    });

    it('returns unchanged item for unknown label', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');
        const item = { label: 'unknown' };
        const result = enrichWithSchemaDocs(item as never, 'image');
        expect(result).toEqual(item);
    });
});
