import { describe, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SideMenu from './SideMenu.svelte';
import type { MenuItemType } from '../types';
import { readable } from 'svelte/store';

describe('SideMenu', () => {
    const items: MenuItemType[] = [
        { id: '1', name: 'Item 1' },
        { id: '2', name: 'Item 2' }
    ];
    const testId = 'side-menu-container';

    it('renders SideMenu component', () => {
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems: vi.fn(),
            containerProps: { 'data-testid': testId }
        });
        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });

    it('renders correct number of MenuItem components', () => {
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems: vi.fn(),
            containerProps: { 'data-testid': testId }
        });
        const menuItems = screen.getAllByRole('checkbox');
        expect(menuItems).toHaveLength(items.length);
    });

    it('calls onChangeSelectedItems when a MenuItem is checked', async () => {
        const onChangeSelectedItems = vi.fn();
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems,
            containerProps: { 'data-testid': testId }
        });
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith(['1']);
    });

    it('calls onChangeSelectedItems with correct ids when multiple MenuItems are checked', async () => {
        const onChangeSelectedItems = vi.fn();
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems,
            containerProps: { 'data-testid': testId }
        });
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        await checkboxes[1].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith(['1', '2']);
    });

    it('calls onChangeSelectedItems with correct ids when a MenuItem is unchecked', async () => {
        const onChangeSelectedItems = vi.fn();
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems,
            containerProps: { 'data-testid': testId }
        });
        const checkboxes = screen.getAllByRole('checkbox');
        await checkboxes[0].click();
        await checkboxes[0].click();
        expect(onChangeSelectedItems).toHaveBeenCalledWith([]);
    });

    it('merges containerProps.class with default classes', () => {
        render(SideMenu, {
            items: readable(items),
            onChangeSelectedItems: vi.fn(),
            containerProps: { 'data-testid': testId, class: 'custom-class' }
        });
        const container = screen.getByTestId(testId);
        expect(container).toHaveClass('w-full', 'space-y-2', 'overflow-hidden', 'custom-class');
    });
});
