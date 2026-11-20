import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ModelAnnotationPreview } from '$lib/api/lightly_studio_local';
import LabelWithModelOverlay from './LabelWithModelOverlay.svelte';

const cat: ModelAnnotationPreview = {
    class_name: 'cat',
    bbox: { x: 1, y: 0, width: 2, height: 2 },
    segmentation_mask: null,
    score: 0.9
};

const labelWithModel = {
    predictions: [] as ModelAnnotationPreview[],
    isGenerating: false,
    isEmptyResult: false,
    isSaving: false,
    canSave: false,
    canGenerate: true,
    generate: vi.fn(),
    removePrediction: vi.fn(),
    clear: vi.fn(),
    save: vi.fn()
};

const defaultProps = {
    sample: { width: 100 },
    scale: 1,
    saveAs: 'box' as const,
    labelWithModel
};

describe('LabelWithModelOverlay', () => {
    const onWindowKeyDown = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        labelWithModel.predictions = [cat];
        labelWithModel.isSaving = false;
        window.addEventListener('keydown', onWindowKeyDown);
    });

    afterEach(() => window.removeEventListener('keydown', onWindowKeyDown));

    it('clears the results on Escape and keeps the tool open', async () => {
        render(LabelWithModelOverlay, { props: defaultProps });

        await fireEvent.keyDown(document.body, { key: 'Escape' });

        expect(labelWithModel.clear).toHaveBeenCalledOnce();
        expect(onWindowKeyDown).not.toHaveBeenCalled();
    });

    it('lets Escape through during a save', async () => {
        labelWithModel.isSaving = true;
        render(LabelWithModelOverlay, { props: defaultProps });

        await fireEvent.keyDown(document.body, { key: 'Escape' });

        expect(labelWithModel.clear).not.toHaveBeenCalled();
        expect(onWindowKeyDown).toHaveBeenCalledOnce();
    });
});
