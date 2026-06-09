import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSelectionFilter } from './useSelectionFilter';

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({ useImageFilters: vi.fn() }));
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({ useVideoFilters: vi.fn() }));

const { useImageFilters } = await import('$lib/hooks/useImageFilters/useImageFilters');
const { useVideoFilters } = await import('$lib/hooks/useVideoFilters/useVideoFilters');

describe('useSelectionFilter', () => {
    let imageFilter: ReturnType<typeof writable>;
    let videoFilter: ReturnType<typeof writable>;

    beforeEach(() => {
        vi.clearAllMocks();
        imageFilter = writable(null);
        videoFilter = writable(null);
        vi.mocked(useImageFilters).mockReturnValue({ imageFilter } as never);
        vi.mocked(useVideoFilters).mockReturnValue({ videoFilter } as never);
    });

    it('returns image filter with filter_type "image" for image collections', () => {
        imageFilter.set({ sample_filter: { tag_ids: ['t-1'] } });
        const { buildSelectionFilter } = useSelectionFilter(() => false);

        expect(buildSelectionFilter()).toEqual({
            sample_filter: { tag_ids: ['t-1'] },
            filter_type: 'image'
        });
    });

    it('returns null when imageFilter is null', () => {
        imageFilter.set(null);
        const { buildSelectionFilter } = useSelectionFilter(() => false);

        expect(buildSelectionFilter()).toBeNull();
    });

    it('returns video filter with filter_type "video" for video collections', () => {
        videoFilter.set({ video_filter: { tag_ids: ['t-2'] } });
        const { buildSelectionFilter } = useSelectionFilter(() => true);

        expect(buildSelectionFilter()).toEqual({
            video_filter: { tag_ids: ['t-2'] },
            filter_type: 'video'
        });
    });

    it('returns null when videoFilter is null for video collections', () => {
        videoFilter.set(null);
        const { buildSelectionFilter } = useSelectionFilter(() => true);

        expect(buildSelectionFilter()).toBeNull();
    });
});
