import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { describe, expect, it, vi } from 'vitest';
import {
    AnnotationType,
    SampleType,
    type AnnotationWithPayloadView
} from '$lib/api/lightly_studio_local';
import AnnotationClassificationGridItem from './AnnotationClassificationGridItem.svelte';

vi.mock('$lib/components/SampleClassificationPills/SampleClassificationPills.svelte', async () => {
    const module = await import('./SampleClassificationPills.mock.svelte');
    return { default: module.default };
});

describe('AnnotationClassificationGridItem', () => {
    it('renders an image thumbnail and forwards the single annotation to the pills component', () => {
        const annotation: AnnotationWithPayloadView = {
            parent_sample_type: SampleType.IMAGE,
            parent_sample_data: {
                sample_id: 'image-parent-1'
            } as AnnotationWithPayloadView['parent_sample_data'],
            annotation: {
                parent_sample_id: 'parent-image-1',
                sample_id: 'annotation-1',
                annotation_type: AnnotationType.CLASSIFICATION
            } as AnnotationWithPayloadView['annotation']
        };

        const { container } = render(AnnotationClassificationGridItem, {
            props: {
                annotation,
                containerWidth: 240,
                containerHeight: 180,
                cachedCollectionVersion: 'v1'
            }
        });

        const thumbnail = screen.getByTestId('classification-grid-item');
        expect(thumbnail).toBeInTheDocument();
        expect(container.firstElementChild).toHaveStyle({
            backgroundImage: expect.stringContaining('sample/image-parent-1')
        });
        expect(screen.getByTestId('mock-sample-classification-pills')).toHaveAttribute(
            'data-annotation-count',
            '1'
        );
        expect(screen.getByTestId('mock-sample-classification-pills')).toHaveAttribute(
            'data-annotation-ids',
            'annotation-1'
        );
    });

    it('renders a frame thumbnail for video frame samples', () => {
        const annotation: AnnotationWithPayloadView = {
            parent_sample_type: SampleType.VIDEO_FRAME,
            parent_sample_data: {
                sample_id: 'frame-parent-1'
            } as AnnotationWithPayloadView['parent_sample_data'],
            annotation: {
                parent_sample_id: 'parent-frame-1',
                sample_id: 'annotation-1',
                annotation_type: AnnotationType.CLASSIFICATION
            } as AnnotationWithPayloadView['annotation']
        };

        render(AnnotationClassificationGridItem, {
            props: {
                annotation,
                containerWidth: 200,
                containerHeight: 120
            }
        });

        expect(screen.getByTestId('classification-grid-item')).toHaveStyle({
            backgroundImage: expect.stringContaining('frame-parent-1')
        });
    });

    it('renders the selection indicator when selected', () => {
        const annotation: AnnotationWithPayloadView = {
            parent_sample_type: SampleType.IMAGE,
            parent_sample_data: {
                sample_id: 'image-parent-1'
            } as AnnotationWithPayloadView['parent_sample_data'],
            annotation: {
                parent_sample_id: 'parent-image-1',
                sample_id: 'annotation-1',
                annotation_type: AnnotationType.CLASSIFICATION
            } as AnnotationWithPayloadView['annotation']
        };

        render(AnnotationClassificationGridItem, {
            props: {
                annotation,
                containerWidth: 240,
                containerHeight: 180,
                selected: true
            }
        });

        expect(screen.getByTestId('sample-selected-box')).toBeInTheDocument();
    });
});
