import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MultiSelectList from './MultiSelectList.svelte';

const items = [
    { value: 'cat', label: 'Cat' },
    { value: 'dog', label: 'Dog' },
    { value: 'bird', label: 'Bird' }
];

const defaultProps = {
    items,
    selectedIds: [] as string[],
    onChange: vi.fn()
};

describe('MultiSelectList', () => {
    it('renders all items', () => {
        render(MultiSelectList, { props: defaultProps });

        for (const item of items) {
            expect(screen.getByText(item.label)).toBeInTheDocument();
        }
    });

    it('calls onChange with added id when an unselected item is clicked', async () => {
        const onChange = vi.fn();
        render(MultiSelectList, { props: { ...defaultProps, onChange } });

        await fireEvent.click(screen.getByText('Cat'));

        expect(onChange).toHaveBeenCalledWith(['cat']);
    });

    it('calls onChange with removed id when a selected item is clicked', async () => {
        const onChange = vi.fn();
        render(MultiSelectList, {
            props: { ...defaultProps, selectedIds: ['cat', 'dog'], onChange }
        });

        await fireEvent.click(screen.getByText('Cat'));

        expect(onChange).toHaveBeenCalledWith(['dog']);
    });

    it('shows the selected count and Select all / Clear when showSelectAll is true', () => {
        render(MultiSelectList, {
            props: { ...defaultProps, selectedIds: ['cat'], showSelectAll: true }
        });

        expect(screen.getByText('1 of 3 selected')).toBeInTheDocument();
        expect(screen.getByText('Select all')).toBeInTheDocument();
        expect(screen.getByText('Clear')).toBeInTheDocument();
    });

    it('calls onChange with all ids when Select all is clicked', async () => {
        const onChange = vi.fn();
        render(MultiSelectList, {
            props: { ...defaultProps, showSelectAll: true, onChange }
        });

        await fireEvent.click(screen.getByText('Select all'));

        expect(onChange).toHaveBeenCalledWith(['cat', 'dog', 'bird']);
    });

    it('calls onChange with empty array when Clear is clicked', async () => {
        const onChange = vi.fn();
        render(MultiSelectList, {
            props: { ...defaultProps, selectedIds: ['cat', 'dog'], showSelectAll: true, onChange }
        });

        await fireEvent.click(screen.getByText('Clear'));

        expect(onChange).toHaveBeenCalledWith([]);
    });

    it('uses itemNounPlural in the search placeholder', () => {
        render(MultiSelectList, {
            props: { ...defaultProps, itemNounPlural: 'animals' }
        });

        expect(screen.getByPlaceholderText('Search animals...')).toBeInTheDocument();
    });

    it('applies searchTestId to the search input', () => {
        render(MultiSelectList, {
            props: { ...defaultProps, searchTestId: 'my-search' }
        });

        expect(screen.getByTestId('my-search')).toBeInTheDocument();
    });

    it('shows the empty message when no items are provided', () => {
        render(MultiSelectList, { props: { ...defaultProps, items: [], itemNoun: 'animal' } });

        expect(screen.getByText('No animal found.')).toBeInTheDocument();
    });
});
