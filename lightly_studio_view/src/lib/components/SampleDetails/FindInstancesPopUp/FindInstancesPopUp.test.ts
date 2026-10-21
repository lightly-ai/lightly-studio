import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import FindInstancesPopUp from './FindInstancesPopUp.svelte';

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [], isLoading: false })
}));

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
    boxCount: 0,
    isGenerating: false,
    resultCount: 0,
    canSave: false,
    onGenerate: vi.fn(),
    onSave: vi.fn(),
    onClear: vi.fn()
};

describe('FindInstancesPopUp', () => {
    it('finds instances on Enter only with a prompt, also when boxes are drawn', async () => {
        const onGenerate = vi.fn();
        const { rerender } = render(FindInstancesPopUp, {
            props: { ...defaultProps, onGenerate, boxCount: 2 }
        });
        const input = screen.getByLabelText('Instance prompt');

        await fireEvent.keyDown(input, { key: 'Enter' });
        expect(onGenerate).not.toHaveBeenCalled();
        expect(screen.getByRole('button', { name: 'Find instances' })).toBeDisabled();

        await rerender({ ...defaultProps, onGenerate, prompt: 'cars' });
        await fireEvent.keyDown(input, { key: 'Enter' });
        expect(onGenerate).toHaveBeenCalledOnce();
    });
});
