import { render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { beforeEach, describe, expect, it } from 'vitest';
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
        annotation_type: 'instance_segmentation',
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
    beforeEach(() => {
        Object.defineProperty(SVGElement.prototype, 'getBBox', {
            configurable: true,
            value: () => ({ x: 0, y: 0, width: 30, height: 12 })
        });
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
