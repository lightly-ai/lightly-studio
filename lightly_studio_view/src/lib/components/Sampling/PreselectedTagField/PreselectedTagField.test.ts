import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PreselectedTagField from './PreselectedTagField.svelte';

const tags = [
    { tag_id: 'tag-1', name: 'First batch', kind: 'sample' as const },
    { tag_id: 'tag-2', name: 'Second batch', kind: 'sample' as const }
];

describe('PreselectedTagField', () => {
    it('selects a sample tag', async () => {
        const onValueChange = vi.fn();
        render(PreselectedTagField, { tags, onValueChange });

        await fireEvent.keyDown(screen.getByTestId('sampling-preselected-tag-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByText('First batch'));

        expect(onValueChange).toHaveBeenCalledWith('tag-1');
    });

    it('explains when no sample tags are available', () => {
        render(PreselectedTagField, { tags: [], onValueChange: vi.fn() });

        expect(screen.getByTestId('sampling-preselected-tag-select')).toHaveTextContent(
            'No sample tags available'
        );
    });
});
