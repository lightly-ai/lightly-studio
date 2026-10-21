import { render } from '@testing-library/svelte';
import { get, readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useTags } from '$lib/hooks/useTags/useTags';
import { SampleType } from '$lib/api/lightly_studio_local';
import ImagesPage from './+page.svelte';

vi.mock('$app/state', () => ({
    page: { params: { collection_id: 'images-id' } }
}));
vi.mock('$lib/components/index.js', async () => ({
    Images: (await import('../LayoutStub.test.svelte')).default
}));
vi.mock('$lib/hooks/useTags/useTags', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/hooks/useTags/useTags')>();
    return {
        useTags: (options: Parameters<typeof actual.useTags>[0]) =>
            actual.useTags({ ...options, autoLoad: false })
    };
});

describe('images page tag filters', () => {
    const storage = useGlobalStorage();
    const tags = useTags({ collection_id: 'images-id', autoLoad: false });
    const defaultProps = {
        data: {
            collection: {
                collection_id: 'images-id',
                dataset_id: 'images-id',
                name: 'Images',
                sample_type: SampleType.IMAGE,
                created_at: new Date(),
                updated_at: new Date(),
                total_sample_count: 0
            },
            collectionHierarchy: [],
            sampleSize: storage.sampleSize,
            globalStorage: storage,
            samplesSelectedTagsIds: tags.tagsSelected,
            samplesDimensions: readable(null),
            samplesTextEmbedding: storage.textEmbedding
        }
    };

    beforeEach(() => {
        tags.clearTagsSelected();
        tags.setTagSelected('tag-1', true);
    });

    it.each(['images', 'captions'] as const)(
        'preserves selected tags when returning from %s',
        (gridType) => {
            storage.setLastGridType(gridType);
            render(ImagesPage, {
                props: defaultProps
            });

            expect(get(tags.tagsSelected)).toEqual(new Set(['tag-1']));
        }
    );

    it('still clears tags when returning from annotations', () => {
        storage.setLastGridType('annotations');
        render(ImagesPage, {
            props: defaultProps
        });

        expect(get(tags.tagsSelected).size).toBe(0);
    });
});
