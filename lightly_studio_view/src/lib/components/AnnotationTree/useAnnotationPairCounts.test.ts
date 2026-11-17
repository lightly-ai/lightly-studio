import { render, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { describe, expect, it, vi } from 'vitest';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import TreeCountsTestWrapper from './TreeCountsTestWrapper.test.svelte';
import { withoutTreeTicks } from './useAnnotationPairCounts.svelte';

const mocks = vi.hoisted(() => ({ countUnannotated: vi.fn(async () => ({ data: [] })) }));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    countUnannotatedImagesBySource: mocks.countUnannotated
}));

const treeTicks = {
    annotation_pairs: [{ collection_id: 'src-labels', annotation_label_id: 'lbl-car' }],
    unannotated_collection_ids: ['src-labels']
};

const withAnnotationsFilter = (annotationsFilter: object): ImageFilter => ({
    filter_type: 'image',
    sample_filter: {
        tag_ids: ['tag-1'],
        annotations_filter: { filter_type: 'annotations', ...annotationsFilter }
    }
});

describe('withoutTreeTicks', () => {
    it('drops the annotations filter when only the tree ticks are in it', () => {
        expect(withoutTreeTicks(withAnnotationsFilter(treeTicks))).toEqual({
            filter_type: 'image',
            sample_filter: { tag_ids: ['tag-1'] }
        });
    });

    it('keeps the other annotation fields', () => {
        expect(
            withoutTreeTicks(withAnnotationsFilter({ ...treeTicks, tag_ids: ['tag-2'] }))
        ).toEqual(withAnnotationsFilter({ tag_ids: ['tag-2'] }));
    });

    it('sends no annotations filter for the "No annotations" counts', async () => {
        const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
        render(TreeCountsTestWrapper, { client, filter: withAnnotationsFilter(treeTicks) });

        await waitFor(() =>
            expect(mocks.countUnannotated).toHaveBeenCalledWith(
                expect.objectContaining({
                    body: {
                        filter: { filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } }
                    }
                })
            )
        );
    });
});
