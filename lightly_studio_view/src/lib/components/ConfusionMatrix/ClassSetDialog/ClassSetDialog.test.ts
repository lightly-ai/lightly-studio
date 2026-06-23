import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClassSetDialog from './ClassSetDialog.svelte';
import type { ClassSetConfig, ColorConfig } from './types';

const allClasses = ['cat', 'dog', 'bird'];

const baseConfig: ClassSetConfig = {
    mode: 'topN',
    n: 2,
    sortBy: 'most-confused',
    manualClasses: ['cat']
};

const baseColor: ColorConfig = { intensity: 1, logScale: false };

function renderDialog(config: Partial<ClassSetConfig> = {}, onApply = vi.fn()) {
    render(ClassSetDialog, {
        props: {
            open: true,
            allClasses,
            config: { ...baseConfig, ...config },
            color: baseColor,
            onApply
        }
    });
    return onApply;
}

describe('ClassSetDialog', () => {
    afterEach(() => {
        document.body.innerHTML = '';
    });

    it('renders its title when open', async () => {
        renderDialog();
        await waitFor(() => expect(screen.getByText('Configure classes')).toBeInTheDocument());
    });

    it('clamps the top-N value to the number of classes on apply', async () => {
        const onApply = renderDialog({ n: 999 });

        await fireEvent.click(screen.getByTestId('class-set-apply'));

        expect(onApply).toHaveBeenCalledWith(
            expect.objectContaining({ n: allClasses.length }),
            expect.anything()
        );
    });

    it('disables Apply when the top-N value is not finite', async () => {
        renderDialog({ n: NaN });

        await waitFor(() => expect(screen.getByTestId('class-set-apply')).toBeDisabled());
    });

    it('disables Apply in manual mode when no class is selected', async () => {
        renderDialog({ mode: 'manual', manualClasses: [] });

        await waitFor(() => expect(screen.getByTestId('class-set-apply')).toBeDisabled());
    });
});
