import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DistributionConfigDialog from './DistributionConfigDialog.svelte';
import type { DistributionConfig } from '../types';

const baseConfig: DistributionConfig = { n: 5, sortBy: 'count', orientation: 'vertical' };

const renderDialog = (overrides: Partial<Parameters<typeof render>[1]> = {}) => {
    const onApply = vi.fn();
    render(DistributionConfigDialog, {
        props: { open: true, maxN: 30, config: baseConfig, onApply, ...overrides }
    });
    return { onApply };
};

describe('DistributionConfigDialog', () => {
    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title and seeds the input from the applied config', () => {
        renderDialog();

        expect(screen.getByText('Configure classes')).toBeInTheDocument();
        expect(screen.getByTestId('distribution-config-top-n')).toHaveValue(5);
    });

    it('does not render its content while closed', () => {
        renderDialog({ open: false });

        expect(screen.queryByText('Configure classes')).not.toBeInTheDocument();
    });

    it('applies the edited top-N and closes', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('distribution-config-top-n'), {
            target: { value: '8' }
        });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseConfig, n: 8 });
        await waitFor(() =>
            expect(screen.queryByText('Configure classes')).not.toBeInTheDocument()
        );
    });

    it('sets top-N to maxN via the "All" quick action', async () => {
        const { onApply } = renderDialog();

        await fireEvent.click(screen.getByTestId('distribution-config-all'));
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseConfig, n: 30 });
    });

    it('clamps top-N above maxN back down to maxN on apply', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('distribution-config-top-n'), {
            target: { value: '999' }
        });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseConfig, n: 30 });
    });

    it('falls back to 1 when the input is cleared to a non-finite value', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('distribution-config-top-n'), {
            target: { value: '' }
        });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseConfig, n: 1 });
    });

    it('closes without applying when Cancel is clicked', async () => {
        const { onApply } = renderDialog();

        await fireEvent.click(screen.getByText('Cancel'));

        expect(onApply).not.toHaveBeenCalled();
        await waitFor(() =>
            expect(screen.queryByText('Configure classes')).not.toBeInTheDocument()
        );
    });
});
