import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ColoringControls from './ColoringControls.svelte';

const defaultProps = {
    intensity: 1.5,
    logScale: false
};

describe('ColoringControls', () => {
    it('renders the current intensity and the log-scale toggle', () => {
        render(ColoringControls, { props: { ...defaultProps } });

        expect(screen.getByText('1.5×')).toBeInTheDocument();
        expect(screen.getByTestId('color-log-scale-checkbox')).toBeInTheDocument();
    });

    it('reflects the log-scale value through the checkbox', () => {
        render(ColoringControls, { props: { ...defaultProps, logScale: true } });

        expect(screen.getByTestId('color-log-scale-checkbox')).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('flips the checkbox state when clicked', async () => {
        render(ColoringControls, { props: { ...defaultProps } });
        const checkbox = screen.getByTestId('color-log-scale-checkbox');
        expect(checkbox).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(checkbox);

        await waitFor(() => expect(checkbox).toHaveAttribute('aria-checked', 'true'));
    });
});
