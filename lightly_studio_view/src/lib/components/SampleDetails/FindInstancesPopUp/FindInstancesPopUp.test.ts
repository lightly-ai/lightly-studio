import { render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import FindInstancesPopUp from './FindInstancesPopUp.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

type Instances = ComponentProps<typeof FindInstancesPopUp>['instances'];

const makeInstances = ({ boxes = 0, predictions = 0, isEmptyResult = false }) =>
    ({
        boxes: Array(boxes).fill({ x: 0, y: 0, width: 1, height: 1 }),
        predictions: Array(predictions).fill({}),
        isGenerating: false,
        isEmptyResult,
        canGenerate: true,
        canSave: predictions > 0,
        generate: vi.fn(),
        save: vi.fn()
    }) as unknown as Instances;

const defaultProps = {
    collectionId: 'collection-1',
    prompt: '',
    onPromptChange: vi.fn(),
    maxInstances: 16,
    onMaxInstancesChange: vi.fn(),
    annotationClass: null,
    onAnnotationClassChange: vi.fn(),
    saveAs: 'mask' as const,
    onSaveAsChange: vi.fn(),
    isDrawingBox: false,
    onDrawBoxChange: vi.fn(),
    instances: makeInstances({}),
    onClear: vi.fn()
};

describe('FindInstancesPopUp', () => {
    it('shows how many boxes are drawn and how many instances are found', async () => {
        const { rerender } = render(FindInstancesPopUp, {
            props: { ...defaultProps, instances: makeInstances({ boxes: 2 }) }
        });
        expect(screen.getByText(/Boxes drawn: 2\./)).toBeInTheDocument();

        await rerender({ ...defaultProps, instances: makeInstances({ predictions: 5 }) });
        expect(screen.getByText(/Instances found: 5\. Pick a class/)).toBeInTheDocument();
    });

    it('says when a search finds no instances', () => {
        render(FindInstancesPopUp, {
            props: { ...defaultProps, instances: makeInstances({ isEmptyResult: true }) }
        });
        expect(screen.getByText(/No instances found\./)).toBeInTheDocument();
    });
});
