import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import ToolRail from './ToolRail.svelte';

describe('ToolRail', () => {
    it('selects the create cuboid tool with the C shortcut', async () => {
        const onToolChange = vi.fn();
        render(ToolRail, { props: { onToolChange } });

        await fireEvent.keyDown(window, { key: 'c' });

        expect(onToolChange).toHaveBeenCalledWith('create-cuboid');
    });
});
