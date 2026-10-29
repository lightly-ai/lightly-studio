import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import FilterList from './FilterList.svelte';
import FilterListTrailingTestWrapper from './FilterListTrailingTestWrapper.test.svelte';

const items = [
    { id: 'car', label: 'car', selected: true, count: '3 of 8' },
    { id: 'cat', label: 'cat', selected: false },
    { id: 'deer', label: 'deer', selected: false },
    { id: 'dog', label: 'dog', selected: false },
    { id: 'fox', label: 'fox', selected: false },
    { id: 'owl', label: 'owl', selected: false }
];

const defaultProps = { items, onToggle: vi.fn(), onSelectionChange: vi.fn() };

describe('FilterList', () => {
    it('reserves the trailing space on the pinned row so counts line up', () => {
        render(FilterListTrailingTestWrapper, {
            props: {
                items: [{ id: 'car', label: 'car', selected: false, count: '1 of 1' }],
                pinnedItem: {
                    id: 'none',
                    label: 'No annotations',
                    selected: false,
                    count: '2 of 2',
                    onToggle: vi.fn()
                }
            }
        });

        expect(screen.getByTestId('trailing-car')).toBeVisible();
        const spacer = screen.getByTestId('trailing-none').parentElement;
        expect(spacer).toHaveClass('invisible');
        expect(spacer).toHaveAttribute('aria-hidden', 'true');
    });

    it('renders the first 50 rows of a long list and shows more on request', async () => {
        const manyItems = Array.from({ length: 120 }, (_, index) => ({
            id: `value-${index}`,
            label: `value-${index}`,
            selected: false
        }));
        render(FilterList, { props: { ...defaultProps, items: manyItems } });

        expect(screen.getAllByRole('checkbox')).toHaveLength(50);
        await fireEvent.click(screen.getByRole('button', { name: 'Show 50 more of 70' }));
        expect(screen.getAllByRole('checkbox')).toHaveLength(100);
    });

    it('searches all rows of a long list, not only the rendered ones', async () => {
        const manyItems = Array.from({ length: 120 }, (_, index) => ({
            id: `value-${index}`,
            label: `value-${index}`,
            selected: false
        }));
        render(FilterList, { props: { ...defaultProps, items: manyItems } });

        await fireEvent.input(screen.getByLabelText('Search'), { target: { value: 'value-119' } });

        expect(screen.getByText('value-119')).toBeInTheDocument();
    });

    it('renders a checkbox and the count of each item', () => {
        render(FilterList, { props: defaultProps });

        expect(screen.getByRole('checkbox', { name: 'car' })).toBeChecked();
        expect(screen.getByRole('checkbox', { name: 'cat' })).not.toBeChecked();
        expect(screen.getByText('3 of 8')).toBeInTheDocument();
    });

    it('filters the rows by the search text', async () => {
        render(FilterList, { props: defaultProps });

        await fireEvent.input(screen.getByLabelText('Search'), { target: { value: 'ca' } });

        expect(screen.getByText('car')).toBeInTheDocument();
        expect(screen.getByText('cat')).toBeInTheDocument();
        expect(screen.queryByText('dog')).not.toBeInTheDocument();
    });

    it('hides the search box for short lists', () => {
        render(FilterList, { props: { ...defaultProps, items: items.slice(0, 2) } });

        expect(screen.queryByLabelText('Search')).not.toBeInTheDocument();
    });

    it('selects only the matching items with "Select all" while searching', async () => {
        const onSelectionChange = vi.fn();
        render(FilterList, { props: { ...defaultProps, onSelectionChange } });

        await fireEvent.input(screen.getByLabelText('Search'), { target: { value: 'o' } });
        await fireEvent.click(screen.getByRole('button', { name: 'Select all' }));

        expect(onSelectionChange).toHaveBeenCalledWith(['car', 'dog', 'fox', 'owl']);
    });

    it('renders the pinned item above the list and toggles it separately', async () => {
        const onToggle = vi.fn();
        const pinnedToggle = vi.fn();
        render(FilterList, {
            props: {
                ...defaultProps,
                onToggle,
                pinnedItem: {
                    id: 'none',
                    label: 'No annotations',
                    selected: false,
                    count: '2 of 5',
                    onToggle: pinnedToggle
                }
            }
        });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'No annotations' }));

        expect(pinnedToggle).toHaveBeenCalledOnce();
        expect(onToggle).not.toHaveBeenCalled();
    });

    it('empties the selection with "Clear"', async () => {
        const onSelectionChange = vi.fn();
        render(FilterList, { props: { ...defaultProps, onSelectionChange } });

        await fireEvent.click(screen.getByRole('button', { name: 'Clear' }));

        expect(onSelectionChange).toHaveBeenCalledWith([]);
        expect(screen.queryByRole('button', { name: 'Exclude' })).not.toBeInTheDocument();
    });
});
