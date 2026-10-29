import { waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '$lib/api/lightly_studio_local';
import { useMetadataFilters } from './useMetadataFilters';

const IMAGES_ID = '00000000-0000-4000-8000-000000000001';
const ANNOTATIONS_ID = '00000000-0000-4000-8000-000000000002';

const metadataInfoByCollection: Record<string, api.MetadataInfoView[]> = {
    [IMAGES_ID]: [{ name: 'temperature', type: 'float', min: 0, max: 100 }],
    [ANNOTATIONS_ID]: [{ name: 'score', type: 'float', min: 0, max: 1 }]
};

describe('useMetadataFilters per collection', () => {
    beforeEach(() => {
        vi.spyOn(api, 'getMetadataInfo').mockImplementation(async ({ path }) => ({
            data: metadataInfoByCollection[path.collection_id],
            error: undefined,
            request: new Request('http://localhost'),
            response: new Response()
        }));
    });

    it('gives a collection its own filters back when the user returns to it', async () => {
        const {
            metadataValues,
            categoricalMetadataValues,
            updateMetadataValues,
            updateCategoricalMetadataValues
        } = useMetadataFilters(IMAGES_ID);
        await waitFor(() =>
            expect(get(metadataValues)).toEqual({ temperature: { min: 0, max: 100 } })
        );
        updateMetadataValues({ temperature: { min: 20, max: 100 } });
        updateCategoricalMetadataValues({ camera: ['north'] });

        useMetadataFilters(ANNOTATIONS_ID);
        await waitFor(() => expect(get(metadataValues)).toEqual({ score: { min: 0, max: 1 } }));
        expect(get(categoricalMetadataValues)).toEqual({});

        useMetadataFilters(IMAGES_ID);
        await waitFor(() =>
            expect(get(metadataValues)).toEqual({ temperature: { min: 20, max: 100 } })
        );
        expect(get(categoricalMetadataValues)).toEqual({ camera: ['north'] });
    });
});
