import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import FilterListRow from './FilterListRow.svelte';

const defaultProps = {
    item: { id: 'car', label: 'car', selected: true },
    onToggle: vi.fn(),
    testId: 'row'
};

describe('FilterListRow', () => {
    it('calls onToggle and keeps the checkbox in sync with item.selected', async () => {
        const onToggle = vi.fn();
        render(FilterListRow, { ...defaultProps, onToggle });

        await userEvent.click(screen.getByRole('checkbox', { name: 'car' }));

        expect(onToggle).toHaveBeenCalledOnce();
        expect(screen.getByRole('checkbox', { name: 'car' })).toBeChecked();
    });
});
