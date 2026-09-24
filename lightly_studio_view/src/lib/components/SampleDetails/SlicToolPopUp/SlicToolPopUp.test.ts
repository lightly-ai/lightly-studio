import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SlicToolPopUp from './SlicToolPopUp.svelte';

const { setSlicLevel, context } = vi.hoisted(() => ({
    setSlicLevel: vi.fn(),
    context: { slic: { level: 'medium', status: 'ready' } }
}));
vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({ context, setSlicLevel })
}));

describe('SLIC controls', () => {
    it('lets the user choose the superpixel size', async () => {
        const view = render(SlicToolPopUp);
        await fireEvent.click(view.getByRole('button', { name: 'Fine' }));
        expect(setSlicLevel).toHaveBeenCalledWith('fine');
    });

    it('explains how to recover from computation failure', () => {
        context.slic.status = 'error';
        const view = render(SlicToolPopUp);
        expect(view.getByRole('alert')).toHaveTextContent('Could not compute superpixels');
    });
});
