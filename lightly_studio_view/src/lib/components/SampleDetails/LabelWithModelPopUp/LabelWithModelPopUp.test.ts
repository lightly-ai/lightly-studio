import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import { get } from 'svelte/store';
import { useBrowserModels } from '$lib/hooks';
import type { ComponentProps } from 'svelte';
import type { LabelingModelView, ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import LabelWithModelPopUp from './LabelWithModelPopUp.svelte';

type LabelWithModel = ComponentProps<typeof LabelWithModelPopUp>['labelWithModel'];

const DETECTION_MODEL = {
    id: 'ltdetrv2-s-coco',
    task: 'object_detection',
    class_names: ['cat'],
    runsIn: 'browser' as const
} satisfies LabelingModelView & { runsIn: string };
const SEGMENTATION_MODEL = {
    id: 'ltdetrv2-seg-s-coco',
    task: 'instance_segmentation',
    class_names: ['cat'],
    runsIn: 'server' as const
} satisfies LabelingModelView & { runsIn: string };
const TEXT_PROMPTED_MODEL = {
    id: 'grounding-dino-tiny',
    task: 'object_detection',
    class_names: [],
    runsIn: 'browser' as const,
    isTextPrompted: true
} satisfies LabelingModelView & { runsIn: string; isTextPrompted: boolean };
const PREVIEW: ModelAnnotationPreview = {
    class_name: 'cat',
    bbox: { x: 0, y: 0, width: 1, height: 1 },
    segmentation_mask: null,
    score: 0.9
};

const makeLabelWithModel = (overrides: Partial<LabelWithModel> = {}): LabelWithModel => ({
    predictions: [],
    isGenerating: false,
    isEmptyResult: false,
    isSaving: false,
    canSave: false,
    canGenerate: true,
    generate: vi.fn(),
    removePrediction: vi.fn(),
    clear: vi.fn(),
    save: vi.fn(),
    ...overrides
});

const defaultProps = {
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

        await fireEvent.click(screen.getByRole('button', { name: 'Run model' }));

        expect(labelWithModel.generate).toHaveBeenCalledOnce();
        expect(screen.getByText('0.50')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /^Save/ })).not.toBeInTheDocument();
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

        await fireEvent.click(screen.getByRole('button', { name: 'Save 2' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Run again' }));

        expect(screen.getByText('2 suggested annotations')).toBeInTheDocument();
        expect(labelWithModel.save).toHaveBeenCalledOnce();
        expect(labelWithModel.generate).toHaveBeenCalledOnce();
        expect(screen.queryByRole('button', { name: 'Run model' })).not.toBeInTheDocument();
    });

    it('blocks a model change while saving', () => {
        const labelWithModel = makeLabelWithModel({ predictions: [PREVIEW], isSaving: true });
        render(LabelWithModelPopUp, { props: { ...defaultProps, labelWithModel } });

        expect(screen.getByTestId('label-with-model-select')).toBeDisabled();
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

    it('asks a text-prompted model what to find and runs only once there is a class', async () => {
        const labelWithModel = makeLabelWithModel();
        const { rerender } = render(LabelWithModelPopUp, {
            props: { ...defaultProps, model: TEXT_PROMPTED_MODEL, labelWithModel }
        });
        expect(screen.getByRole('button', { name: 'Run model' })).toBeDisabled();

        await fireEvent.input(screen.getByLabelText('What to find'), {
            target: { value: 'Forklift, pallet , ,' }
        });
        const typed = get(useBrowserModels().models).find(
            (model) => model.id === TEXT_PROMPTED_MODEL.id
        );
        expect(typed?.class_names).toEqual(['Forklift', 'pallet']);

        await rerender({
            ...defaultProps,
            model: { ...TEXT_PROMPTED_MODEL, class_names: ['Forklift', 'pallet'] },
            labelWithModel
        });
        expect(screen.getByRole('button', { name: 'Run model' })).toBeEnabled();
    });

    it('does not ask a model with fixed classes what to find', () => {
        render(LabelWithModelPopUp, {
            props: { ...defaultProps, labelWithModel: makeLabelWithModel() }
        });

        expect(screen.queryByLabelText('What to find')).not.toBeInTheDocument();
    });
});
