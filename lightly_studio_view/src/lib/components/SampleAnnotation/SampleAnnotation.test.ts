import { render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import SampleAnnotation from './SampleAnnotation.svelte';

const BASE_ANNOTATION_FIELDS = {
    parent_sample_id: 'parent-sample-1',
    created_at: new Date('1970-01-01T00:00:00.000Z')
} satisfies Pick<
    ComponentProps<typeof SampleAnnotation>['annotation'],
    'parent_sample_id' | 'created_at'
>;

const createInstanceSegmentationAnnotation = (): ComponentProps<
    typeof SampleAnnotation
>['annotation'] =>
    ({
        ...BASE_ANNOTATION_FIELDS,
        sample_id: 'instance-segmentation-1',
        annotation_type: 'segmentation_mask',
        annotation_label: { annotation_label_name: 'person' },
        segmentation_details: {
            x: 1,
            y: 2,
            width: 10,
            height: 12
        }
    }) satisfies ComponentProps<typeof SampleAnnotation>['annotation'];

const createObjectDetectionAnnotation = (): ComponentProps<typeof SampleAnnotation>['annotation'] =>
    ({
        ...BASE_ANNOTATION_FIELDS,
        sample_id: 'object-detection-1',
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: 'car' },
        object_detection_details: {
            x: 1,
            y: 2,
            width: 10,
            height: 12
        }
    }) satisfies ComponentProps<typeof SampleAnnotation>['annotation'];

describe('SampleAnnotation', () => {
    let originalGetBBox: PropertyDescriptor | undefined;

    beforeEach(() => {
        originalGetBBox = Object.getOwnPropertyDescriptor(SVGElement.prototype, 'getBBox');
        Object.defineProperty(SVGElement.prototype, 'getBBox', {
            configurable: true,
            value: () => ({ x: 0, y: 0, width: 30, height: 12 })
        });
    });

    afterEach(() => {
        if (originalGetBBox !== undefined) {
            Object.defineProperty(SVGElement.prototype, 'getBBox', originalGetBBox);
            return;
        }

        Reflect.deleteProperty(SVGElement.prototype, 'getBBox');
    });

    it('hides instance-segmentation label when bounding boxes are hidden', () => {
        render(SampleAnnotation, {
            props: {
                annotation: createInstanceSegmentationAnnotation(),
                imageWidth: 100,
                showLabel: true,
                showBoundingBox: false
            }
        });

        expect(screen.queryByTestId('svg-annotation-text')).not.toBeInTheDocument();
    });

    it('shows instance-segmentation label when bounding boxes are shown', () => {
        render(SampleAnnotation, {
            props: {
                annotation: createInstanceSegmentationAnnotation(),
                imageWidth: 100,
                showLabel: true,
                showBoundingBox: true
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('person');
    });

    it('shows instance-segmentation label when bounding-box visibility is omitted', () => {
        render(SampleAnnotation, {
            props: {
                annotation: createInstanceSegmentationAnnotation(),
                imageWidth: 100,
                showLabel: true
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('person');
    });

    it('keeps object-detection label visible when bounding boxes are hidden', () => {
        render(SampleAnnotation, {
            props: {
                annotation: createObjectDetectionAnnotation(),
                imageWidth: 100,
                showLabel: true,
                showBoundingBox: false
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('car');
    });
});
