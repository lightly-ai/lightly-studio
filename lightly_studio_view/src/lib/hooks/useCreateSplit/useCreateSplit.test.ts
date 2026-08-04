import { createSplit } from '$lib/api/lightly_studio_local/sdk.gen';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCreateSplit } from './useCreateSplit';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    createSplit: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: vi.fn(), success: vi.fn() }
}));

const { toast } = await import('svelte-sonner');

describe('useCreateSplit', () => {
    const now = new Date();
    const tags = writable([
        {
            tag_id: 't-train',
            name: 'train',
            kind: 'sample' as const,
            created_at: now,
            updated_at: now
        },
        { tag_id: 't-val', name: 'val', kind: 'sample' as const, created_at: now, updated_at: now }
    ]);
    const defaultParams = {
        tags,
        setTagSelected: vi.fn(),
        loadTags: vi.fn().mockResolvedValue(undefined),
        closeSplitDialog: vi.fn()
    };
    const submitInput = {
        collectionId: 'col-1',
        sizes: { train: 80, val: 20 },
        filter: null,
        seed: 42
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('posts the split, toasts the summary, and selects the new tags', async () => {
        vi.mocked(createSplit).mockResolvedValue({
            data: {
                splits: [
                    { name: 'train', count: 8 },
                    { name: 'val', count: 2 }
                ],
                seed: 42
            },
            error: null
        } as never);

        const { submit } = useCreateSplit(defaultParams);
        const success = await submit(submitInput);

        expect(success).toBe(true);
        expect(createSplit).toHaveBeenCalledWith({
            path: { collection_id: 'col-1' },
            body: { sizes: { train: 80, val: 20 }, filter: undefined, seed: 42 }
        });
        expect(toast.success).toHaveBeenCalled();
        expect(defaultParams.loadTags).toHaveBeenCalled();
        expect(defaultParams.setTagSelected).toHaveBeenCalledWith('t-train', true);
        expect(defaultParams.setTagSelected).toHaveBeenCalledWith('t-val', true);
        expect(defaultParams.closeSplitDialog).toHaveBeenCalled();
    });

    it('toasts an error and keeps the dialog open on failure', async () => {
        vi.mocked(createSplit).mockResolvedValue({
            data: undefined,
            error: { error: 'boom' }
        } as never);

        const { submit } = useCreateSplit(defaultParams);
        const success = await submit(submitInput);

        expect(success).toBe(false);
        expect(toast.error).toHaveBeenCalled();
        expect(defaultParams.closeSplitDialog).not.toHaveBeenCalled();
    });
});
