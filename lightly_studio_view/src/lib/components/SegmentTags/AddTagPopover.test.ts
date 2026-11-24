import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import AddTagPopover from './AddTagPopover.svelte';

describe('AddTagPopover', () => {
    it('creates a tag using the trimmed value shown in the UI', async () => {
        const onSelect = vi.fn();

        render(AddTagPopover, {
            props: {
                options: [],
                attachedTagNames: new Set<string>(),
                busy: false,
                onSelect
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Add tag' }));
        await fireEvent.input(screen.getByPlaceholderText('Tag name…'), {
            target: { value: '  New Tag  ' }
        });
        await fireEvent.click(screen.getByRole('option', { name: /Create:\s*New Tag/i }));

        expect(onSelect).toHaveBeenCalledWith('New Tag');
    });

    it('does not offer create for an attached tag with different casing', async () => {
        render(AddTagPopover, {
            props: {
                options: [],
                attachedTagNames: new Set(['MyTag']),
                busy: false,
                onSelect: vi.fn()
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Add tag' }));
        await fireEvent.input(screen.getByPlaceholderText('Tag name…'), {
            target: { value: 'mytag' }
        });

        expect(screen.queryByText('Create:')).not.toBeInTheDocument();
    });

    it('starts with an empty name after a tag was added', async () => {
        const onSelect = vi.fn();
        render(AddTagPopover, {
            props: { options: [], attachedTagNames: new Set<string>(), busy: false, onSelect }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Add tag' }));
        await fireEvent.input(screen.getByPlaceholderText('Tag name…'), {
            target: { value: 'occluded' }
        });
        await fireEvent.click(screen.getByRole('option', { name: /Create:\s*occluded/i }));
        await fireEvent.click(screen.getByRole('button', { name: 'Add tag' }));

        expect(screen.getByPlaceholderText('Tag name…')).toHaveValue('');
    });
});
