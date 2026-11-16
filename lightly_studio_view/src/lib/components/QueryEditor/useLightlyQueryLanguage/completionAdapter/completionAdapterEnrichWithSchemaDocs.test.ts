import { describe, expect, it } from 'vitest';

describe('enrichWithSchemaDocs', () => {
    it.each(['tp', 'fp', 'fn', 'disagreement', 'miou'])(
        'enriches quoted evaluation keyword %s with field documentation',
        async (name) => {
            const { enrichWithSchemaDocs } =
                await import('./completionAdapterEnrichWithSchemaDocs');
            const result = enrichWithSchemaDocs(
                { label: `"${name}"` } as never,
                'sample_evaluation'
            );
            expect(result.detail).toBe(`Sample evaluation.${name}: float`);
            expect(result.documentation).toBeTruthy();
        }
    );
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
        expect(result.detail).toBe('Video.fps: float');
        expect(result.documentation).toEqual({
            value: 'Frames per second. Equality only (`=`, `!=`).'
        });
    });

    it('enriches annotation source and confidence fields in annotation scopes', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');

        const sourceResult = enrichWithSchemaDocs({ label: 'source' } as never, 'classification');
        expect(sourceResult.detail).toBe('Classification.source: string');
        expect(sourceResult.documentation).toEqual({
            value: 'Annotation source collection name.'
        });

        const confidenceResult = enrichWithSchemaDocs(
            { label: 'confidence' } as never,
            'object_detection'
        );
        expect(confidenceResult.detail).toBe('ObjectDetection.confidence: float');
        expect(confidenceResult.documentation).toEqual({
            value: 'Detection confidence score.'
        });
    });

    it('returns unchanged item for unknown label', async () => {
        const { enrichWithSchemaDocs } = await import('./completionAdapterEnrichWithSchemaDocs');
        const item = { label: 'unknown' };
        const result = enrichWithSchemaDocs(item as never, 'image');
        expect(result).toEqual(item);
    });
});
