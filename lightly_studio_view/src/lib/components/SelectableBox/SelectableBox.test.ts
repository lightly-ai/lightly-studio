import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import SelectableBox from './SelectableBox.svelte';

describe('SelectableBox', () => {
    it('renders unselected checkbox', () => {
        render(SelectableBox);

        const checkbox = screen.getByRole('checkbox');

        expect(checkbox).toBeInTheDocument();
        expect(checkbox).not.toBeChecked();
    });

    it('renders selected checkbox', () => {
        render(SelectableBox, {
            props: {
                isSelected: true,
                onSelect: () => {}
            }
        });

        const checkbox = screen.getByRole('checkbox');

        expect(checkbox).toBeInTheDocument();
        expect(checkbox).toBeChecked();
    });

    it('calls onSelect when checkbox is clicked', async () => {
        const onSelect = vi.fn();
        const { container } = render(SelectableBox, {
            props: {
                isSelected: false,
                onSelect
            }
        });

        const checkbox = container.querySelector('button[role="checkbox"]');
        await fireEvent.click(checkbox!);

        expect(onSelect).toHaveBeenCalled();
    });
});
