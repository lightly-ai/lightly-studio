import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { splitDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import { toast } from 'svelte-sonner';
import DatasetSplitHarness from './DatasetSplitHarness.svelte';

const { loadTags, imageFilter, videoFilter, filteredSampleCount, tags } = await vi.hoisted(
    async () => {
        const { writable } = await import('svelte/store');
        return {
            loadTags: vi.fn(),
            imageFilter: writable({ filter_type: 'image', sample_filter: { tag_ids: ['images'] } }),
            videoFilter: writable({ filter_type: 'video', sample_filter: { tag_ids: ['videos'] } }),
            filteredSampleCount: writable(11),
            tags: writable([])
        };
    }
);
vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({ splitDataset: vi.fn() }));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn() } }));
vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter }),
    useVideoFilters: () => ({ videoFilter }),
    useGlobalStorage: () => ({ filteredSampleCount }),
    useTags: () => ({ tags, loadTags })
}));

function setup(sampleType: 'image' | 'video') {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const onClose = vi.fn();
    render(DatasetSplitHarness, { client, sampleType, onClose });
    return { invalidate, onClose };
}

beforeEach(() => {
    vi.clearAllMocks();
    filteredSampleCount.set(11);
    imageFilter.set({
        filter_type: 'image',
        sample_filter: { tag_ids: ['images'] }
    });
    videoFilter.set({
        filter_type: 'video',
        sample_filter: { tag_ids: ['videos'] }
    });
});

describe('useDatasetSplit', () => {
    it.each(['image', 'video'] as const)(
        'submits the captured %s scope and blocks repeats',
        async (sampleType) => {
            setup(sampleType);
            const filter = {
                filter_type: sampleType,
                sample_filter: { tag_ids: [`${sampleType}s`] }
            };
            const store = sampleType === 'image' ? imageFilter : videoFilter;
            store.update((filter) => ({ ...filter, sample_filter: { tag_ids: [] } }));
            filteredSampleCount.set(100);
            expect(screen.getByLabelText('Split 1 sample count')).toHaveTextContent('9 samples');
            await fireEvent.input(screen.getByLabelText('Seed (optional)'), {
                target: { value: '-7' }
            });
            vi.mocked(splitDataset).mockReturnValue(new Promise<never>(() => {}));
            const form = screen.getByRole('button', { name: 'Split dataset' }).closest('form')!;
            await fireEvent.submit(form);
            await fireEvent.submit(form);
            expect(splitDataset).toHaveBeenCalledOnce();
            expect(splitDataset).toHaveBeenCalledWith(
                expect.objectContaining({
                    path: { collection_id: 'collection' },
                    body: expect.objectContaining({ filter, seed: -7 })
                })
            );
            expect(screen.getByRole('button', { name: 'Splitting…' })).toBeDisabled();
        }
    );

    it('preserves inputs on failure and refreshes on a successful retry', async () => {
        const { invalidate, onClose } = setup('image');
        await fireEvent.input(screen.getByLabelText('Tag 1'), { target: { value: 'training' } });
        vi.mocked(splitDataset).mockRejectedValueOnce(new Error('Network error'));
        await fireEvent.click(screen.getByRole('button', { name: 'Split dataset' }));
        await waitFor(() =>
            expect(screen.getByRole('alert')).toHaveTextContent('Unable to split dataset')
        );
        expect(screen.getByLabelText('Tag 1')).toHaveValue('training');
        expect(onClose).not.toHaveBeenCalled();
        vi.mocked(splitDataset).mockResolvedValueOnce({
            data: [{ tag_name: 'training', sample_count: 9 }],
            request: new Request('http://localhost'),
            response: new Response()
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Split dataset' }));
        await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
        expect(loadTags).toHaveBeenCalledOnce();
        expect(invalidate).toHaveBeenCalledOnce();
        expect(toast.success).toHaveBeenCalledWith(
            'Created the following tags: training (9 samples).'
        );
    });
});
