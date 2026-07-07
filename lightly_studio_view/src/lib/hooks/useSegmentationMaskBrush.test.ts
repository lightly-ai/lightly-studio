import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import type { AnnotationType, AnnotationView } from '$lib/api/lightly_studio_local';
import type { AnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

import { useSegmentationMaskBrush } from './useSegmentationMaskBrush';
import { useGlobalStorage } from './useGlobalStorage';
import { useReversibleActions } from './useReversibleActions';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { applySegmentationMaskConstraints } from '$lib/utils/segmentationOverlap';
import { toast } from 'svelte-sonner';

const annotationLabelContext: AnnotationLabelContext = {
    isDrawing: true,
    annotationId: null,
    annotationLabel: null,
    annotationSource: null,
    lastCreatedAnnotationId: null,
    annotationType: null
};

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: annotationLabelContext,
        setAnnotationId(id: string | null) {
            annotationLabelContext.annotationId = id;
        },

        setAnnotationLabel(label: string | null) {
            annotationLabelContext.annotationLabel = label;
        },
        setAnnotationSource(source: string | null) {
            annotationLabelContext.annotationSource = source;
        },
        setLastCreatedAnnotationId(id: string | null) {
            annotationLabelContext.lastCreatedAnnotationId = id;
        },
        setIsDrawing(value: boolean) {
            annotationLabelContext.isDrawing = value;
        },
        setAnnotationType(type: AnnotationType | null) {
            annotationLabelContext.annotationType = type;
        }
    })
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    computeBoundingBoxFromMask: vi.fn(),
    encodeBinaryMaskToRLE: vi.fn(),
    getBoundingBox: vi.fn()
}));

vi.mock('$lib/utils/segmentationOverlap', () => ({
    applySegmentationMaskConstraints: vi.fn(async () => [])
}));

const createAnnotation = vi.fn();
const createLabel = vi.fn();
const deleteAnnotation = vi.fn();

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({ createAnnotation })
}));

const updateAnnotations = vi.fn();
vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations })
}));

vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: () => ({ createLabel })
}));

vi.mock('svelte-sonner', () => {
    return {
        toast: {
            error: vi.fn()
        }
    };
});

const bbox = { x: 1, y: 2, width: 10, height: 20 };
const rle = [1, 2, 3];
const mask = new Uint8Array(100);
const datasetId = 'd1';

const sample = { width: 100, height: 100 };

