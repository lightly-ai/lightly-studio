import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { get, writable } from 'svelte/store';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import PlotColorByPopover from './PlotColorByPopover.svelte';
import { usePlotColorByType } from './usePlotColorByType/usePlotColorByType';

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
        usePlotColorByType('test-collection-id').clearSelectedColorByType();
    });

    it('renders supported metadata fields with metadata prefix and omits unsupported ones', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByRole('option', { name: 'metadata.split' })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: 'metadata.is_train' })).toBeInTheDocument();
        expect(screen.queryByRole('option', { name: 'metadata.score' })).not.toBeInTheDocument();
        expect(screen.queryByRole('option', { name: 'metadata.object' })).not.toBeInTheDocument();
    });

    it('selecting a metadata field stores metadata as the selected type', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange,
            withTags: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.split' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith('split');
        expect(get(colorByType.selectedColorByType)).toBe('metadata');
    });

    it('renders a tags option when withTags is true', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: true
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByRole('option', { name: 'tags' })).toBeInTheDocument();
    });

    it('does not render a tags option when withTags is false', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.queryByRole('option', { name: 'tags' })).not.toBeInTheDocument();
    });

    it('selecting tags stores tags as the selected type', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange,
            withTags: true
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'tags' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
        expect(get(colorByType.selectedColorByType)).toBe('tags');
    });

    it('clicking the selected metadata field clears the selected type', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        colorByType.setSelectedColorByType('metadata');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange,
            withTags: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.split' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
        expect(get(colorByType.selectedColorByType)).toBeNull();
    });

    it('button shows the selected label', () => {
        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange: vi.fn(),
            withTags: false
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('metadata.split');
    });

    it('button shows tags when tags are selected', () => {
        usePlotColorByType('test-collection-id').setSelectedColorByType('tags');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: true
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('tags');
    });

    it('shows the empty state when no supported metadata fields exist and withTags is false', async () => {
        metadataInfoStore.set([{ name: 'payload', type: 'object' }]);

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false
        });

        expect(screen.getByTestId('plot-color-by-button')).toBeDisabled();
        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('Nothing to color by');
        expect(screen.queryByTestId('plot-color-by-options')).not.toBeInTheDocument();
    });
});
