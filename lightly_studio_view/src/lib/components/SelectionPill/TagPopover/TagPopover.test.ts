import { QueryClient } from '@tanstack/svelte-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    addSampleIdsToTagId,
    addSamplesToTagByFilter,
    countTagsForSelection,
    createTag,
    removeSamplesFromTagByFilter,
    removeThingIdsToTagId
} from '$lib/api/lightly_studio_local/sdk.gen';
import TagPopoverHarness from './TagPopoverHarness.svelte';

const mocks = await vi.hoisted(async () => {
    const { writable } = await import('svelte/store');
    return {
        target: { kind: 'ids', ids: ['s1', 's2', 's3'] } as unknown,
        tags: writable<{ tag_id: string; name: string }[]>([]),
        loadTags: vi.fn()
    };
});
const baseTags = [
    { tag_id: 'a', name: 'a' },
    { tag_id: 'b', name: 'b' },
    { tag_id: 'c', name: 'c' }
];

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async () => ({
    ...(await vi.importActual('$lib/api/lightly_studio_local/sdk.gen')),
    countTagsForSelection: vi.fn(),
    createTag: vi.fn(),
    addSampleIdsToTagId: vi.fn(),
    addSamplesToTagByFilter: vi.fn(),
    removeThingIdsToTagId: vi.fn(),
    removeSamplesFromTagByFilter: vi.fn()
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('$lib/hooks/useSelectionTarget/useSelectionTarget', () => ({
    getSelectionTarget: () => mocks.target
}));
vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        tags: mocks.tags,
        loadTags: mocks.loadTags
    })
}));

function setup() {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    render(TagPopoverHarness, { client, selectedCount: 3 });
    return { invalidate };
}

beforeEach(() => {
    vi.clearAllMocks();
    mocks.tags.set(baseTags);
    mocks.target = { kind: 'ids', ids: ['s1', 's2', 's3'] };
    vi.mocked(countTagsForSelection).mockResolvedValue({
        data: [
            { tag_id: 'a', count: 1 },
            { tag_id: 'b', count: 3 }
        ]
    } as never);
    const ok = { data: {} } as never;
    vi.mocked(addSampleIdsToTagId).mockResolvedValue(ok);
    vi.mocked(addSamplesToTagByFilter).mockResolvedValue(ok);
    vi.mocked(removeThingIdsToTagId).mockResolvedValue(ok);
    vi.mocked(removeSamplesFromTagByFilter).mockResolvedValue(ok);
    vi.mocked(createTag).mockResolvedValue({ data: { tag_id: 'new' } } as never);
});

