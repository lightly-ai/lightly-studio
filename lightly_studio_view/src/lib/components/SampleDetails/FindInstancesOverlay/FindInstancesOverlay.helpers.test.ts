import { describe, expect, it } from 'vitest';
import { buildInstancesRequestBody, canGenerateInstances } from './FindInstancesOverlay.helpers';

describe('FindInstancesOverlay.helpers', () => {
    it('needs a non-blank prompt to generate', () => {
        expect(canGenerateInstances({ prompt: '  ' })).toBe(false);
        expect(canGenerateInstances({ prompt: 'car' })).toBe(true);
    });

    it('builds the request with a trimmed prompt and omits empty boxes', () => {
        expect(
            buildInstancesRequestBody({
                collectionId: 'c',
                sampleId: 's',
                prompt: ' cars ',
                boxes: [],
                maxInstances: 8
            })
        ).toEqual({
            collection_id: 'c',
            sample_id: 's',
            text_prompt: 'cars',
            boxes: null,
            max_instances: 8
        });

        const box = { x: 0.1, y: 0.1, width: 0.2, height: 0.2 };
        expect(
            buildInstancesRequestBody({
                collectionId: 'c',
                sampleId: 's',
                prompt: 'cars',
                boxes: [box],
                maxInstances: 16
            })
        ).toMatchObject({ text_prompt: 'cars', boxes: [box] });
    });
});
