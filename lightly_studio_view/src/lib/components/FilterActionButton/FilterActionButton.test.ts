import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import Eye from '@lucide/svelte/icons/eye';
import { describe, expect, it, vi } from 'vitest';
import FilterActionButton from './FilterActionButton.svelte';

describe('FilterActionButton', () => {
    it('renders a labelled button that calls onclick', async () => {
        const onclick = vi.fn();
        render(FilterActionButton, { label: 'Show all', icon: Eye, onclick });

        await userEvent.click(screen.getByRole('button', { name: 'Show all' }));

        expect(onclick).toHaveBeenCalledOnce();
    });
});
