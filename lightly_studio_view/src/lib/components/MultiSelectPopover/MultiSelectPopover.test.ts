import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import MultiSelectPopover from './MultiSelectPopover.svelte';

const defaultProps = {
    items: [
        { value: 'a', label: 'Alpha' },
        { value: 'b', label: 'Beta' },
        { value: 'c', label: 'Gamma' }
    ],
    selectedIds: ['a', 'b'],
    label: '2 tags selected',
    onChange: vi.fn(),
    itemNoun: 'tag',
    itemNounPlural: 'tags',
    testId: 'tag-picker'
};

describe('MultiSelectPopover', () => {
    it('shows the label on the button', () => {
        render(MultiSelectPopover, { props: defaultProps });

        expect(screen.getByTestId('tag-picker')).toHaveTextContent('2 tags selected');
    });

    it('cannot open while disabled', () => {
        render(MultiSelectPopover, { props: { ...defaultProps, disabled: true } });

        expect(screen.getByTestId('tag-picker')).toBeDisabled();
    });

    it('lists the items and reports a toggled item', async () => {
        const onChange = vi.fn();
        render(MultiSelectPopover, { props: { ...defaultProps, onChange } });

        await fireEvent.click(screen.getByTestId('tag-picker'));
        await fireEvent.click(await screen.findByText('Gamma'));

        expect(onChange).toHaveBeenCalledWith(['a', 'b', 'c']);
    });
});
