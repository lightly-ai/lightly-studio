import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationClassVisibility } from '$lib/hooks';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
import AnnotationItem from './AnnotationItem.svelte';

vi.mock('$lib/components', async () => {
    const module = await import('./AnnotationCanvas.mock.svelte');
    return { AnnotationCanvas: module.default };
});

const createSegmentationAnnotation = (): AnnotationView =>
    ({
        sample_id: 'annotation-1',
        annotation_type: 'segmentation_mask',
        annotation_label: { annotation_label_name: 'car' },
        segmentation_details: {
            x: 100,
            y: 200,
            width: 400,
            height: 200,
            segmentation_mask: [0, 1]
        }
    }) as AnnotationView;

const defaultProps = {
    annotation: createSegmentationAnnotation(),
    containerWidth: 200,
    containerHeight: 100,
    showLabel: false,
    sample: { width: 1000, height: 800, url: '/image.jpg' }
};

describe('AnnotationItem', () => {
    beforeEach(() => {
        useAnnotationClassVisibility().hiddenClassNamesStore.set([]);
        useHideAnnotations().isHidden.set(false);
        useCustomLabelColors().clearCustomColors();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('passes the padded annotation crop and tile dimensions to the canvas', () => {
        render(AnnotationItem, { props: defaultProps });

        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-source-crop',
            JSON.stringify({ x: 80, y: 180, width: 440, height: 240 })
        );
        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-output-width',
            '200'
        );
        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-output-height',
            '100'
        );
        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-object-fit',
            'contain'
        );
    });

    it('keeps the custom segmentation color and alpha independent', () => {
        useCustomLabelColors().setCustomColor('car', '#123456', 0.65);

        render(AnnotationItem, { props: { ...defaultProps, showLabel: true } });

        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-color',
            'rgba(18, 52, 86, 0.26)'
        );
        expect(screen.getByTestId('mock-annotation-canvas')).toHaveAttribute(
            'data-opacity',
            '0.65'
        );
        expect(screen.getByText('car').parentElement).toHaveStyle({
            backgroundColor: 'rgba(18, 52, 86, 0.26)'
        });
    });

    it('hides annotations when their class is hidden', () => {
        useAnnotationClassVisibility().hiddenClassNamesStore.set(['car']);

        const { container } = render(AnnotationItem, { props: defaultProps });

        expect(screen.getByTestId('mock-annotation-canvas').parentElement).toHaveClass('invisible');
        expect(container.querySelector('.annotation-box')).toHaveClass('invisible');
    });
});
