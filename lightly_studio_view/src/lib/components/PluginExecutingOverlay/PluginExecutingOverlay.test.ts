import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import PluginExecutingOverlay from './PluginExecutingOverlay.svelte';
import { useOperatorsDialog } from '$lib/hooks';

const { setPluginExecuting, setPluginProgress } = useOperatorsDialog();

describe('PluginExecutingOverlay', () => {
    afterEach(() => {
        setPluginExecuting(false);
        setPluginProgress(null);
        document.body.innerHTML = '';
    });

    it('is hidden when plugin is not executing', () => {
        render(PluginExecutingOverlay);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('shows the overlay while plugin is executing', async () => {
        render(PluginExecutingOverlay);
        setPluginExecuting(true);
        await screen.findByRole('dialog');
        expect(
            screen.getByText('Plugin executing. This might take up to several minutes…')
        ).toBeInTheDocument();
    });

    it('hides the overlay after execution completes', async () => {
        render(PluginExecutingOverlay);
        setPluginExecuting(true);
        await screen.findByRole('dialog');
        setPluginExecuting(false);
        await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });

    it('shows reported progress instead of the spinner', async () => {
        render(PluginExecutingOverlay);
        setPluginExecuting(true);
        setPluginProgress({ current: 128, total: 1000, description: 'Running inference' });

        await screen.findByText('13%');
        expect(screen.getByText('Running inference')).toBeInTheDocument();
        expect(screen.getByText('128 / 1000 samples')).toBeInTheDocument();
        expect(
            screen.queryByText('Plugin executing. This might take up to several minutes…')
        ).not.toBeInTheDocument();
    });

    it('falls back to the spinner when the total is not known yet', async () => {
        render(PluginExecutingOverlay);
        setPluginExecuting(true);
        setPluginProgress({ current: 0, total: 0, description: '' });

        await screen.findByRole('dialog');
        expect(
            screen.getByText('Plugin executing. This might take up to several minutes…')
        ).toBeInTheDocument();
    });
});
