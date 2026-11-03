import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import ExportScope from './ExportScope.svelte';

const imageFilter = writable<unknown>(null);
const filteredSampleCount = writable(0);
const tags = writable<Record<string, { tag_id: string; name: string }[]>>({});

vi.mock('$lib/hooks', () => ({
    useAnnotationCollections: () => ({
        data: [
            { collection_id: 'source-gt', name: 'ground_truth' },
            { collection_id: 'source-v1', name: 'model_v1' }
        ]
    }),
    useAnnotationLabels: () => ({
        data: [
            { annotation_label_id: 'deer-id', annotation_label_name: 'deer' },
            { annotation_label_id: 'raccoon-id', annotation_label_name: 'raccoon' }
        ]
    }),
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

    it('names the ticked source and class pairs', () => {
        filteredSampleCount.set(4);
        imageFilter.set({
            filter_type: 'image',
            sample_filter: {
                annotations_filter: {
                    filter_type: 'annotations',
                    source_label_pairs: [
                        { collection_id: 'source-gt', annotation_label_id: 'deer-id' },
                        { collection_id: 'source-v1', annotation_label_id: 'raccoon-id' }
                    ]
                }
            }
        });

        render(ExportScope, { props: { collectionId: 'col-1', sampleType: 'image' } });

        expect(
            screen.getByText(
                'Exports the 4 images matching your current filters, with deer in ground_truth, raccoon in model_v1.'
            )
        ).toBeInTheDocument();
    });
});
