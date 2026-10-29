import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import ExportScope from './ExportScope.svelte';

const imageFilter = writable<unknown>(null);
const filteredSampleCount = writable(0);
const tags = writable<Record<string, { tag_id: string; name: string }[]>>({});

vi.mock('$lib/hooks', () => ({
    useImageFilters: () => ({ imageFilter }),
    useVideoFilters: () => ({ videoFilter: writable(null) }),
    useGlobalStorage: () => ({ filteredSampleCount, tags })
}));

describe('ExportScope', () => {
    it('names the filtered tag', () => {
        filteredSampleCount.set(3);
        tags.set({ 'col-1': [{ tag_id: 'tag-1', name: 'to_label' }] });
        imageFilter.set({ filter_type: 'image', sample_filter: { tag_ids: ['tag-1'] } });

        render(ExportScope, { props: { collectionId: 'col-1', sampleType: 'image' } });

        expect(
            screen.getByText('Exports the 3 images matching your current filters in tag to_label.')
        ).toBeInTheDocument();
        expect(screen.queryByText(/To export one tag/)).not.toBeInTheDocument();
    });
});
