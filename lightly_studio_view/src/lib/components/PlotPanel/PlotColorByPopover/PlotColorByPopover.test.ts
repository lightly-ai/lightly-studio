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
            withTags: false,
            withAnnotationLabels: false
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
            withTags: false,
            withAnnotationLabels: false
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
            withTags: true,
            withAnnotationLabels: false
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
            withTags: false,
            withAnnotationLabels: false
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
            withTags: true,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'tags' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
        expect(get(colorByType.selectedColorByType)).toBe('tags');
    });

    it('renders an annotations option when withAnnotationLabels is true', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: true
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByRole('option', { name: 'annotations' })).toBeInTheDocument();
    });

    it('does not render an annotations option when withAnnotationLabels is false', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.queryByRole('option', { name: 'annotations' })).not.toBeInTheDocument();
    });

    it('selecting annotations stores annotation_label as the selected type', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange,
            withTags: false,
            withAnnotationLabels: true
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'annotations' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
        expect(get(colorByType.selectedColorByType)).toBe('annotation_label');
    });

    it('selecting a metadata field named annotation_label routes to metadata when annotation labels are also available', async () => {
        metadataInfoStore.set([{ name: 'annotation_label', type: 'string' }]);

        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange,
            withTags: false,
            withAnnotationLabels: true
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.annotation_label' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith('annotation_label');
        expect(get(colorByType.selectedColorByType)).toBe('metadata');
    });

    it('selecting a metadata field named tags routes to metadata when tags are also available', async () => {
        metadataInfoStore.set([{ name: 'tags', type: 'string' }]);

        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange,
            withTags: true,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'metadata.tags' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith('tags');
        expect(get(colorByType.selectedColorByType)).toBe('metadata');
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
            withTags: false,
            withAnnotationLabels: false
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
            withTags: false,
            withAnnotationLabels: false
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('metadata.split');
    });

    it('button shows tags when tags are selected', () => {
        usePlotColorByType('test-collection-id').setSelectedColorByType('tags');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: true,
            withAnnotationLabels: false
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('tags');
    });

    it('button shows annotations when annotation_label is selected', () => {
        usePlotColorByType('test-collection-id').setSelectedColorByType('annotation_label');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: true
        });

        expect(screen.getByTestId('plot-color-by-button')).toHaveTextContent('annotations');
    });

    it('renders a No coloring option when there is something to color by', async () => {
        const user = userEvent.setup();

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByRole('option', { name: 'No coloring' })).toBeInTheDocument();
    });

    it('selecting No coloring clears the selected type', async () => {
        const user = userEvent.setup();
        const onSelectedKeyChange = vi.fn();
        const colorByType = usePlotColorByType('test-collection-id');

        colorByType.setSelectedColorByType('metadata');

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: 'split',
            onSelectedKeyChange,
            withTags: false,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(screen.getByRole('option', { name: 'No coloring' }));

        expect(onSelectedKeyChange).toHaveBeenCalledWith(null);
        expect(get(colorByType.selectedColorByType)).toBeNull();
    });

    it('does not render a No coloring option when there is nothing to color by', async () => {
        const user = userEvent.setup();
        metadataInfoStore.set([{ name: 'payload', type: 'object' }]);

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.queryByRole('option', { name: 'No coloring' })).not.toBeInTheDocument();
    });

    it('shows the empty state when no supported metadata fields exist and withTags is false', async () => {
        const user = userEvent.setup();
        metadataInfoStore.set([{ name: 'payload', type: 'object' }]);

        render(PlotColorByPopover, {
            collectionId: 'test-collection-id',
            selectedKey: null,
            onSelectedKeyChange: vi.fn(),
            withTags: false,
            withAnnotationLabels: false
        });

        await user.click(screen.getByTestId('plot-color-by-button'));

        expect(screen.getByText('Nothing to color by')).toBeInTheDocument();
    });
});
