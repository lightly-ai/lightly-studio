import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import type { AnnotationDetailsWithPayloadView } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import AnnotationDetails from './AnnotationDetails.svelte';

vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'dataset-1' } } }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('../SampleDetails/SampleDetailsPanel.svelte', async () => ({
    default: (await import('./SampleDetailsPanelStub.test.svelte')).default
}));

const annotationDetails = {
    annotation: {
        sample_id: 'a1',
        parent_sample_id: 'image-1',
        annotation_label: { annotation_label_name: 'deer' }
    }
} as unknown as AnnotationDetailsWithPayloadView;

describe('AnnotationDetails', () => {
    it('does not make the viewed class the class for new annotations', () => {
        const { lastAnnotationLabel, updateLastAnnotationLabel } = useGlobalStorage();
        updateLastAnnotationLabel('col-1', 'fox');

        render(AnnotationDetails, {
            props: {
                annotationDetails,
                parentSample: { width: 10, height: 10, url: '/image.jpg' },
                parentSampleDetails: createRawSnippet(() => ({ render: () => '<div></div>' })),
                updateAnnotation: vi.fn(),
                refetch: vi.fn(),
                collectionId: 'col-1',
                collectionDatasetId: 'dataset-1'
            }
        });

        expect(screen.getByTestId('sample-details-panel-stub')).toBeInTheDocument();
        expect(get(lastAnnotationLabel)['col-1']).toBe('fox');
    });
});