describe('TagPopover', () => {
    it('shows k/N per tag and a list that scrolls after 5 rows', async () => {
        setup();
        expect(await screen.findByText('1/3')).toBeInTheDocument();
        expect(screen.getByText('3/3')).toBeInTheDocument();
        expect(screen.getByText('0/3')).toBeInTheDocument();
        const list = screen.getByTestId('tag-popover-list');
        expect(list).toHaveClass('max-h-40', 'overflow-y-auto');
    });

    it('adds by IDs, toasts and invalidates counts, tags and grids', async () => {
        const { invalidate } = setup();
        await screen.findByText('1/3');
        await fireEvent.click(screen.getByLabelText('Add a to selection'));

        await waitFor(() =>
            expect(addSampleIdsToTagId).toHaveBeenCalledWith({
                path: { collection_id: 'c1', tag_id: 'a' },
                body: { sample_ids: ['s1', 's2', 's3'] }
            })
        );
        expect(toast.success).toHaveBeenCalledWith("Added 'a' to 3 items");
        expect(mocks.loadTags).toHaveBeenCalled();
        const keys = invalidate.mock.calls.map(([filters]) => JSON.stringify(filters?.queryKey));
        expect(keys.some((k) => k.includes('countTagsForSelection'))).toBe(true);
        expect(keys).toContain(JSON.stringify(['readImagesInfinite', 'c1']));
        expect(keys).toContain(JSON.stringify(['readAnnotationsWithPayloadInfinite', 'c1']));
    });

    it('adds by filter when the target is a filter', async () => {
        mocks.target = { kind: 'filter', filter: { x: 1 }, size: 3 };
        setup();
        await screen.findByText('1/3');
        await fireEvent.click(screen.getByLabelText('Add a to selection'));
        await waitFor(() =>
            expect(addSamplesToTagByFilter).toHaveBeenCalledWith({
                path: { collection_id: 'c1', tag_id: 'a' },
                body: { filter: { x: 1 } }
            })
        );
        expect(addSampleIdsToTagId).not.toHaveBeenCalled();
    });

    it('removes with the x button', async () => {
        setup();
        await screen.findByText('3/3');
        await fireEvent.click(screen.getByLabelText('Remove b from selection'));
        await waitFor(() =>
            expect(removeThingIdsToTagId).toHaveBeenCalledWith({
                path: { tag_id: 'b' },
                body: { sample_ids: ['s1', 's2', 's3'] }
            })
        );
        expect(toast.success).toHaveBeenCalledWith("Removed 'b' from 3 items");
    });

    it('removes by filter when the target is a filter', async () => {
        mocks.target = { kind: 'filter', filter: { x: 1 }, size: 3 };
        setup();
        await screen.findByText('3/3');
        await fireEvent.click(screen.getByLabelText('Remove b from selection'));
        await waitFor(() =>
            expect(removeSamplesFromTagByFilter).toHaveBeenCalledWith({
                path: { collection_id: 'c1', tag_id: 'b' },
                body: { filter: { x: 1 } }
            })
        );
    });

    it('offers Create for an unknown name and assigns on Enter', async () => {
        setup();
        const input = await screen.findByPlaceholderText('Search or create a tag…');
        const user = userEvent.setup();
        await user.type(input, 'fresh');
        expect(await screen.findByText("Create 'fresh'")).toBeInTheDocument();
        await user.keyboard('{Enter}');

        await waitFor(() =>
            expect(createTag).toHaveBeenCalledWith({
                path: { collection_id: 'c1' },
                body: { name: 'fresh' }
            })
        );
        await waitFor(() =>
            expect(addSampleIdsToTagId).toHaveBeenCalledWith(
                expect.objectContaining({ path: { collection_id: 'c1', tag_id: 'new' } })
            )
        );
        expect(toast.success).toHaveBeenCalledWith("Added 'fresh' to 3 items");
    });

    describe('create failures', () => {
        async function typeFresh() {
            setup();
            const input = await screen.findByPlaceholderText('Search or create a tag…');
            const user = userEvent.setup();
            await user.type(input, 'fresh');
            await screen.findByText("Create 'fresh'");
            return { input, user };
        }

        it('toasts an error and does not reject when createTag throws', async () => {
            const unhandled = vi.fn();
            process.on('unhandledRejection', unhandled);
            vi.mocked(createTag).mockRejectedValue(new Error('network'));
            const { user } = await typeFresh();
            await user.keyboard('{Enter}');

            await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to create tag.'));
            await new Promise((resolve) => setTimeout(resolve, 0));
            process.off('unhandledRejection', unhandled);
            expect(unhandled).not.toHaveBeenCalled();
        });

        it('refreshes tags and keeps the input when the add after create fails', async () => {
            vi.mocked(addSampleIdsToTagId).mockResolvedValueOnce({ error: {} } as never);
            mocks.loadTags.mockImplementation(() =>
                mocks.tags.set([...baseTags, { tag_id: 'new', name: 'fresh' }])
            );
            const { input, user } = await typeFresh();
            await user.keyboard('{Enter}');

            await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to add tag.'));
            expect(mocks.loadTags).toHaveBeenCalled();
            expect(input).toHaveValue('fresh');

            // The tag now exists, so the Create row is gone and a retry only adds.
            await waitFor(() => expect(screen.queryByText("Create 'fresh'")).toBeNull());
            await user.keyboard('{Enter}');
            await waitFor(() =>
                expect(toast.success).toHaveBeenCalledWith("Added 'fresh' to 3 items")
            );
            expect(createTag).toHaveBeenCalledTimes(1);
        });
    });
});
