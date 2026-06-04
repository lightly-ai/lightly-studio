import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import GridHeaderSelectAllButton from './GridHeaderSelectAllButton.svelte';

describe('GridHeaderSelectAllButton', () => {
    const buildProps = (overrides: Partial<Parameters<typeof render>[1]['props']> = {}) => ({
        checked: false,
        onSelectAll: vi.fn().mockResolvedValue(undefined),
        onDeselectAll: vi.fn(),
        ...overrides
    });

    it('renders the checkbox unchecked with "Select all" label by default', () => {
        render(GridHeaderSelectAllButton, { props: buildProps() });

        const checkbox = screen.getByTestId('select-all-button');
        expect(checkbox).toBeInTheDocument();
        expect(checkbox).toHaveAttribute('aria-checked', 'false');
        expect(checkbox).toHaveAttribute('aria-label', 'Select all');
        expect(screen.getByText('Select all')).toBeInTheDocument();
    });

    it('renders the checkbox checked when checked=true', () => {
        render(GridHeaderSelectAllButton, { props: buildProps({ checked: true }) });

        const checkbox = screen.getByTestId('select-all-button');
        expect(checkbox).toHaveAttribute('aria-checked', 'true');
        expect(checkbox).toHaveAttribute('aria-label', 'Deselect all');
    });

    it('calls onSelectAll when toggled on', async () => {
        const props = buildProps();
        render(GridHeaderSelectAllButton, { props });

        await fireEvent.click(screen.getByTestId('select-all-button'));

        expect(props.onSelectAll).toHaveBeenCalledTimes(1);
        expect(props.onDeselectAll).not.toHaveBeenCalled();
    });

    it('calls onDeselectAll when toggled off', async () => {
        const props = buildProps({ checked: true });
        render(GridHeaderSelectAllButton, { props });

        await fireEvent.click(screen.getByTestId('select-all-button'));

        expect(props.onDeselectAll).toHaveBeenCalledTimes(1);
        expect(props.onSelectAll).not.toHaveBeenCalled();
    });

    it('clicking the label also toggles the checkbox', async () => {
        const props = buildProps();
        render(GridHeaderSelectAllButton, { props });

        await fireEvent.click(screen.getByText('Select all'));

        expect(props.onSelectAll).toHaveBeenCalledTimes(1);
    });
});
