import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import TagComparisonSelect from './TagComparisonSelect.svelte';

const items = [
    { value: 'tag-a', label: 'Reviewed' },
    { value: 'tag-b', label: 'Priority' }
];

describe('TagComparisonSelect', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('selects a tag without mutating the controlled value', async () => {
        const user = userEvent.setup();
        const onChange = vi.fn();
        render(TagComparisonSelect, { props: { items, selectedIds: [], onChange } });

        await user.click(screen.getByTestId('dataset-distribution-tag-select'));
        await user.click(screen.getByText('Reviewed'));

        expect(onChange).toHaveBeenCalledWith(['tag-a']);
        expect(screen.getByTestId('dataset-distribution-tag-select')).toHaveTextContent(
            'Compare sample tags'
        );
    });

    it('deselects an already selected tag', async () => {
        const user = userEvent.setup();
        const onChange = vi.fn();
        render(TagComparisonSelect, {
            props: { items, selectedIds: ['tag-a'], onChange }
        });

        expect(screen.getByTestId('dataset-distribution-tag-select')).toHaveTextContent(
            '1 tag selected'
        );
        await user.click(screen.getByTestId('dataset-distribution-tag-select'));
        await user.click(screen.getByText('Reviewed'));

        expect(onChange).toHaveBeenCalledWith([]);
    });
});
