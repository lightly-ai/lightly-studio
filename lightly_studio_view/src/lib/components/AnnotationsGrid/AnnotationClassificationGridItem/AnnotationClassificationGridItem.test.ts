import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { tick } from 'svelte';
import {
    SampleType,
    AnnotationType,
    type AnnotationWithPayloadView,
    type ImageAnnotationView,
    type VideoFrameAnnotationView,
    type AnnotationView
} from '$lib/api/lightly_studio_local';
import AnnotationClassificationGridItem from './AnnotationClassificationGridItem.svelte';

vi.mock('$lib/components/SampleClassificationPills/SampleClassificationPills.svelte', async () => {
    const module = await import('./SampleClassificationPills.mock.svelte');
    return { default: module.default };
});

vi.mock('$lib/utils', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils')>();
    return {
        ...actual,
        getGridImageURL: ({ sampleId }: { sampleId: string }) => `http://images/sample/${sampleId}`,
        getGridFrameURL: ({ sampleId }: { sampleId: string }) => `http://frames/media/${sampleId}`
    };
});

function buildAnnotation(
    overrides: Partial<AnnotationWithPayloadView> = {}
): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: 'ann-1',
            annotation_type: AnnotationType.CLASSIFICATION,
            annotation_label: { annotation_label_name: 'cat' },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-1'
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-1',
            width: 800,
            height: 600
        } as unknown as ImageAnnotationView,
        ...overrides
    };
}

const defaultProps = {
    containerWidth: 200,
    containerHeight: 150,
    showLabel: true,
    cachedCollectionVersion: 'v1'
};

function renderItem(annotation: AnnotationWithPayloadView, props: Record<string, unknown> = {}) {
    return render(AnnotationClassificationGridItem, {
        props: { annotation, ...defaultProps, ...props }
    });
}

describe('AnnotationClassificationGridItem', () => {
    it('renders thumbnail div and SampleClassificationPills for an image annotation', async () => {
        const { container } = renderItem(buildAnnotation());

        await tick();

        const thumbnail = container.firstElementChild as HTMLElement;
        expect(thumbnail).toBeInTheDocument();
        expect(thumbnail.style.backgroundImage).toContain('img-1');
        expect(screen.getByTestId('mock-classification-pills')).toBeInTheDocument();
    });

    it('renders thumbnail using frame URL for a video frame annotation', async () => {
        const annotation = buildAnnotation({
            parent_sample_type: SampleType.VIDEO_FRAME,
            parent_sample_data: {
                sample_id: 'frame-1',
                video: { width: 1920, height: 1080, file_path_abs: '/video.mp4' }
            } as unknown as VideoFrameAnnotationView
        });
        const { container } = renderItem(annotation);

        await tick();

        const thumbnail = container.firstElementChild as HTMLElement;
        expect(thumbnail.style.backgroundImage).toContain('frames/media/frame-1');
    });

    it('applies grid-item-selected class when selected is true', () => {
        const { container } = renderItem(buildAnnotation(), { selected: true });

        expect(container.firstElementChild).toHaveAttribute('aria-selected', 'true');
    });

    it('hides SampleClassificationPills when showLabel is false', () => {
        renderItem(buildAnnotation(), { showLabel: false });

        expect(screen.queryByTestId('mock-classification-pills')).not.toBeInTheDocument();
    });

    it('passes only the single annotation to SampleClassificationPills', async () => {
        renderItem(buildAnnotation());

        await tick();

        const pills = screen.getByTestId('mock-classification-pills');
        // Exactly one annotation is passed — not all sibling labels for the parent sample.
        expect(pills).toHaveAttribute('data-annotation-count', '1');
        expect(pills).toHaveAttribute('data-annotation-id', 'ann-1');
    });

    it('calls onCropWindowChange with a full-image CropWindow (windowX/Y=0) once URL is available', async () => {
        const onCropWindowChange = vi.fn();
        const annotation = buildAnnotation({
            parent_sample_data: {
                sample_id: 'img-1',
                width: 1024,
                height: 768
            } as unknown as ImageAnnotationView
        });

        renderItem(annotation, { onCropWindowChange });

        await tick();

        expect(onCropWindowChange).toHaveBeenCalledOnce();
        const [annotationId, cropWindow] = onCropWindowChange.mock.calls[0];
        expect(annotationId).toBe('ann-1');
        expect(cropWindow.windowX).toBe(0);
        expect(cropWindow.windowY).toBe(0);
        expect(cropWindow.windowWidth).toBe(1024);
        expect(cropWindow.windowHeight).toBe(768);
        expect(cropWindow.sampleWidth).toBe(1024);
        expect(cropWindow.sampleHeight).toBe(768);
    });

    it('calls onCropWindowChange with null on unmount', async () => {
        const onCropWindowChange = vi.fn();

        const { unmount } = renderItem(buildAnnotation(), { onCropWindowChange });

        await tick();
        unmount();
        await tick();

        const lastCall = onCropWindowChange.mock.calls.at(-1);
        expect(lastCall?.[0]).toBe('ann-1');
        expect(lastCall?.[1]).toBeNull();
    });
});
