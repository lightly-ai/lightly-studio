import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SlicToolPopUp from './SlicToolPopUp.svelte';

const { setSlicLevel, context } = vi.hoisted(() => ({
    setSlicLevel: vi.fn(),
    context: { slic: { level: 'medium', status: 'ready' } }
}));
vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({ context, setSlicLevel })
}));

const annotationContext = {
    annotationId: 'object-1' as string | null,
    isDrawing: false,
    isOnAnnotationDetailsView: false
};
const setAnnotationId = vi.fn();
const setLastCreatedAnnotationId = vi.fn();
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: annotationContext,
        setAnnotationId,
        setLastCreatedAnnotationId
    })
}));
beforeEach(() => {
    Object.assign(annotationContext, {
        annotationId: 'object-1',
        isDrawing: false,
        isOnAnnotationDetailsView: false
    });
    vi.clearAllMocks();
});

describe('SLIC controls', () => {
    it('finishes the object and keeps size controls available', async () => {
        const view = render(SlicToolPopUp);
        await fireEvent.click(view.getByRole('button', { name: 'Finish' }));
        expect(setAnnotationId).toHaveBeenCalledWith(null);
        expect(setLastCreatedAnnotationId).toHaveBeenCalledWith(null);
        expect(view.getByRole('button', { name: 'Fine' })).toBeInTheDocument();
    });
    it.each(['no object', 'drawing', 'saving', 'details'])('guards Finish during %s', (state) => {
        annotationContext.annotationId = state === 'no object' ? null : 'object-1';
        annotationContext.isDrawing = state === 'drawing';
        annotationContext.isOnAnnotationDetailsView = state === 'details';
        const view = render(SlicToolPopUp, { isPending: state === 'saving' });
        if (state === 'details') expect(view.queryByRole('button', { name: 'Finish' })).toBeNull();
        else expect(view.getByRole('button', { name: 'Finish' })).toBeDisabled();
    });
    it('lets the user choose the superpixel size', async () => {
        const view = render(SlicToolPopUp);
        await fireEvent.click(view.getByRole('button', { name: 'Fine' }));
        expect(view.getByRole('button', { name: 'Medium' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
        expect(setSlicLevel).toHaveBeenCalledWith('fine');
    });
});
