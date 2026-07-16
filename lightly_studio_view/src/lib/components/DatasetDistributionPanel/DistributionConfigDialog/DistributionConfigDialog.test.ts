import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import DistributionConfigDialog from './DistributionConfigDialog.svelte';
import type { DistributionConfig } from '../types';
import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';

const baseConfig: DistributionConfig = {
    mode: 'topN',
    n: 5,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'vertical',
    countMode: AnnotationCountMode.OBJECTS
};

const allClasses = Array.from({ length: 30 }, (_, i) => `class-${i}`);

const renderDialog = (overrides: Partial<Parameters<typeof render>[1]> = {}) => {
    const onApply = vi.fn();
    render(DistributionConfigDialog, {
        props: { open: true, allClasses, config: baseConfig, onApply, ...overrides }
    });
    return { onApply };
};

describe('DistributionConfigDialog', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

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

    it('shows the Count by select with Objects selected by default', () => {
        renderDialog();

        const countBySelect = screen.getByTestId('distribution-config-count-mode');
        expect(countBySelect).toBeInTheDocument();
        expect(countBySelect).toHaveTextContent('Objects');
    });

    it('applies the selected count mode on Apply', async () => {
        const user = userEvent.setup();
        const { onApply } = renderDialog();

        await user.click(screen.getByTestId('distribution-config-count-mode'));
        const samplesOption = await waitFor(() => screen.getByRole('option', { name: 'Samples' }));
        await user.click(samplesOption);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith(
            expect.objectContaining({ countMode: AnnotationCountMode.SAMPLES })
        );
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

    it('applies the manually selected classes', async () => {
        const { onApply } = renderDialog({
            config: { ...baseConfig, mode: 'manual', manualClasses: ['class-2'] }
        });

        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onApply).toHaveBeenCalledWith(
            expect.objectContaining({ mode: 'manual', manualClasses: ['class-2'] })
        );
    });

    it('disables Apply in manual mode when no class is selected', async () => {
        renderDialog({ config: { ...baseConfig, mode: 'manual', manualClasses: [] } });

        await waitFor(() => expect(screen.getByTestId('distribution-config-apply')).toBeDisabled());
    });
});
