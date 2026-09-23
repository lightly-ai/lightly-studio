import { render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
import MenuDialogHost from './MenuDialogHost.svelte';

vi.mock('$lib/components/Settings/SettingsDialog.svelte', async () => ({
    default: (await import('./MenuDialogHostStub.test.svelte')).default
}));

const collection: CollectionView = {
    collection_id: 'collection-id',
    dataset_id: 'dataset-id',
    name: 'Collection',
    sample_type: 'group',
    created_at: new Date('2026-01-01'),
    updated_at: new Date('2026-01-01')
};

const settingsDialog = useSettingsDialog();

describe('MenuDialogHost', () => {
    afterEach(settingsDialog.closeSettingsDialog);

    it('loads a dialog only when it is opened', async () => {
        render(MenuDialogHost, { props: { collection } });
        expect(screen.queryByTestId('lazy-menu-dialog')).not.toBeInTheDocument();

        settingsDialog.openSettingsDialog();

        expect(await screen.findByTestId('lazy-menu-dialog')).toBeInTheDocument();
    });
});
