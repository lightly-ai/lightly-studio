import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { VideoSortFieldExpr } from '$lib/api/lightly_studio_local';
import type { SortField } from '$lib/hooks/useVideoSortFields/useVideoSortFields';
import { VIDEO_SORT_FIELDS } from '$lib/hooks/useVideoSortFields/useVideoSortFields';
import { useVideoOrderBy } from './useVideoOrderBy';

const videoSortBy = writable<VideoSortFieldExpr[] | null>(null);
const allSortFields = writable<SortField[]>([...VIDEO_SORT_FIELDS]);
const updateSortBy = vi.fn();

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({ videoSortBy, updateSortBy })
}));

vi.mock('$lib/hooks/useVideoSortFields/useVideoSortFields', async (importOriginal) => {
    const original =
        await importOriginal<typeof import('$lib/hooks/useVideoSortFields/useVideoSortFields')>();
    return {
        ...original,
        useVideoSortFields: () => ({ allSortFields })
    };
});

describe('useVideoOrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        videoSortBy.set(null);
        allSortFields.set([...VIDEO_SORT_FIELDS]);
    });

    describe('selectedDirection', () => {
        it('returns ASC when no sort is active', () => {
            const { selectedDirection } = useVideoOrderBy({ collectionId: () => 'col1' });
            expect(get(selectedDirection)).toBe(SortDirection.ASC);
        });

        it('returns the direction of the active sort', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'file_name', direction: SortDirection.DESC }
            ]);
            const { selectedDirection } = useVideoOrderBy({ collectionId: () => 'col1' });
            expect(get(selectedDirection)).toBe(SortDirection.DESC);
        });
    });

    describe('selectedLabel', () => {
        it('returns null when no sort is active', () => {
            const { selectedLabel } = useVideoOrderBy({ collectionId: () => 'col1' });
            expect(get(selectedLabel)).toBeNull();
        });

        it('returns the label for an active video sort field', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'duration_s', direction: SortDirection.ASC }
            ]);
            const { selectedLabel } = useVideoOrderBy({ collectionId: () => 'col1' });
            expect(get(selectedLabel)).toBe('duration');
        });

        it('returns the metadata label when a metadata field is active', () => {
            allSortFields.set([
                ...VIDEO_SORT_FIELDS,
                { source: 'metadata', value: 'brightness', label: 'metadata.brightness' }
            ]);
            videoSortBy.set([
                { source: 'metadata', field_name: 'brightness', direction: SortDirection.ASC }
            ]);
            const { selectedLabel } = useVideoOrderBy({ collectionId: () => 'col1' });
            expect(get(selectedLabel)).toBe('metadata.brightness');
        });
    });

    describe('isFieldSelected', () => {
        it('returns false for any field when no sort is active', () => {
            const { isFieldSelected } = useVideoOrderBy({ collectionId: () => 'col1' });
            const check = get(isFieldSelected);

            expect(check({ source: 'video', value: 'file_name', label: 'file name' })).toBe(false);
        });

        it('returns true for the matching video field', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'width', direction: SortDirection.ASC }
            ]);
            const { isFieldSelected } = useVideoOrderBy({ collectionId: () => 'col1' });
            const check = get(isFieldSelected);

            expect(check({ source: 'video', value: 'width', label: 'width' })).toBe(true);
            expect(check({ source: 'video', value: 'height', label: 'height' })).toBe(false);
        });

        it('updates reactively when videoSortBy changes', () => {
            const { isFieldSelected } = useVideoOrderBy({ collectionId: () => 'col1' });
            const field = { source: 'video' as const, value: 'width', label: 'width' };

            expect(get(isFieldSelected)(field)).toBe(false);

            videoSortBy.set([
                { source: 'video', field_name: 'width', direction: SortDirection.ASC }
            ]);

            expect(get(isFieldSelected)(field)).toBe(true);
        });
    });

    describe('handleFieldClick', () => {
        it('selects a video field with ASC direction by default', () => {
            const { handleFieldClick } = useVideoOrderBy({ collectionId: () => 'col1' });

            handleFieldClick({ source: 'video', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'video', field_name: 'file_name', direction: SortDirection.ASC }
            ]);
        });

        it('deselects the field when clicking the already selected field', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'file_name', direction: SortDirection.ASC }
            ]);
            const { handleFieldClick } = useVideoOrderBy({ collectionId: () => 'col1' });

            handleFieldClick({ source: 'video', value: 'file_name', label: 'file name' });

            expect(updateSortBy).toHaveBeenCalledWith(null);
        });

        it('switches to a different field while preserving the current direction', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'file_name', direction: SortDirection.DESC }
            ]);
            const { handleFieldClick } = useVideoOrderBy({ collectionId: () => 'col1' });

            handleFieldClick({ source: 'video', value: 'width', label: 'width' });

            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'video', field_name: 'width', direction: SortDirection.DESC }
            ]);
        });

        it('selects a metadata field', () => {
            const { handleFieldClick } = useVideoOrderBy({ collectionId: () => 'col1' });

            handleFieldClick({ source: 'metadata', value: 'score', label: 'metadata.score' });

            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'metadata', field_name: 'score', direction: SortDirection.ASC }
            ]);
        });
    });

    describe('toggleDirection', () => {
        it('does nothing when no sort is active', () => {
            const { toggleDirection } = useVideoOrderBy({ collectionId: () => 'col1' });

            toggleDirection();

            expect(updateSortBy).not.toHaveBeenCalled();
        });

        it('toggles direction for a video field', () => {
            videoSortBy.set([
                { source: 'video', field_name: 'file_name', direction: SortDirection.ASC }
            ]);
            const { toggleDirection } = useVideoOrderBy({ collectionId: () => 'col1' });

            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'video', field_name: 'file_name', direction: SortDirection.DESC }
            ]);

            videoSortBy.set([
                { source: 'video', field_name: 'file_name', direction: SortDirection.DESC }
            ]);
            toggleDirection();
            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'video', field_name: 'file_name', direction: SortDirection.ASC }
            ]);
        });

        it('toggles direction for a metadata field', () => {
            videoSortBy.set([
                { source: 'metadata', field_name: 'score', direction: SortDirection.ASC }
            ]);
            const { toggleDirection } = useVideoOrderBy({ collectionId: () => 'col1' });

            toggleDirection();

            expect(updateSortBy).toHaveBeenCalledWith([
                { source: 'metadata', field_name: 'score', direction: SortDirection.DESC }
            ]);
        });
    });
});
