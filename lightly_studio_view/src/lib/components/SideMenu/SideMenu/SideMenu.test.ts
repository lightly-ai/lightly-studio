import { describe, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SideMenu from './SideMenu.svelte';
import type { ComponentProps } from 'svelte';
import type { MenuItemType } from '../types';
import { readable } from 'svelte/store';

describe('SideMenu', () => {
    const items: MenuItemType[] = [
        { id: '1', name: 'Item 1' },
        { id: '2', name: 'Item 2' }
    ];
    const testId = 'side-menu-container';
    const onChangeSelectedItems = vi.fn();
    const menuProps: ComponentProps<typeof SideMenu> = {
        items: readable(items),
        onChangeSelectedItems,
        containerProps: { 'data-testid': testId }
    };

    it('renders SideMenu component', () => {
        render(SideMenu, menuProps);
        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });

    it('renders correct number of MenuItem components', () => {
        render(SideMenu, menuProps);
        const menuItems = screen.getAllByRole('checkbox');
        expect(menuItems).toHaveLength(items.length);
    });

    it('calls onChangeSelectedItems when a MenuItem is checked', async () => {
        render(SideMenu, menuProps);
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith(['1']);
    });

    it('calls onChangeSelectedItems with correct ids when multiple MenuItems are checked', async () => {
        render(SideMenu, menuProps);
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        await checkboxes[1].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith(['1', '2']);
    });

    it('calls onChangeSelectedItems with correct ids when a MenuItem is unchecked', async () => {
        render(SideMenu, menuProps);
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        await checkboxes[0].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith([]);
    });
});
