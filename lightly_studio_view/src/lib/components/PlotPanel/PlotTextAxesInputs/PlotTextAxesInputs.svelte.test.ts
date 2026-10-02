import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import PlotTextAxesInputs from './PlotTextAxesInputs.svelte';
import { createEmptyTextAxesDraft } from './textAxesDraft';

describe('PlotTextAxesInputs', () => {
    it('commits the text axes on Enter when all four texts are filled', async () => {
        const user = userEvent.setup();
        const onCommit = vi.fn();
        const draft = $state(createEmptyTextAxesDraft());
        render(PlotTextAxesInputs, { draft, onCommit });

        await user.type(screen.getByLabelText('X axis start'), 'young');
        await user.type(screen.getByLabelText('X axis end'), 'old');
        await user.type(screen.getByLabelText('Y axis start'), 'sad');
        await user.type(screen.getByLabelText('Y axis end'), 'happy{Enter}');

        // The parent owns the draft, so it keeps the texts when the plot unmounts.
        expect(draft).toEqual({
            xNegative: 'young',
            xPositive: 'old',
            yNegative: 'sad',
            yPositive: 'happy'
        });
        expect(onCommit).toHaveBeenCalledExactlyOnceWith({
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });
    });

    it('marks the empty inputs and does not commit when a text is missing', async () => {
        const user = userEvent.setup();
        const onCommit = vi.fn();
        const draft = $state(createEmptyTextAxesDraft());
        render(PlotTextAxesInputs, { draft, onCommit });

        await user.type(screen.getByLabelText('X axis start'), 'young');
        await user.type(screen.getByLabelText('X axis end'), 'old');
        await user.type(screen.getByLabelText('Y axis start'), 'sad{Enter}');

        expect(onCommit).not.toHaveBeenCalled();
        expect(screen.getByLabelText('Y axis end')).toHaveAttribute('aria-invalid', 'true');
        expect(screen.getByLabelText('Y axis start')).toHaveAttribute('aria-invalid', 'false');
    });
});
