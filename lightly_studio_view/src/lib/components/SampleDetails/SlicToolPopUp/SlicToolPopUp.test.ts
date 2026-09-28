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
        expect(view.getByRole('button', { name: 'Medium' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
        expect(setSlicLevel).toHaveBeenCalledWith('fine');
    });

    it.each([
        ['idle', 'Not started'],
        ['computing', 'Computing…'],
        ['ready', 'Ready'],
        ['error', 'Could not compute superpixels']
    ])('displays %s status', (status, label) => {
        context.slic.status = status;
        const view = render(SlicToolPopUp);
        expect(view.getByRole(status === 'error' ? 'alert' : 'status')).toHaveTextContent(label);
    });
});
