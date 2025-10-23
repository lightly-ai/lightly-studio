import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import SelectList from './SelectList.svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { createRawSnippet } from 'svelte';

describe('SelectList', () => {
    const mockItems = [
        { value: 'item1', label: 'Item 1' },
        { value: 'item2', label: 'Item 2' },
        { value: 'item3', label: 'Item 3' }
    ];

    it('renders combobox', () => {
        render(SelectList, {
            props: {
                items: mockItems
            }
        });

        expect(screen.getByTestId('select-list-trigger')).toBeInTheDocument();
    });

    it('renders with custom label', () => {
        const label = 'Choose a cat';
        render(SelectList, {
            props: {
                items: mockItems,
                label
            }
        });

        const button = screen.getByTestId('select-list-trigger');
        expect(button.textContent).toContain(label);
    });

    it('renders with custom placeholder', async () => {
        const placeholder = 'Search frameworks...';
        const user = userEvent.setup();

        render(SelectList, {
            props: {
                items: mockItems,
                placeholder
            }
        });
        await user.click(screen.getByTestId('select-list-trigger'));

        await waitFor(() => expect(screen.getByTestId('select-list-input')).toBeInTheDocument());
        expect(screen.getByTestId('select-list-input')).toHaveAttribute('placeholder', placeholder);
    });

    it('renders with default notFound text', async () => {
        const user = userEvent.setup();
        render(SelectList, {
            props: {
                items: mockItems
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        await user.type(screen.getByTestId('select-list-input'), 'nonexistent');

        expect(screen.getByText('Item not found')).toBeInTheDocument();
    });

    it('renders with custom notFound snippet', async () => {
        const user = userEvent.setup();
        const textNotFound = 'No frameworks found';

        const notFound = createRawSnippet(() => {
            return {
                render: () => `
                    <h1 data-testid="select-list-empty">${textNotFound}</h1>
                `
            };
        });

        render(SelectList, {
            props: {
                items: mockItems,
                notFound
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        await waitFor(() => expect(screen.getByTestId('select-list-input')).toBeInTheDocument());

        await user.type(screen.getByTestId('select-list-input'), 'nonexistent');

        expect(screen.getByRole('heading', { name: textNotFound })).toBeInTheDocument();
    });

    it('renders all items in the list', async () => {
        const user = userEvent.setup();
        render(SelectList, {
            props: {
                items: mockItems
            }
        });
        await user.click(screen.getByTestId('select-list-trigger'));

        mockItems.forEach((item) => {
            const option = screen.getByRole('option', { name: item.label });
            expect(option).toBeInTheDocument();
            expect(option).toHaveAttribute('data-value', item.value);
        });
    });

    it('selects an item when clicked', async () => {
        const user = userEvent.setup();
        const onSelect = vi.fn();
        render(SelectList, {
            props: {
                items: mockItems,
                onSelect
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        const itemToSelect = screen.getByRole('option', { name: mockItems[1].label });
        await user.click(itemToSelect);

        expect(screen.getByTestId('select-list-trigger')).toHaveTextContent(mockItems[1].label);
        expect(onSelect).toHaveBeenCalledWith(mockItems[1]);
    });

    it('shows selected value', () => {
        const selectedItem = mockItems[2];
        render(SelectList, {
            props: {
                items: mockItems,
                selectedItem
            }
        });

        expect(screen.getByTestId('select-list-trigger')).toHaveTextContent(selectedItem.label);
    });

    it('creates new item when pressing Enter with unique label', async () => {
        const user = userEvent.setup();
        const onSelect = vi.fn();
        const items = [...mockItems];

        render(SelectList, {
            props: {
                items,
                onSelect
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        const input = screen.getByTestId('select-list-input');
        await user.type(input, 'New Item{Enter}');

        await waitFor(() => {
            expect(onSelect).toHaveBeenCalledWith({ value: 'New Item', label: 'New Item' });
        });
    });

    it('selects existing item when pressing Enter with case-insensitive match', async () => {
        const user = userEvent.setup();
        const onSelect = vi.fn();
        const items = [
            { value: 'Dog', label: 'Dog' },
            { value: 'Cat', label: 'Cat' },
            { value: 'Bird', label: 'Bird' }
        ];

        render(SelectList, {
            props: {
                items,
                onSelect
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        const input = screen.getByTestId('select-list-input');
        await user.type(input, 'dog{Enter}');

        await waitFor(() => {
            // Should select the existing "Dog" label, not create "dog"
            expect(onSelect).toHaveBeenCalledWith({ value: 'Dog', label: 'Dog' });
        });
    });

    it('selects existing item when pressing Enter with different casing', async () => {
        const user = userEvent.setup();
        const onSelect = vi.fn();
        const items = [
            { value: 'BMW', label: 'BMW' },
            { value: 'Audi', label: 'Audi' }
        ];

        render(SelectList, {
            props: {
                items,
                onSelect
            }
        });

        await user.click(screen.getByTestId('select-list-trigger'));
        const input = screen.getByTestId('select-list-input');
        await user.type(input, 'bmw{Enter}');

        await waitFor(() => {
            expect(onSelect).toHaveBeenCalledWith({ value: 'BMW', label: 'BMW' });
        });
    });
});