describe('useSegmentationMaskBrush', () => {
    beforeEach(() => {
        useGlobalStorage().clearReversibleActions();
        annotationLabelContext.isDrawing = true;
        annotationLabelContext.annotationId = null;
        annotationLabelContext.annotationLabel = null;
        annotationLabelContext.annotationSource = null;
        annotationLabelContext.lastCreatedAnnotationId = null;

        vi.clearAllMocks();

        vi.mocked(computeBoundingBoxFromMask).mockReturnValue(bbox);
        vi.mocked(encodeBinaryMaskToRLE).mockReturnValue(rle);
        vi.mocked(applySegmentationMaskConstraints).mockResolvedValue([]);

        createAnnotation.mockResolvedValue({
            sample_id: 'new-annotation-id'
        });

        createLabel.mockResolvedValue({
            annotation_label_id: 'new-label-id',
            annotation_label_name: 'car'
        });
    });

    it('does nothing when not drawing', async () => {
        annotationLabelContext.isDrawing = false;

        const refetch = vi.fn();

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, []);

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).not.toHaveBeenCalled();
        expect(annotationLabelContext.isDrawing).toBe(false);
    });

    it('shows toast error when bounding box is invalid', async () => {
        vi.mocked(computeBoundingBoxFromMask).mockReturnValue(null);

        annotationLabelContext.annotationLabel = 'car';

        const refetch = vi.fn();

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, []);

        expect(toast.error).toHaveBeenCalledWith('Invalid segmentation mask');
        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).not.toHaveBeenCalled();
    });

    it('updates an existing annotation when selectedAnnotation is provided', async () => {
        const refetch = vi.fn();
        const updateAnnotation = vi.fn().mockResolvedValue(true);

        annotationLabelContext.annotationId = 'existing-id';

        const selectedAnnotation = {
            sample_id: 'existing-id'
        } as AnnotationView;

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, selectedAnnotation, [], updateAnnotation);

        expect(updateAnnotation).toHaveBeenCalledWith({
            annotation_id: 'existing-id',
            collection_id: 'c1',
            bounding_box: bbox,
            segmentation_mask: rle
        });

        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });

    it('refetches and shows error when selected annotation is locked', async () => {
        const refetch = vi.fn();
        const updateAnnotation = vi.fn();

        const selectedAnnotation = {
            sample_id: 'locked-id'
        } as AnnotationView;

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, selectedAnnotation, [], updateAnnotation, new Set(['locked-id']));

        expect(refetch).toHaveBeenCalledTimes(1);
        expect(toast.error).toHaveBeenCalledWith('This annotation is locked');
        expect(updateAnnotation).not.toHaveBeenCalled();
        expect(createAnnotation).not.toHaveBeenCalled();
    });

    it('does not apply constraints when selected annotation is locked', async () => {
        const refetch = vi.fn();
        const updateAnnotation = vi.fn();
        const selectedAnnotation = {
            sample_id: 'locked-id'
        } as AnnotationView;

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, selectedAnnotation, [], updateAnnotation, new Set(['locked-id']));

        expect(applySegmentationMaskConstraints).not.toHaveBeenCalled();
        expect(updateAnnotation).not.toHaveBeenCalled();
        expect(refetch).toHaveBeenCalledTimes(1);
    });

    it('creates a new annotation using an existing label', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = 'car';

        const labels = [
            {
                annotation_label_id: 'car-label-id',
                annotation_label_name: 'car'
            }
        ];

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, labels);

        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({
                parent_sample_id: 's1',
                annotation_type: 'segmentation_mask',
                segmentation_mask: rle,
                annotation_label_id: 'car-label-id'
            })
        );

        expect(annotationLabelContext.annotationId).toBe('new-annotation-id');
        expect(annotationLabelContext.lastCreatedAnnotationId).toBe('new-annotation-id');
        expect(refetch).toHaveBeenCalled();
    });

    it('shows error and does not create annotation when no label is selected', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = null;

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, []);

        expect(toast.error).toHaveBeenCalledWith(
            'Please select a class before creating an annotation'
        );
        expect(applySegmentationMaskConstraints).not.toHaveBeenCalled();
        expect(createLabel).not.toHaveBeenCalled();
        expect(createAnnotation).not.toHaveBeenCalled();
        expect(refetch).not.toHaveBeenCalled();
    });

    it('sends annotation_collection_name from the selected source in the context', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = 'car';
        annotationLabelContext.annotationSource = 'predictions';

        const labels = [{ annotation_label_id: 'car-label-id', annotation_label_name: 'car' }];

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, labels);

        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_collection_name: 'predictions' })
        );
    });

    it('persists the label chosen via requestLabel (source is owned by the pill)', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = null;
        // The source is chosen separately via the on-canvas pill, not the class dialog.
        annotationLabelContext.annotationSource = 'predictions';

        const requestLabel = vi.fn().mockResolvedValue({ label: 'car' });

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation,
            requestLabel
        });

        await finishBrush(mask, null, []);

        expect(annotationLabelContext.annotationLabel).toBe('car');
        // The label choice is persisted to the session store, keyed by collection id.
        const { lastAnnotationLabel } = useGlobalStorage();
        expect(get(lastAnnotationLabel)['c1']).toBe('car');
        // The collection name still flows from the context source set by the pill.
        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_collection_name: 'predictions' })
        );
    });

    it('omits annotation_collection_name when no source is selected', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = 'car';
        annotationLabelContext.annotationSource = null;

        const labels = [{ annotation_label_id: 'car-label-id', annotation_label_name: 'car' }];

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, labels);

        expect(createAnnotation).toHaveBeenCalledWith(
            expect.objectContaining({ annotation_collection_name: undefined })
        );
    });

    it('creates a new label with the selected name when label does not exist yet', async () => {
        const refetch = vi.fn();

        annotationLabelContext.annotationLabel = 'car';

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, []);

        expect(createLabel).toHaveBeenCalledWith({
            dataset_id: datasetId,
            annotation_label_name: 'car'
        });

        expect(createAnnotation).toHaveBeenCalled();
        expect(refetch).toHaveBeenCalled();
    });

    it('adds a create-annotation undo action to the stack when a new annotation is created with a brush stroke', async () => {
        const { reversibleActions } = useReversibleActions();

        annotationLabelContext.annotationLabel = 'car';
        const refetch = vi.fn();

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, [
            { annotation_label_id: 'car-label-id', annotation_label_name: 'car' }
        ]);

        const actions = get(reversibleActions);
        expect(actions).toHaveLength(1);
        expect(actions[0].groupId).toBe('annotation-create');
        expect(actions[0].description).toBe('Undo create annotation');
    });

    it('places create-annotation undo below stroke-update undo after a second stroke on the newly created annotation', async () => {
        const { reversibleActions } = useReversibleActions();

        annotationLabelContext.annotationLabel = 'car';
        const refetch = vi.fn();
        const updateAnnotation = vi.fn().mockResolvedValue(undefined);

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        // First stroke: creates the annotation (no selected annotation)
        await finishBrush(mask, null, [
            { annotation_label_id: 'car-label-id', annotation_label_name: 'car' }
        ]);

        // Simulate the user starting a new stroke (onpointerdown sets isDrawing back to true)
        annotationLabelContext.isDrawing = true;

        // Second stroke: updates the newly created annotation
        const createdAnnotation = {
            sample_id: 'new-annotation-id',
            annotation_type: 'segmentation_mask',
            segmentation_details: {
                segmentation_mask: [1, 2, 3]
            }
        } as AnnotationView;
        await finishBrush(
            mask,
            createdAnnotation,
            [{ annotation_label_id: 'car-label-id', annotation_label_name: 'car' }],
            updateAnnotation
        );

        const actions = get(reversibleActions);
        expect(actions).toHaveLength(2);
        // Most recent action (update stroke) must be first so it is undone first
        expect(actions[0].groupId).toBe('bbox-change-annotation-details');
        // Annotation creation must be second so it is undone after all strokes are reverted
        expect(actions[1].groupId).toBe('annotation-create');
    });

    it('calls deleteAnnotation with the annotation id when the create undo action is executed', async () => {
        const { reversibleActions, executeReversibleAction } = useReversibleActions();

        annotationLabelContext.annotationLabel = 'car';
        const refetch = vi.fn();
        deleteAnnotation.mockResolvedValue(undefined);

        const { finishBrush } = useSegmentationMaskBrush({
            collectionId: 'c1',
            datasetId,
            sampleId: 's1',
            sample,
            refetch,
            deleteAnnotation
        });

        await finishBrush(mask, null, [
            { annotation_label_id: 'car-label-id', annotation_label_name: 'car' }
        ]);

        // After creating the annotation, annotationId is set to the new annotation's id.
        expect(annotationLabelContext.annotationId).toBe('new-annotation-id');

        const actions = get(reversibleActions);
        await executeReversibleAction(actions[0].id);

        expect(deleteAnnotation).toHaveBeenCalledWith('new-annotation-id');
        expect(get(reversibleActions)).toHaveLength(0);
        expect(annotationLabelContext.annotationId).toBeNull();
    });
});
