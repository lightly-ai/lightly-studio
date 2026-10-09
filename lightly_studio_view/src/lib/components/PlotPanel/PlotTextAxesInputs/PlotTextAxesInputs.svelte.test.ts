import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import PlotTextAxesInputs from './PlotTextAxesInputs.svelte';
import { createEmptyTextAxesDraft } from './textAxesDraft';

describe('PlotTextAxesInputs', () => {
    it('commits the trimmed texts on Enter only when all four are filled', async () => {
        const user = userEvent.setup();
        const onCommit = vi.fn();
        const draft = $state(createEmptyTextAxesDraft());
        render(PlotTextAxesInputs, { draft, onCommit });

        await user.type(screen.getByLabelText('X axis start'), 'young');
        await user.type(screen.getByLabelText('X axis end'), 'old');
        await user.type(screen.getByLabelText('Y axis start'), 'sad{Enter}');

        // A missing text marks its input and blocks the commit.
        expect(onCommit).not.toHaveBeenCalled();
        expect(screen.getByLabelText('Y axis end')).toHaveAttribute('aria-invalid', 'true');
        expect(screen.getByLabelText('Y axis start')).toHaveAttribute('aria-invalid', 'false');

        await user.type(screen.getByLabelText('Y axis end'), ' happy {Enter}');

        // The parent owns the draft, so it keeps the texts when the plot unmounts.
        expect(draft.yPositive).toBe(' happy ');
        expect(onCommit).toHaveBeenCalledExactlyOnceWith({
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });
    });
});
