import { render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { getColorByLabel } from '$lib/utils';
import SampleAnnotation from './SampleAnnotation.svelte';

const BASE_ANNOTATION_FIELDS = {
    parent_sample_id: 'parent-sample-1',
    annotation_collection_id: 'collection-1',
    created_at: new Date('1970-01-01T00:00:00.000Z')
} satisfies Pick<
    ComponentProps<typeof SampleAnnotation>['annotation'],
    'parent_sample_id' | 'annotation_collection_id' | 'created_at'
>;

const createSegmentationMaskAnnotation = (): ComponentProps<
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
                annotation: createSegmentationMaskAnnotation(),
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
                annotation: createSegmentationMaskAnnotation(),
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
                annotation: createSegmentationMaskAnnotation(),
                imageWidth: 100,
                showLabel: true
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('person');
    });

    it('appends confidence to the canvas label when confidence is set', () => {
        render(SampleAnnotation, {
            props: {
                annotation: { ...createObjectDetectionAnnotation(), confidence: 0.87 },
                imageWidth: 100,
                showLabel: true
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('car (0.87)');
    });

    it('does not show confidence in the canvas label when confidence is null', () => {
        render(SampleAnnotation, {
            props: {
                annotation: { ...createObjectDetectionAnnotation(), confidence: null },
                imageWidth: 100,
                showLabel: true
            }
        });

        expect(screen.getByTestId('svg-annotation-text')).toHaveTextContent('car');
        expect(screen.getByTestId('svg-annotation-text')).not.toHaveTextContent('(');
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

    describe('coloring by source', () => {
        const { setSelectedCollectionIds, setCollectionIdToName } =
            useAnnotationCollectionsFilter();

        // The factory annotation belongs to 'collection-1' (named "Predictions" below)
        // and has the label 'car'.
        const sourceColor = getColorByLabel('Predictions', 1).color;
        const labelColor = getColorByLabel('car', 1).color;

        afterEach(() => {
            setSelectedCollectionIds([]);
            setCollectionIdToName({});
        });

        it('uses distinct colors for the source and the label', () => {
            // Sanity check so the assertions below are meaningful.
            expect(sourceColor).not.toBe(labelColor);
        });

        it('colors by the source name when colorBySource is true', () => {
            setCollectionIdToName({ 'collection-1': 'Predictions' });

            render(SampleAnnotation, {
                props: {
                    annotation: createObjectDetectionAnnotation(),
                    imageWidth: 100,
                    colorBySource: true
                }
            });

            expect(screen.getByTestId('annotation_box')).toHaveAttribute('stroke', sourceColor);
        });

        it('colors by the label when colorBySource is false, even with multiple sources selected', () => {
            setSelectedCollectionIds(['collection-1', 'collection-2']);
            setCollectionIdToName({ 'collection-1': 'Predictions' });

            render(SampleAnnotation, {
                props: {
                    annotation: createObjectDetectionAnnotation(),
                    imageWidth: 100,
                    colorBySource: false
                }
            });

            expect(screen.getByTestId('annotation_box')).toHaveAttribute('stroke', labelColor);
        });

        it('falls back to the global selection rule when colorBySource is omitted', () => {
            setSelectedCollectionIds(['collection-1', 'collection-2']);
            setCollectionIdToName({ 'collection-1': 'Predictions' });

            render(SampleAnnotation, {
                props: { annotation: createObjectDetectionAnnotation(), imageWidth: 100 }
            });

            expect(screen.getByTestId('annotation_box')).toHaveAttribute('stroke', sourceColor);
        });
    });

    describe('opacity when custom label color is absent', () => {
        const { clearCustomColors, setCustomColor } = useCustomLabelColors();

        afterEach(() => {
            clearCustomColors();
        });

        it('renders bounding-box fill-opacity as a valid number when the label has no custom color', () => {
            render(SampleAnnotation, {
                props: { annotation: createObjectDetectionAnnotation(), imageWidth: 100 }
            });

            const opacity = Number(
                screen.getByTestId('annotation_box').getAttribute('fill-opacity')
            );
            expect(isNaN(opacity)).toBe(false);
            expect(opacity).toBe(0.4);
        });

        it('uses custom alpha for bounding-box fill-opacity when label has a custom color', () => {
            setCustomColor('car', '#ff0000', 0.8);

            render(SampleAnnotation, {
                props: { annotation: createObjectDetectionAnnotation(), imageWidth: 100 }
            });

            const opacity = Number(
                screen.getByTestId('annotation_box').getAttribute('fill-opacity')
            );
            expect(opacity).toBeCloseTo(0.32); // 0.8 * 0.4
        });
    });
});
