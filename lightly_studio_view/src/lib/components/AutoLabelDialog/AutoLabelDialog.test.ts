import { render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { useAutoLabelDialog } from '$lib/hooks/useAutoLabelDialog';
import AutoLabelDialog from './AutoLabelDialog.svelte';

vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    useGlobalStorage: () => ({ filteredSampleCount: writable(12) })
}));

const autoLabelDialog = useAutoLabelDialog();

describe('AutoLabelDialog', () => {
    afterEach(autoLabelDialog.closeAutoLabelDialog);

    it('shows the configuration with a disabled run button', () => {
        autoLabelDialog.openAutoLabelDialog();
        render(AutoLabelDialog);

        expect(screen.getByText('12 images matching current filters')).toBeInTheDocument();
        expect(screen.getByLabelText('Targets')).toBeInTheDocument();
        expect(screen.getByText('Auto-labeling is coming soon.')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Auto-label' })).toBeDisabled();
    });
});
