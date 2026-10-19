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

        await user.type(screen.getByLabelText('Left'), 'young');
        await user.type(screen.getByLabelText('Right'), 'old');
        await user.type(screen.getByLabelText('Bottom'), 'sad{Enter}');

        // A missing text marks its input and blocks the commit.
        expect(onCommit).not.toHaveBeenCalled();
        expect(screen.getByLabelText('Top')).toHaveAttribute('aria-invalid', 'true');
        expect(screen.getByLabelText('Bottom')).toHaveAttribute('aria-invalid', 'false');

        await user.type(screen.getByLabelText('Top'), ' happy {Enter}');

        // The parent owns the draft, so it keeps the texts when the plot unmounts.
        expect(draft.yPositive).toBe(' happy ');
        expect(onCommit).toHaveBeenCalledExactlyOnceWith({
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });
    });
});
