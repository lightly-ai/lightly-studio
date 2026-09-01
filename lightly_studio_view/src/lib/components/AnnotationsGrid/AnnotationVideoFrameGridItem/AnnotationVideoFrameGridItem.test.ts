import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import type { AnnotationView, VideoFrameAnnotationView } from '$lib/api/lightly_studio_local';
import AnnotationVideoFrameGridItem from './AnnotationVideoFrameGridItem.svelte';

vi.mock('$lib/components', async () => {
    const module = await import('../AnnotationItem/AnnotationCanvas.mock.svelte');
    return { AnnotationCanvas: module.default };
});

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return {
        useSettings: () => ({
            gridViewThumbnailQualityStore: writable('raw'),
            settingsStore: writable({})
        })
    };
});

vi.mock('$lib/utils', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/utils')>();
    return {
        ...actual,
        getGridFrameURL: ({ sampleId }: { sampleId: string }) => `http://frames/media/${sampleId}`
    };
});

function buildAnnotation(orderValue?: number | null): AnnotationView {
    return {
        sample_id: 'ann-1',
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: 'cat' },
        object_detection_details: { x: 10, y: 20, width: 100, height: 50 },
        order_value: orderValue
    } as unknown as AnnotationView;
}

const defaultProps = {
    videoFrame: {
        sample_id: 'frame-1',
        video: { width: 1920, height: 1080 }
    } as unknown as VideoFrameAnnotationView,
    containerWidth: 200,
    containerHeight: 150,
    showLabel: false
};

describe('AnnotationVideoFrameGridItem', () => {
    it('shows the sort value badge when the annotation has an order value', () => {
        render(AnnotationVideoFrameGridItem, {
            props: { ...defaultProps, annotation: buildAnnotation(0.75) }
        });

        expect(screen.getByText('0.75')).toBeInTheDocument();
    });

    it('renders no sort value badge when the order value is null', () => {
        const { container } = render(AnnotationVideoFrameGridItem, {
            props: { ...defaultProps, annotation: buildAnnotation(null) }
        });

        expect(container.textContent?.trim()).toBe('');
    });
});
