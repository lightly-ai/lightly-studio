import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { useDatasetSplitDialog } from '$lib/components/DatasetSplit/useDatasetSplitDialog';
import Menu from './Menu.svelte';
import MenuDialogHost from './MenuDialogHost.svelte';

vi.mock('$lib/components/DatasetSplit/useDatasetSplit/useDatasetSplit.svelte', () => ({
    useDatasetSplit: () => ({
        sampleCount: 10,
        tags: writable([]),
        pending: writable(false),
        error: writable(undefined),
        submit: vi.fn()
    })
}));

const collection: CollectionView = {
    collection_id: 'collection-id',
    dataset_id: 'dataset-id',
    name: 'Collection',
    sample_type: 'image',
    created_at: new Date('2026-01-01'),
    updated_at: new Date('2026-01-01')
};

const { openDatasetSplitDialog, closeDatasetSplitDialog } = useDatasetSplitDialog();

async function openMenu() {
    await fireEvent.keyDown(screen.getByTestId('menu-trigger'), { key: 'Enter' });
    expect(await screen.findByRole('listbox')).toBeInTheDocument();
}

describe('Split dataset menu', () => {
    afterEach(closeDatasetSplitDialog);

    it.each(['image', 'video'] as const)(
        'opens, closes and reopens on the %s grid',
        async (sample_type) => {
            const props = {
                collection: { ...collection, sample_type },
                isImages: sample_type === 'image',
                isVideos: sample_type === 'video'
            };
            render(Menu, props);
            render(MenuDialogHost, props);
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
            await openMenu();
            await fireEvent.pointerUp(screen.getByTestId('menu-dataset-split'));
            expect(await screen.findByRole('dialog')).toBeInTheDocument();
            await fireEvent.input(screen.getByLabelText('Tag 1'), {
                target: { value: 'training' }
            });
            await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
            await openMenu();
            await fireEvent.pointerUp(screen.getByTestId('menu-dataset-split'));
            expect(await screen.findByLabelText('Tag 1')).toHaveValue('train');
        }
    );

    it('discards the open dialog when navigating or unmounting the host', async () => {
        const props = { collection, isImages: true };
        const host = render(MenuDialogHost, props);
        openDatasetSplitDialog(collection.collection_id);
        expect(await screen.findByRole('dialog')).toBeInTheDocument();
        await host.rerender({ collection: { ...collection, collection_id: 'other-collection' } });
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        await host.rerender(props);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        openDatasetSplitDialog(collection.collection_id);
        expect(await screen.findByRole('dialog')).toBeInTheDocument();
        host.unmount();
        render(MenuDialogHost, props);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it.each(['image', 'video_frame', 'group'] as const)(
        'hides splitting outside image/video grids (%s)',
        async (sample_type) => {
            render(Menu, { collection: { ...collection, sample_type } });
            await openMenu();
            expect(screen.queryByTestId('menu-dataset-split')).not.toBeInTheDocument();
        }
    );
});
