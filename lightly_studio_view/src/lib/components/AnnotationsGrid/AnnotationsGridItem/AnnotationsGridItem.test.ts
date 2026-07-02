import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import {
    SampleType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView
} from '$lib/api/lightly_studio_local';
import { getSimilarityColor } from '$lib/utils';
import AnnotationsGridItem from './AnnotationsGridItem.svelte';

// Stub the heavy child components so the test exercises only the dispatch and
// similarity-badge logic that lives in AnnotationsGridItem itself.
vi.mock('../AnnotationImageGridItem/AnnotationImageGridItem.svelte', async () => {
    const module = await import('./AnnotationImageGridItem.mock.svelte');
    return { default: module.default };
});

vi.mock('../AnnotationVideoFrameGridItem/AnnotationVideoFrameGridItem.svelte', async () => {
    const module = await import('./AnnotationVideoFrameGridItem.mock.svelte');
    return { default: module.default };
});

const imageData = { sample_id: 'image-sample-1' } as unknown as ImageAnnotationView;
const videoFrameData = { sample_id: 'video-sample-1' } as unknown as VideoFrameAnnotationView;

function buildAnnotation(
    overrides: Partial<AnnotationWithPayloadView> = {}
): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {} as AnnotationWithPayloadView['annotation'],
        parent_sample_data: imageData,
        ...overrides
    };
}

function renderItem(annotation: AnnotationWithPayloadView, props = {}) {
    return render(AnnotationsGridItem, {
        props: {
            annotation,
            width: 200,
            height: 150,
            cachedCollectionVersion: 'v1',
            showLabel: true,
            ...props
        }
    });
}

describe('AnnotationsGridItem', () => {
    it('renders the image grid item for an image parent sample', () => {
        renderItem(buildAnnotation({ parent_sample_type: SampleType.IMAGE }));

        expect(screen.getByTestId('mock-image-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-video-grid-item')).not.toBeInTheDocument();
    });

    it('renders the video frame grid item for a video frame parent sample', () => {
        renderItem(
            buildAnnotation({
                parent_sample_type: SampleType.VIDEO_FRAME,
                parent_sample_data: videoFrameData
            })
        );

        expect(screen.getByTestId('mock-video-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-image-grid-item')).not.toBeInTheDocument();
    });

    it('renders the video frame grid item for a video parent sample', () => {
        renderItem(
            buildAnnotation({
                parent_sample_type: SampleType.VIDEO,
                parent_sample_data: videoFrameData
            })
        );

        expect(screen.getByTestId('mock-video-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-image-grid-item')).not.toBeInTheDocument();
    });

    it('renders neither child for an unsupported parent sample type', () => {
        renderItem(buildAnnotation({ parent_sample_type: SampleType.ANNOTATION }));

        expect(screen.queryByTestId('mock-image-grid-item')).not.toBeInTheDocument();
        expect(screen.queryByTestId('mock-video-grid-item')).not.toBeInTheDocument();
    });

    it('forwards dimensions, label, selection and payload to the image child', () => {
        renderItem(buildAnnotation({ parent_sample_type: SampleType.IMAGE }), {
            showLabel: false,
            selected: true
        });

        const child = screen.getByTestId('mock-image-grid-item');
        expect(child).toHaveAttribute('data-sample-id', 'image-sample-1');
        expect(child).toHaveAttribute('data-container-width', '200');
        expect(child).toHaveAttribute('data-container-height', '150');
        expect(child).toHaveAttribute('data-cached-version', 'v1');
        expect(child).toHaveAttribute('data-show-label', 'false');
        expect(child).toHaveAttribute('data-selected', 'true');
    });

    it('forwards dimensions, label and selection to the video child', () => {
        renderItem(
            buildAnnotation({
                parent_sample_type: SampleType.VIDEO_FRAME,
                parent_sample_data: videoFrameData
            }),
            { showLabel: false, selected: true }
        );

        const child = screen.getByTestId('mock-video-grid-item');
        expect(child).toHaveAttribute('data-sample-id', 'video-sample-1');
        expect(child).toHaveAttribute('data-container-width', '200');
        expect(child).toHaveAttribute('data-container-height', '150');
        expect(child).toHaveAttribute('data-show-label', 'false');
        expect(child).toHaveAttribute('data-selected', 'true');
    });

    it('shows the similarity badge with a two-decimal score and matching color', () => {
        const { container } = renderItem(buildAnnotation({ similarity_score: 0.956 }));

        expect(screen.getByText('0.96')).toBeInTheDocument();
        const dot = container.querySelector('span[style*="background-color"]');
        expect(dot).not.toBeNull();
        expect(dot).toHaveStyle({ backgroundColor: getSimilarityColor(0.956) });
    });

    it('shows the similarity badge for a zero score', () => {
        renderItem(buildAnnotation({ similarity_score: 0 }));

        expect(screen.getByText('0.00')).toBeInTheDocument();
    });

    it('hides the similarity badge when the score is undefined', () => {
        const { container } = renderItem(buildAnnotation({ similarity_score: undefined }));

        expect(container.querySelector('span[style*="background-color"]')).toBeNull();
    });

    it('hides the similarity badge when the score is null', () => {
        const { container } = renderItem(buildAnnotation({ similarity_score: null }));

        expect(container.querySelector('span[style*="background-color"]')).toBeNull();
    });
});
