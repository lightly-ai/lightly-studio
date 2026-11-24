import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TagChips from './TagChips.svelte';

const tags = [
    { tag_id: 't1', name: 'occluded' },
    { tag_id: 't2', name: 'blurry' }
];

describe('TagChips', () => {
    it('shows the tag names without remove buttons when read-only', () => {
        render(TagChips, { tags });

        const names = screen.getAllByTestId('segment-tag-name').map((el) => el.textContent);
        expect(names).toEqual(['occluded', 'blurry']);
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('removes a tag by its id', async () => {
        const onRemove = vi.fn();
        render(TagChips, { tags, onRemove });

        await fireEvent.click(screen.getByRole('button', { name: 'Remove tag blurry' }));

        expect(onRemove).toHaveBeenCalledWith('t2');
    });

    it('disables the remove button while its removal is pending', () => {
        render(TagChips, { tags, onRemove: vi.fn(), removingTagIds: new Set(['t1']) });

        expect(screen.getByRole('button', { name: 'Remove tag occluded' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Remove tag blurry' })).toBeEnabled();
    });

    it('shows the full name of a long tag on hover', () => {
        const name = 'a very long tag name that does not fit into the side panel';
        render(TagChips, { tags: [{ tag_id: 't3', name }] });

        expect(screen.getByTestId('segment-tag-name')).toHaveAttribute('title', name);
    });
});
