import { render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import PluginExecutingOverlay from './PluginExecutingOverlay.svelte';
import { useOperatorsDialog } from '$lib/hooks';

const { setPluginExecuting } = useOperatorsDialog();

describe('PluginExecutingOverlay', () => {
    afterEach(() => {
        setPluginExecuting(false);
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
});
