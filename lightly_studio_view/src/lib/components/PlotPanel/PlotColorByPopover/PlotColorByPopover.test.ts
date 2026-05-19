import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PlotColorByPopover from './PlotColorByPopover.svelte';

const metadataInfoStore = writable([
    { name: 'split', type: 'string' },
    { name: 'frame_index', type: 'integer' },
    { name: 'is_train', type: 'boolean' },
    { name: 'score', type: 'float' },
    { name: 'object', type: 'object' }
]);

vi.mock('$lib/hooks/', () => ({
    useMetadataFilters: () => ({
        metadataInfo: metadataInfoStore
    })
}));

describe('PlotColorByPopover', () => {
    beforeEach(() => {
        metadataInfoStore.set([
            { name: 'split', type: 'string' },
            { name: 'frame_index', type: 'integer' },
            { name: 'is_train', type: 'boolean' },
            { name: 'score', type: 'float' },
            { name: 'object', type: 'object' }
        ]);
    });

    it('renders supported metadata fields with metadata prefix and omits unsupported ones', async () => {
        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn()
        });

        await fireEvent.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByText('metadata.split')).toBeInTheDocument();
        expect(screen.getByText('metadata.is_train')).toBeInTheDocument();
        expect(screen.queryByText('metadata.score')).not.toBeInTheDocument();
        expect(screen.queryByText('metadata.object')).not.toBeInTheDocument();
    });

    it('selecting one field calls onSelectedKeyChange with the key', async () => {
        const onSelectedKeyChange = vi.fn();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange
        });

        await fireEvent.click(screen.getByTestId('plot-color-by-button'));
        await fireEvent.click(screen.getByText('metadata.split'));

        expect(onSelectedKeyChange).toHaveBeenCalledWith('split');
    });

    it('clicking the selected field calls onSelectedKeyChange with null', async () => {
        const onSelectedKeyChange = vi.fn();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange
        });

        await fireEvent.click(screen.getByTestId('plot-color-by-button'));
        await fireEvent.click(
            within(screen.getByTestId('plot-color-by-options')).getByText('metadata.split')
        );

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
    });

    it('button shows the selected label', () => {
        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange: vi.fn()
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('metadata.split');
    });

    it('shows the empty state when no supported metadata fields exist', async () => {
        metadataInfoStore.set([{ name: 'payload', type: 'object' }]);

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn()
        });

        await fireEvent.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByText('Nothing to color by.')).toBeInTheDocument();
    });
});
