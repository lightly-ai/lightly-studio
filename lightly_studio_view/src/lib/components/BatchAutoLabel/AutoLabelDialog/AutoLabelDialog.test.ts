import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AutoLabelDialog from './AutoLabelDialog.svelte';

const mocks = vi.hoisted(() => ({
    getDetector: vi.fn(),
    setPromptClassNames: vi.fn(),
    models: [] as unknown[]
}));

vi.mock('$lib/hooks', async () => {
    const { writable: createStore } = await import('svelte/store');
    return {
        useBrowserModels: () => ({
            models: createStore(mocks.models),
            loadProgress: createStore(null),
            getDetector: mocks.getDetector,
            setPromptClassNames: mocks.setPromptClassNames
        })
    };
});

const COCO_MODEL = {
    id: 'ltdetrv2-s-coco',
    task: 'object_detection',
    class_names: [],
    runsIn: 'browser',
    isTextPrompted: false
};
const TEXT_PROMPTED_MODEL = {
    id: 'grounding-dino-tiny',
    task: 'object_detection',
    class_names: ['forklift'],
    runsIn: 'browser',
    isTextPrompted: true
};

describe('AutoLabelDialog', () => {
    beforeEach(() => {
        mocks.getDetector.mockReset();
        mocks.setPromptClassNames.mockReset();
    });

    it('shows why the model could not load instead of loading forever', async () => {
        mocks.models = [COCO_MODEL];
        mocks.getDetector.mockRejectedValue(new Error('HTTP 404'));

        render(AutoLabelDialog, { open: true, selectedCount: 3, onStart: vi.fn() });

        expect(await screen.findByText(/Could not load the model: HTTP 404/)).toBeInTheDocument();
        expect(screen.queryByText('Loading the model classes…')).not.toBeInTheDocument();
    });

    it('asks a text-prompted model what to find and starts with the typed classes', async () => {
        mocks.models = [TEXT_PROMPTED_MODEL];
        mocks.getDetector.mockResolvedValue({ classNames: [] });
        const onStart = vi.fn();

        render(AutoLabelDialog, { open: true, selectedCount: 3, onStart });
        await fireEvent.input(screen.getByLabelText('What to find'), {
            target: { value: 'forklift, pallet' }
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Auto-label 3 images' }));

        expect(mocks.setPromptClassNames).toHaveBeenCalledWith('grounding-dino-tiny', [
            'forklift',
            'pallet'
        ]);
        expect(screen.queryByText(/no class names/)).not.toBeInTheDocument();
        expect(onStart).toHaveBeenCalledWith({
            modelId: 'grounding-dino-tiny',
            threshold: 0.5,
            classNames: ['forklift']
        });
    });
});
