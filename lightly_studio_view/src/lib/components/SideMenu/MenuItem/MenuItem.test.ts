import MenuItem from './MenuItem.svelte';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

describe('MenuItem', () => {
    const props = {
        name: 'test-label',
        checked: false,
        onCheckedChange: vi.fn()
    };

    it('renders the item name', () => {
        render(MenuItem, props);

        expect(screen.getByText(props.name)).toBeInTheDocument();
    });

    it('renders a checkbox', () => {
        render(MenuItem, props);

        expect(screen.getByRole('checkbox')).toBeInTheDocument();
    });

    it('reflects checked state', () => {
        render(MenuItem, { ...props, checked: true });

        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('calls onCheckedChange when checkbox is clicked', async () => {
        const onCheckedChange = vi.fn();
        render(MenuItem, { ...props, onCheckedChange });

        await userEvent.click(screen.getByRole('checkbox'));

        expect(onCheckedChange).toHaveBeenCalledOnce();
    });

    it('sets title attribute to item name', () => {
        render(MenuItem, props);

        expect(screen.getByTitle(props.name)).toBeInTheDocument();
    });

    it('does not render color marker by default', () => {
        render(MenuItem, props);

        expect(screen.queryByTestId('color-marker-test-label')).not.toBeInTheDocument();
    });

    it('renders color marker when showColorMarker is true', () => {
        render(MenuItem, { ...props, showColorMarker: true });

        expect(screen.queryByTestId('color-marker-test-label')).toBeInTheDocument();
    });
});
