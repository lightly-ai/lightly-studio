import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import PlotColorByPopover from './PlotColorByPopover.svelte';

const metadataInfoStore = writable([
    { name: 'split', type: 'string' },
    { name: 'frame_index', type: 'integer' },
    { name: 'is_train', type: 'boolean' },
    { name: 'score', type: 'float' },
    { name: 'object', type: 'object' }
]);

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataInfo: metadataInfoStore
    })
}));

describe('PlotColorByPopover', () => {
    beforeAll(() => {
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
        Element.prototype.scrollIntoView = vi.fn();
    });

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
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn()
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByRole('option', { name: 'metadata.split' })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: 'metadata.is_train' })).toBeInTheDocument();
        expect(screen.queryByRole('option', { name: 'metadata.score' })).not.toBeInTheDocument();
        expect(screen.queryByRole('option', { name: 'metadata.object' })).not.toBeInTheDocument();
    });

    it('selecting one field calls onSelectedKeyChange with the key', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.split' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith('split');
    });

    it('clicking the selected field calls onSelectedKeyChange with null', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.split' }));

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

        expect(screen.getByTestId('plot-color-by-button')).toBeDisabled();
        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('Nothing to color by');
        expect(screen.queryByTestId('plot-color-by-options')).not.toBeInTheDocument();
    });
});
