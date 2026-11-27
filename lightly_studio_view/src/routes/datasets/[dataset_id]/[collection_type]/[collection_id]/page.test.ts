import { describe, expect, it, vi } from 'vitest';
import { SampleType } from '$lib/api/lightly_studio_local';
import { routeHelpers } from '$lib/routes';
import type { PageLoadEvent } from './$types';
import { load } from './+page';

vi.mock('@sveltejs/kit', () => ({
    redirect: vi.fn((status: number, location: string) => {
        throw { type: 'redirect', status, location };
    }),
    error: vi.fn((status: number, message: string) => {
        throw { type: 'error', status, message };
    })
}));

type Thrown = { type: string; status: number; location?: string; message?: string };

const datasetId = 'dataset-1';
const collectionId = 'collection-1';

const runLoad = async (collection: unknown): Promise<Thrown> => {
    try {
        await load({
            params: { dataset_id: datasetId, collection_type: 'any', collection_id: collectionId },
            parent: async () => ({ collection })
        } as unknown as PageLoadEvent);
    } catch (thrown) {
        return thrown as Thrown;
    }
    throw new Error('load should have thrown');
};

describe('[collection_id]/+page.ts', () => {
    it.each([
        [SampleType.VIDEO, routeHelpers.toVideos],
        [SampleType.VIDEO_FRAME, routeHelpers.toFrames],
        [SampleType.IMAGE, routeHelpers.toImages],
        [SampleType.ANNOTATION, routeHelpers.toAnnotations],
        [SampleType.CAPTION, routeHelpers.toCaptions],
        [SampleType.GROUP, routeHelpers.toGroups],
        [SampleType.SEQUENCE, routeHelpers.toMcapSequences]
    ])('redirects %s collections to their route', async (sampleType, routeBuilder) => {
        const thrown = await runLoad({ collection_id: collectionId, sample_type: sampleType });

        expect(thrown).toEqual({
            type: 'redirect',
            status: 307,
            location: routeBuilder(datasetId, sampleType.toLowerCase(), collectionId)
        });
    });

    it('throws 500 when the layout did not load a collection', async () => {
        const thrown = await runLoad(undefined);

        expect(thrown).toMatchObject({ type: 'error', status: 500 });
    });

    it('throws 404 for an unknown sample type', async () => {
        const thrown = await runLoad({ collection_id: collectionId, sample_type: 'unknown' });

        expect(thrown).toMatchObject({
            type: 'error',
            status: 404,
            message: 'Unknown sample type: unknown'
        });
    });
});
