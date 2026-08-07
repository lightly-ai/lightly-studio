import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import {
    AnnotationType,
    SampleType,
    type AnnotationView,
    type AnnotationWithPayloadView,
    type ImageAnnotationView
} from '$lib/api/lightly_studio_local';
import AnnotationTile from './AnnotationTile.svelte';

vi.mock('$lib/components/GridItem', async () => {
    const { default: MockGridItem } = await import('../../GridItem/GridItem.mock.svelte');
    return { GridItem: MockGridItem };
});

vi.mock('$lib/components', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/components')>();
    const { default: MockAnnotationsGridItem } =
        await import('../AnnotationsGridItem/AnnotationsGridItem.mock.svelte');
    const { default: MockSelectableBox } =
        await import('../../SelectableBox/SelectableBox.mock.svelte');
    return {
        ...actual,
        AnnotationsGridItem: MockAnnotationsGridItem,
        SelectableBox: MockSelectableBox
    };
});

vi.mock('../AnnotationClassificationGridItem/AnnotationClassificationGridItem.svelte', async () => {
    const { default: MockClassification } =
        await import('../AnnotationClassificationGridItem/AnnotationClassificationGridItem.mock.svelte');
    return { default: MockClassification };
});

function buildClassificationAnnotation(id: string): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: id,
            annotation_type: AnnotationType.CLASSIFICATION,
            annotation_label: { annotation_label_name: 'cat' },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-1'
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-1',
            width: 800,
            height: 600
        } as unknown as ImageAnnotationView
    };
}

function buildOdAnnotation(id: string): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: id,
            annotation_type: AnnotationType.OBJECT_DETECTION,
            annotation_label: { annotation_label_name: 'dog' },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-2',
            object_detection_details: { x: 0, y: 0, width: 100, height: 100 }
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-2',
            width: 640,
            height: 480
        } as unknown as ImageAnnotationView
    };
}

const defaultProps = {
    index: 0,
    width: 200,
    height: 200,
    selected: false,
    showLabel: true,
    cachedCollectionVersion: 'v1',
    canShowSelectionOverlay: true,
    cropWindow: undefined,
    cropUrl: undefined,
    onCropWindowChange: vi.fn(),
    onDragStart: vi.fn(),
    onSelect: vi.fn(),
    onDoubleClick: vi.fn()
};

describe('AnnotationTile', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders AnnotationClassificationGridItem for a classification annotation', () => {
        render(AnnotationTile, {
            props: { ...defaultProps, annotation: buildClassificationAnnotation('cls-1') }
        });

        expect(screen.getByTestId('mock-classification-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-annotations-grid-item')).not.toBeInTheDocument();
    });

    it('renders AnnotationsGridItem for an OD annotation', () => {
        render(AnnotationTile, {
            props: { ...defaultProps, annotation: buildOdAnnotation('od-1') }
        });

        expect(screen.getByTestId('mock-annotations-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-classification-grid-item')).not.toBeInTheDocument();
    });

    it('sets the annotation id and index data attributes on the tile', () => {
        const { container } = render(AnnotationTile, {
            props: { ...defaultProps, index: 3, annotation: buildClassificationAnnotation('cls-1') }
        });

        const tile = container.querySelector('.annotation-grid-item');
        expect(tile).toHaveAttribute('data-annotation-id', 'cls-1');
        expect(tile).toHaveAttribute('data-annotation-index', '3');
        expect(tile).toHaveAttribute('data-sample-id', 'img-1');
    });

    it('shows the selection overlay only when selected and allowed', () => {
        render(AnnotationTile, {
            props: {
                ...defaultProps,
                selected: true,
                canShowSelectionOverlay: true,
                annotation: buildClassificationAnnotation('cls-1')
            }
        });

        expect(screen.getByTestId('mock-selectable-box')).toBeInTheDocument();
    });

    it('hides the selection overlay when the user is not allowed to see it', () => {
        render(AnnotationTile, {
            props: {
                ...defaultProps,
                selected: true,
                canShowSelectionOverlay: false,
                annotation: buildClassificationAnnotation('cls-1')
            }
        });

        expect(screen.queryByTestId('mock-selectable-box')).not.toBeInTheDocument();
    });

    it('calls onSelect with the annotation id and index when the tile is clicked', async () => {
        const onSelect = vi.fn();
        render(AnnotationTile, {
            props: {
                ...defaultProps,
                index: 2,
                onSelect,
                annotation: buildClassificationAnnotation('cls-1')
            }
        });

        await fireEvent.click(screen.getByTestId('annotation-grid-item'));

        expect(onSelect).toHaveBeenCalledWith(expect.anything(), 'cls-1', 2);
    });
});
