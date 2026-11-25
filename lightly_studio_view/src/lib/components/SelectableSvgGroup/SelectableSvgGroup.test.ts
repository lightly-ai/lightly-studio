import { fireEvent, render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SelectableSvgGroup from './SelectableSvgGroup.svelte';

const defaultProps = {
    groupId: 'box-1',
    box: { x: 1, y: 2, width: 10, height: 20 },
    children: createRawSnippet(() => ({ render: () => '<rect></rect>' }))
};

const renderGroup = () => {
    const onSelect = vi.fn();
    render(SelectableSvgGroup, { props: { ...defaultProps, onSelect } });
    return { onSelect, group: screen.getByTestId('selectable-svg-group') };
};

const markHandled = (event: KeyboardEvent) => event.preventDefault();

describe('SelectableSvgGroup', () => {
    afterEach(() => {
        window.removeEventListener('keydown', markHandled, true);
    });

    it('selects the group on Enter and Space', async () => {
        const { onSelect, group } = renderGroup();

        await fireEvent.keyDown(group, { key: 'Enter' });
        await fireEvent.keyDown(group, { key: ' ' });

        expect(onSelect).toHaveBeenNthCalledWith(1, 'box-1');
        expect(onSelect).toHaveBeenNthCalledWith(2, 'box-1');
    });

    it('ignores a key that another handler already handled', async () => {
        window.addEventListener('keydown', markHandled, true);
        const { onSelect, group } = renderGroup();

        await fireEvent.keyDown(group, { key: 'Enter' });

        expect(onSelect).not.toHaveBeenCalled();
    });
});
