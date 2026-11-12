import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { Eye } from '@lucide/svelte';
import { describe, expect, it, vi } from 'vitest';
import FilterActionButton from './FilterActionButton.svelte';

describe('FilterActionButton', () => {
    it('renders a labelled button that calls onclick', async () => {
        const onclick = vi.fn();
        render(FilterActionButton, { label: 'Show all', icon: Eye, onclick });

        await userEvent.click(screen.getByRole('button', { name: 'Show all' }));

        expect(onclick).toHaveBeenCalledOnce();
    });

    it('does not call onclick when disabled', async () => {
        const onclick = vi.fn();
        render(FilterActionButton, { label: 'Clear', icon: Eye, onclick, disabled: true });

        const button = screen.getByRole('button', { name: 'Clear' });
        expect(button).toBeDisabled();
        await userEvent.click(button);

        expect(onclick).not.toHaveBeenCalled();
    });
});
