import { fireEvent, render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import SelectableSvgGroup from './SelectableSvgGroup.svelte';

describe('SelectableSvgGroup', () => {
    it('selects the group on a click inside its box when no child accepts clicks', async () => {
        const onSelect = vi.fn();
        const children = createRawSnippet(() => ({ render: () => '<g></g>' }));
        render(SelectableSvgGroup, {
            groupId: 'annotation-1',
            box: { x: 10, y: 20, width: 30, height: 40 },
            onSelect,
            children
        });

        await fireEvent.click(screen.getByTestId('selectable-svg-group-hit-area'));

        expect(onSelect).toHaveBeenCalledWith('annotation-1');
    });
});
