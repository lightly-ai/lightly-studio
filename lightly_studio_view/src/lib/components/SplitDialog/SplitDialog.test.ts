import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SplitDialog from './SplitDialog.svelte';

const pageMock = vi.hoisted(() => ({
    params: { collection_id: 'test-collection-id' },
    data: { collection: { sample_type: 'image' as string } }
}));

vi.mock('$app/state', () => ({ page: pageMock }));

type MockTag = { tag_id: string; name: string; kind: 'sample' };
let tagsStore: Writable<MockTag[]>;

vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        tags: tagsStore,
        loadTags: vi.fn().mockResolvedValue(undefined),
        setTagSelected: vi.fn()
    })
}));

vi.mock('$lib/hooks/useSplitDialog/useSplitDialog', () => ({
    useSplitDialog: () => ({
        isSplitDialogOpen: readable(true),
        openSplitDialog: vi.fn(),
        closeSplitDialog: vi.fn()
    })
}));

const submitMock = vi.fn();
let isSubmittingStore: Writable<boolean>;

vi.mock('$lib/hooks/useCreateSplit/useCreateSplit', () => ({
    useCreateSplit: () => ({ isSubmitting: isSubmittingStore, submit: submitMock })
}));

let overlapData: { tags: { name: string; count: number }[] };

vi.mock('$lib/hooks/useSelectionTagOverlap/useSelectionTagOverlap.svelte', () => ({
    useSelectionTagOverlap: () => ({
        get data() {
            return overlapData;
        },
        isLoading: false,
        isSuccess: true
    })
}));

let imageFilterStore: Writable<Record<string, unknown> | null>;
let videoFilterStore: Writable<Record<string, unknown> | null>;
let filteredSampleCountStore: Writable<number>;

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({ imageFilter: imageFilterStore })
}));

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({ videoFilter: videoFilterStore })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ filteredSampleCount: filteredSampleCountStore })
}));

describe('SplitDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        pageMock.data.collection.sample_type = 'image';
        tagsStore = writable([]);
        isSubmittingStore = writable(false);
        imageFilterStore = writable(null);
        videoFilterStore = writable(null);
        filteredSampleCountStore = writable(1000);
        overlapData = { tags: [] };
        submitMock.mockResolvedValue(true);
    });

    it('renders the default train/val/test rows with previewed sample counts', () => {
        render(SplitDialog);

        const names = screen.getAllByTestId('split-name-input') as HTMLInputElement[];
        expect(names.map((input) => input.value)).toEqual(['train', 'val', 'test']);

        const previews = screen.getAllByTestId('split-count-preview');
        expect(previews.map((el) => el.textContent?.replace(/\s+/g, ' ').trim())).toEqual([
            '800 samples',
            '100 samples',
            '100 samples'
        ]);
    });

    it('informs which target splits will be created', () => {
        render(SplitDialog);

        expect(screen.getByTestId('split-created-info').textContent).toContain(
            'train, val and test will be created.'
        );
    });

    it('submits the split sizes when valid', async () => {
        render(SplitDialog);

        await fireEvent.submit(screen.getByTestId('split-submit').closest('form')!);

        expect(submitMock).toHaveBeenCalledWith({
            collectionId: 'test-collection-id',
            sizes: { train: 80, val: 10, test: 10 },
            filter: null
        });
    });

    it('warns and requires confirmation before clearing tags that overlap the selection', async () => {
        tagsStore.set([{ tag_id: 't-train', name: 'train', kind: 'sample' }]);
        overlapData = { tags: [{ name: 'train', count: 120 }] };
        render(SplitDialog);

        expect(screen.getByTestId('split-cleared-warning').textContent).toContain(
            'train (120 samples) will be cleared and reassigned.'
        );

        // First submit only arms the overwrite confirmation, without calling submit.
        await fireEvent.submit(screen.getByTestId('split-submit').closest('form')!);
        expect(submitMock).not.toHaveBeenCalled();

        await fireEvent.submit(screen.getByTestId('split-submit').closest('form')!);
        expect(submitMock).toHaveBeenCalledOnce();
    });
});
