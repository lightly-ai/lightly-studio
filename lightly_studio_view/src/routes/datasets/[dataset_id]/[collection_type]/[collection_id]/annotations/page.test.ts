const { trackEvent } = vi.hoisted(() => ({ trackEvent: vi.fn() }));
vi.mock('$lib/hooks', () => ({
    usePostHog: () => ({ trackEvent })
}));
vi.mock('$app/state', () => ({
    page: { params: { dataset_id: 'image-collection', collection_id: 'annotation-collection' } }
}));
vi.mock('$lib/components', () => ({ AnnotationsGrid: vi.fn() }));

import { render, waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import * as lightly_studio_local from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useTags } from '$lib/hooks/useTags/useTags';
import AnnotationsPage from './+page.svelte';

const tagIdByCollection: Record<string, string> = {
    'image-collection': 'image-tag',
    'annotation-collection': 'annotation-tag'
};

describe('annotations +page.svelte', () => {
    it('clears the tag selection of the annotation collection when entered from another grid', async () => {
        vi.spyOn(lightly_studio_local, 'readTags').mockImplementation(async ({ path }) => ({
            data: [
                {
                    tag_id: tagIdByCollection[path.collection_id],
                    name: tagIdByCollection[path.collection_id],
                    created_at: new Date(0),
                    updated_at: new Date(0)
                }
            ],
            error: undefined,
            request: new Request('http://localhost'),
            response: new Response()
        }));
        const imageTags = useTags({ collection_id: 'image-collection' });
        const annotationTags = useTags({ collection_id: 'annotation-collection' });
        await Promise.all([imageTags.loadTags(), annotationTags.loadTags()]);
        imageTags.setTagSelected('image-tag', true);
        annotationTags.setTagSelected('annotation-tag', true);
        useGlobalStorage().setLastGridType('images');

        render(AnnotationsPage);

        await waitFor(() => expect(get(annotationTags.tagsSelected)).toEqual(new Set()));
        expect(get(imageTags.tagsSelected)).toEqual(new Set(['image-tag']));
    });
});
