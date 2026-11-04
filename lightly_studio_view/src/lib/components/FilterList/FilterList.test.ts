import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import FilterList from './FilterList.svelte';
import type { FilterListItem } from './filterList.helpers';

const makeItems = (count: number): FilterListItem[] =>
    Array.from({ length: count }, (_, index) => ({
        id: `id-${index}`,
        label: `Item ${index}`,
        selected: false
    }));

const renderList = (props: Partial<Parameters<typeof render<typeof FilterList>>[1]> = {}) => {
    const onToggle = vi.fn();
    const onSelectionChange = vi.fn();
    render(FilterList, { items: makeItems(3), onToggle, onSelectionChange, ...props });
    return { onToggle, onSelectionChange };
};

describe('FilterList', () => {
    it('filters the rows with the search', async () => {
        renderList({ items: makeItems(8) });

        await userEvent.type(screen.getByPlaceholderText('Search…'), 'item 7');

        expect(screen.getAllByTestId('filter-list-item')).toHaveLength(1);
        expect(screen.getByTestId('filter-list-name')).toHaveTextContent('Item 7');
    });

    it('highlights the search match', async () => {
        renderList({ items: makeItems(8) });

        await userEvent.type(screen.getByPlaceholderText('Search…'), ' item 7 ');

        expect(screen.getByTestId('filter-list-name').querySelector('mark')).toHaveTextContent(
            'Item 7'
        );
    });

    it('shows the no-match text when nothing matches', async () => {
        renderList({ items: makeItems(8) });

        await userEvent.type(screen.getByPlaceholderText('Search…'), 'zzz');

        expect(screen.getByText('No matches.')).toBeInTheDocument();
    });

    it('renders the count of a row', () => {
        renderList({ items: [{ id: 'a', label: 'A', selected: false, count: '3 of 8' }] });

        expect(screen.getByTestId('filter-list-count')).toHaveTextContent('3 of 8');
    });

    it('calls onToggle when a row checkbox is clicked', async () => {
        const { onToggle } = renderList();

        await userEvent.click(screen.getByRole('checkbox', { name: 'Item 1' }));

        expect(onToggle).toHaveBeenCalledWith('id-1');
    });

    it('selects all visible ids plus the selected ones', async () => {
        const items = makeItems(8);
        items[0].selected = true;
        const { onSelectionChange } = renderList({ items });

        await userEvent.type(screen.getByPlaceholderText('Search…'), 'item 7');
        await userEvent.click(screen.getByRole('button', { name: 'Select all' }));

        expect(onSelectionChange).toHaveBeenCalledWith(['id-0', 'id-7']);
    });

    it('clears the selection', async () => {
        const { onSelectionChange } = renderList();

        await userEvent.click(screen.getByRole('button', { name: 'Clear' }));

        expect(onSelectionChange).toHaveBeenCalledWith([]);
    });

    it('renders 50 rows at a time and shows more on click', async () => {
        renderList({ items: makeItems(120) });

        expect(screen.getAllByTestId('filter-list-item')).toHaveLength(50);
        await userEvent.click(screen.getByRole('button', { name: 'Show 50 more' }));

        expect(screen.getAllByTestId('filter-list-item')).toHaveLength(100);
    });

    it('renders the pinned item above the list outside the selection', async () => {
        const onPinnedToggle = vi.fn();
        const { onSelectionChange } = renderList({
            pinnedItem: {
                id: 'none',
                label: 'No annotations',
                selected: true,
                onToggle: onPinnedToggle
            }
        });

        const rows = screen.getAllByTestId(/^filter-list(-pinned)?-item$/);
        expect(rows[0]).toHaveAttribute('data-testid', 'filter-list-pinned-item');
        await userEvent.click(screen.getByRole('button', { name: 'Select all' }));

        expect(onSelectionChange).toHaveBeenCalledWith(['id-0', 'id-1', 'id-2']);
    });
});
