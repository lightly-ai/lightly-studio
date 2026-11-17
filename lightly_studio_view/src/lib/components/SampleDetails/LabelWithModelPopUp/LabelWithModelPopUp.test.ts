import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import type { LabelingModelView, ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import LabelWithModelPopUp from './LabelWithModelPopUp.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

type LabelWithModel = ComponentProps<typeof LabelWithModelPopUp>['labelWithModel'];

const DETECTION_MODEL: LabelingModelView = {
    id: 'ltdetrv2-s-coco',
    task: 'object_detection',
    class_names: ['cat']
};
const SEGMENTATION_MODEL: LabelingModelView = {
    id: 'ltdetrv2-seg-s-coco',
    task: 'instance_segmentation',
    class_names: ['cat']
};
const PREVIEW: ModelAnnotationPreview = {
    class_name: 'cat',
    bbox: { x: 0, y: 0, width: 1, height: 1 },
    segmentation_mask: null,
    score: 0.9
};

const makeLabelWithModel = (overrides: Partial<LabelWithModel> = {}): LabelWithModel => ({
    review: {
        suggestions: (overrides.predictions ?? []).map((preview, id) => ({
            id,
            preview,
            box: { ...preview.bbox },
            status: 'accepted'
        })),
        acceptedSuggestions: (overrides.predictions ?? []).map((preview, id) => ({
            id,
            preview,
            box: { ...preview.bbox },
            status: 'accepted'
        })),
        hideAccepted: false,
        setHideAccepted: vi.fn(),
        isVisible: () => true,
        undo: vi.fn(),
        focusedId: null,
        focusedSuggestion: undefined,
        focus: vi.fn(),
        accept: vi.fn(),
        reject: vi.fn(),
        acceptAll: vi.fn(),
        updateBox: vi.fn(),
        pendingCount: 0,
        hasUnsavedSuggestions: true,
        changeClass: vi.fn(),
        replace: vi.fn(),
        remove: vi.fn()
    },
    generationError: null,
    needsRegeneration: false,
    annotationSource: 'review',
    annotationSourceBlockedReason: null,
    pendingChange: null,
    requestChange: vi.fn((action: () => void) => action()),
    confirmChange: vi.fn(),
    cancelChange: vi.fn(),
    predictions: [],
    hasUnsavedSuggestions: false,
    isGenerating: false,
    isEmptyResult: false,
    isSaving: false,
    canSave: false,
    canGenerate: true,
    generate: vi.fn(),
    clear: vi.fn(),
    save: vi.fn(),
    ...overrides
});

const defaultProps = {
    collectionId: 'collection-1',
    models: [DETECTION_MODEL, SEGMENTATION_MODEL],
    model: DETECTION_MODEL,
    onModelChange: vi.fn(),
    threshold: 0.5,
    onThresholdChange: vi.fn(),
    saveAs: 'box' as const,
    onSaveAsChange: vi.fn()
};

describe('LabelWithModelPopUp', () => {
    it('shows only the run button before a run', async () => {
        const labelWithModel = makeLabelWithModel();
        render(LabelWithModelPopUp, { props: { ...defaultProps, labelWithModel } });

        await fireEvent.click(screen.getByRole('button', { name: 'Generate suggestions' }));

        expect(labelWithModel.generate).toHaveBeenCalledOnce();
        expect(screen.getByText('50%')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /^Save/ })).not.toBeInTheDocument();
    });

    it('closes from the panel header', async () => {
        const onClose = vi.fn();
        render(LabelWithModelPopUp, {
            ...defaultProps,
            onClose,
            labelWithModel: makeLabelWithModel()
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Close tool' }));
        expect(onClose).toHaveBeenCalledOnce();
    });

    it('shows a hint after an empty result', () => {
        const labelWithModel = makeLabelWithModel({ isEmptyResult: true });
        render(LabelWithModelPopUp, { props: { ...defaultProps, labelWithModel } });

        expect(screen.getByText(/suggested no annotations/)).toBeInTheDocument();
    });

    it('shows the save controls after a run', async () => {
        const labelWithModel = makeLabelWithModel({
            predictions: [PREVIEW, PREVIEW],
            canSave: true
        });
        render(LabelWithModelPopUp, { props: { ...defaultProps, labelWithModel } });

        await fireEvent.click(screen.getByRole('button', { name: 'Save accepted (2)' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Generate again' }));

        expect(screen.getByText('2 suggested annotations')).toBeInTheDocument();
        expect(labelWithModel.save).toHaveBeenCalledOnce();
        expect(labelWithModel.generate).toHaveBeenCalledOnce();
        expect(
            screen.queryByRole('button', { name: 'Generate suggestions' })
        ).not.toBeInTheDocument();
    });

    it('shows the save as toggle only for a segmentation model', async () => {
        const labelWithModel = makeLabelWithModel({ predictions: [PREVIEW], canSave: true });
        const { rerender } = render(LabelWithModelPopUp, {
            props: { ...defaultProps, labelWithModel }
        });
        expect(screen.queryByRole('group', { name: 'Save as' })).not.toBeInTheDocument();

        await rerender({ ...defaultProps, model: SEGMENTATION_MODEL, labelWithModel });

        expect(screen.getByRole('group', { name: 'Save as' })).toBeInTheDocument();
    });
});
