import { render, fireEvent, screen } from '@testing-library/svelte';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { useSettings } from '$lib/hooks/useSettings';
import ToolRail from './ToolRail.svelte';

const { settingsStore } = useSettings();

function setToolShortcuts(select: string, createCuboid: string) {
    settingsStore.update((settings) => ({
        ...settings,
        key_point_cloud_select: select,
        key_point_cloud_create_cuboid: createCuboid
    }));
}

describe('ToolRail', () => {
    afterEach(() => {
        setToolShortcuts('q', 'c');
    });

    it('offers only the select and create tools', () => {
        render(ToolRail);

        const labels = screen.getAllByRole('button').map((button) => button.ariaLabel);
        expect(labels).toEqual(['Select cuboid', 'Create cuboid']);
    });

    it('selects each tool with its default shortcut', async () => {
        const onToolChange = vi.fn();
        render(ToolRail, { props: { onToolChange } });

        await fireEvent.keyDown(window, { key: 'c' });
        await fireEvent.keyDown(window, { key: 'q' });

        expect(onToolChange.mock.calls).toEqual([['create-cuboid'], ['select']]);
    });

    it('uses the configured shortcut and shows it in the tooltip', async () => {
        setToolShortcuts('z', 'n');
        const onToolChange = vi.fn();
        render(ToolRail, { props: { onToolChange } });

        await fireEvent.pointerEnter(screen.getByLabelText('Create cuboid').parentElement!);
        expect(screen.getByRole('tooltip')).toHaveTextContent('Press N to create');
        await fireEvent.keyDown(window, { key: 'n' });

        expect(onToolChange).toHaveBeenCalledWith('create-cuboid');
    });

    it('ignores a tool shortcut recorded on a camera navigation key', async () => {
        setToolShortcuts('w', 'c');
        const onToolChange = vi.fn();
        render(ToolRail, { props: { onToolChange } });

        await fireEvent.keyDown(window, { key: 'w' });

        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('ignores the shortcut while typing in an input', async () => {
        const onToolChange = vi.fn();
        render(ToolRail, { props: { onToolChange } });
        const input = document.createElement('input');
        document.body.append(input);

        await fireEvent.keyDown(input, { key: 'c' });

        expect(onToolChange).not.toHaveBeenCalled();
        input.remove();
    });
});
