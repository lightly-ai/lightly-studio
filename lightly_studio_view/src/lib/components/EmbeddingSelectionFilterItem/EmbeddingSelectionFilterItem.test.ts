import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import EmbeddingSelectionFilterItem from './EmbeddingSelectionFilterItem.svelte';

const defaultProps = {
    checked: false,
    selectionCount: 1,
    itemLabel: 'sample',
    onVisibilityChange: vi.fn(),
    onClear: vi.fn()
};

describe('EmbeddingSelectionFilterItem', () => {
    it('renders filter item with title and singular count', () => {
        render(EmbeddingSelectionFilterItem, {
            props: { ...defaultProps }
        });

        expect(screen.getByTestId('embedding-selection-filter-chip')).toBeInTheDocument();
        expect(screen.getByText('Embedding Plot Filter')).toBeInTheDocument();
        expect(screen.getByText(/1\s*sample/i)).toBeInTheDocument();
    });

    it('renders pluralized count for multiple selected items', () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                ...defaultProps,
                selectionCount: 2
            }
        });

        expect(screen.getByText(/2\s*samples/i)).toBeInTheDocument();
    });

    it('calls onVisibilityChange when checkbox is toggled', async () => {
        const onVisibilityChange = vi.fn();
        render(EmbeddingSelectionFilterItem, {
            props: {
                ...defaultProps,
                onVisibilityChange
            }
        });

        await fireEvent.click(screen.getByLabelText('Embedding plot filter'));
        expect(onVisibilityChange).toHaveBeenCalledWith(true);
    });

    it('calls onClear when clear button is clicked', async () => {
        const onClear = vi.fn();
        render(EmbeddingSelectionFilterItem, {
            props: {
                ...defaultProps,
                onClear
            }
        });

        await fireEvent.click(screen.getByLabelText('Clear embedding plot filter'));
        expect(onClear).toHaveBeenCalledOnce();
    });
});
