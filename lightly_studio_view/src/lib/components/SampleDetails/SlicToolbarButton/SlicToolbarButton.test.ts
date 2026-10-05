import { render, fireEvent } from '@testing-library/svelte';
import { expect, it, vi } from 'vitest';
import SlicToolbarButton from './SlicToolbarButton.svelte';

it('activates the tool and exposes its selected state', async () => {
    const onclick = vi.fn();
    const view = render(SlicToolbarButton, { onclick });
    const button = view.getByRole('button', { name: 'AI-Assisted labeling' });
    expect(button).toHaveAttribute('aria-pressed', 'false');
    await fireEvent.click(button);
    expect(onclick).toHaveBeenCalledOnce();
    await view.rerender({ onclick, isActive: true });
    expect(button).toHaveAttribute('aria-pressed', 'true');
});
