import {
    addSampleIdsToTagId,
    addSamplesToTagByFilter,
    createTag,
    removeSampleIdsFromTagId
} from '$lib/api/lightly_studio_local';
import type { TagByFilterBody } from '$lib/api/lightly_studio_local';
import type { TagView } from '$lib/services/types';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { useTagMutations } from './useTagMutations';

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        createTag: vi.fn(),
        addSampleIdsToTagId: vi.fn(),
        addSamplesToTagByFilter: vi.fn(),
        removeSampleIdsFromTagId: vi.fn()
    };
});

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: vi.fn() })
}));

const existingTag: TagView = {
    tag_id: 'tag-1',
    name: 'Vehicle',
    kind: 'sample',
    created_at: new Date('2024-01-01T00:00:00.000Z'),
    updated_at: new Date('2024-01-01T00:00:00.000Z')
};

const okResponse = { data: true, error: undefined };
const errorResponse = { data: undefined, error: { detail: 'boom' } };

const imageFilter = { filter_type: 'image' } as TagByFilterBody['filter'];

interface SetupOverrides {
    targetIds?: string[];
    snapshot?: { filter: TagByFilterBody['filter']; size: number } | null;
    tags?: TagView[];
}

function setup({
    targetIds = ['s1', 's2'],
    snapshot = null,
    tags = [existingTag]
}: SetupOverrides = {}) {
    const onSamplesRefetch = vi.fn();
    const onTagsRefetch = vi.fn();
    const mutations = useTagMutations({
        collectionId: 'collection-1',
        getTagKind: () => 'sample',
        getTargetIds: () => targetIds,
        getSelectAllSnapshot: () => snapshot,
        getExistingTags: () => tags,
        onSamplesRefetch,
        onTagsRefetch
    });
    return { ...mutations, onSamplesRefetch, onTagsRefetch };
}

describe('useTagMutations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(addSampleIdsToTagId).mockResolvedValue(okResponse as never);
        vi.mocked(addSamplesToTagByFilter).mockResolvedValue(okResponse as never);
        vi.mocked(removeSampleIdsFromTagId).mockResolvedValue(okResponse as never);
        vi.mocked(createTag).mockResolvedValue({ data: { tag_id: 'tag-new' } } as never);
    });

    it('assigns by id list and refetches the grid and tag list', async () => {
        const { assignTag, onSamplesRefetch, onTagsRefetch } = setup();

        await assignTag('tag-1');

        expect(addSampleIdsToTagId).toHaveBeenCalledWith({
            path: { collection_id: 'collection-1', tag_id: 'tag-1' },
            body: { sample_ids: ['s1', 's2'] }
        });
        expect(addSamplesToTagByFilter).not.toHaveBeenCalled();
        expect(onSamplesRefetch).toHaveBeenCalledTimes(1);
        expect(onTagsRefetch).toHaveBeenCalledTimes(1);
    });

    it('assigns by filter when the targets are an unmodified select-all', async () => {
        const { assignTag } = setup({
            targetIds: ['s1', 's2'],
            snapshot: { filter: imageFilter, size: 2 }
        });

        await assignTag('tag-1');

        expect(addSamplesToTagByFilter).toHaveBeenCalledWith({
            path: { collection_id: 'collection-1', tag_id: 'tag-1' },
            body: { filter: imageFilter }
        });
        expect(addSampleIdsToTagId).not.toHaveBeenCalled();
    });

    it('falls back to the id list when the select-all has been modified', async () => {
        const { assignTag } = setup({
            targetIds: ['s1'],
            snapshot: { filter: imageFilter, size: 2 }
        });

        await assignTag('tag-1');

        expect(addSampleIdsToTagId).toHaveBeenCalled();
        expect(addSamplesToTagByFilter).not.toHaveBeenCalled();
    });

    it('assigns an existing tag matched case-insensitively without creating one', async () => {
        const { assignByName, onTagsRefetch } = setup();

        await assignByName('vehicle');

        expect(createTag).not.toHaveBeenCalled();
        expect(addSampleIdsToTagId).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { collection_id: 'collection-1', tag_id: 'tag-1' }
            })
        );
        // Delegating to assignTag must not fire the callbacks twice.
        expect(onTagsRefetch).toHaveBeenCalledTimes(1);
    });

    it('creates a tag then assigns it and refreshes the tag list', async () => {
        const { assignByName, onTagsRefetch, onSamplesRefetch } = setup();

        await assignByName('Brand New');

        expect(createTag).toHaveBeenCalledWith({
            path: { collection_id: 'collection-1' },
            body: { name: 'Brand New', kind: 'sample' }
        });
        expect(addSampleIdsToTagId).toHaveBeenCalledWith(
            expect.objectContaining({
                path: { collection_id: 'collection-1', tag_id: 'tag-new' }
            })
        );
        expect(onTagsRefetch).toHaveBeenCalledTimes(1);
        expect(onSamplesRefetch).toHaveBeenCalledTimes(1);
    });

    it('removes a tag from every target, including a select-all', async () => {
        const { removeTag, onSamplesRefetch } = setup({
            targetIds: ['s1', 's2'],
            snapshot: { filter: imageFilter, size: 2 }
        });

        await removeTag('tag-1');

        // No remove-by-filter endpoint exists, so the ids are always sent.
        expect(removeSampleIdsFromTagId).toHaveBeenCalledWith({
            path: { collection_id: 'collection-1', tag_id: 'tag-1' },
            body: { sample_ids: ['s1', 's2'] }
        });
        expect(onSamplesRefetch).toHaveBeenCalledTimes(1);
    });

    it('toasts and skips the refetch when a mutation fails', async () => {
        vi.mocked(removeSampleIdsFromTagId).mockResolvedValue(errorResponse as never);
        const { removeTag, busy, onSamplesRefetch } = setup();

        await removeTag('tag-1');

        expect(toast.error).toHaveBeenCalledWith('Failed to remove tag. Please try again.');
        expect(onSamplesRefetch).not.toHaveBeenCalled();
        expect(get(busy)).toBe(false);
    });

    it('does nothing when there are no targets', async () => {
        const { assignTag, removeTag } = setup({ targetIds: [] });

        await assignTag('tag-1');
        await removeTag('tag-1');

        expect(addSampleIdsToTagId).not.toHaveBeenCalled();
        expect(removeSampleIdsFromTagId).not.toHaveBeenCalled();
    });
});
