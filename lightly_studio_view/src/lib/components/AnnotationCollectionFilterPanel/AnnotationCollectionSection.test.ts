import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import AnnotationCollectionSection from './AnnotationCollectionSection.svelte';

const mocks = vi.hoisted(() => ({
    labels: [
        { annotation_label_id: 'label-1', annotation_label_name: 'Car' },
        { annotation_label_id: 'label-2', annotation_label_name: 'Road' }
    ],
    counts: [
        {
            annotation_collection_id: 'annotation-collection-1',
            label_name: 'Car',
            current_count: 1,
            total_count: 3
        },
        {
            annotation_collection_id: 'annotation-collection-1',
            label_name: 'Road',
            current_count: 1,
            total_count: 2
        }
    ]
}));

vi.mock('@tanstack/svelte-query', () => {
    return {
        createQuery: vi.fn(() => ({ data: mocks.labels, isSuccess: true }))
    };
});

vi.mock('$lib/hooks/useAnnotationCollectionsLabelFilter/useAnnotationCollectionsLabelFilter', () => ({
    useAnnotationCollectionsLabelFilter: vi.fn(() => ({
        annotationFilter: readable(undefined),
        toggleCollection: vi.fn(),
        toggleLabel: vi.fn(),
        selectedLabels: readable(
            new Map([
                ['annotation-collection-1', new Set(['label-1', 'label-2'])]
            ])
        ),
        allAvailableLabels: readable(
            new Map([
                ['annotation-collection-1', ['label-1', 'label-2']]
            ])
        ),
        selectedCollectionIds: readable(['annotation-collection-1']),
        getCollectionCheckState: vi.fn(() => 'all')
    }))
}));

describe('AnnotationCollectionSection', () => {
    it('renders collection and label counts', async () => {
        const onLabelsLoaded = vi.fn();
        render(AnnotationCollectionSection, {
            props: {
                collection: {
                    collection_id: 'annotation-collection-1',
                    name: 'Vehicles'
                },
                countsByCollectionLabelKey: new Map(
                    mocks.counts.map((count) => [
                        `${count.annotation_collection_id}:${count.label_name}`,
                        count
                    ])
                ),
                onLabelsLoaded
            }
        });

        expect(screen.getByText('2 of 5')).toBeInTheDocument();

        await screen.getByText('Vehicles').click();

        expect(await screen.findByText('1 of 3')).toBeInTheDocument();
        expect(screen.getByText('1 of 2')).toBeInTheDocument();
        expect(onLabelsLoaded).toHaveBeenCalledWith('annotation-collection-1', mocks.labels);
    });
});
