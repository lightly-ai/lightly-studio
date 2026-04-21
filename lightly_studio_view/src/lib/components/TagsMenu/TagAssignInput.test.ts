import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TagAssignInput from './TagAssignInput.svelte';
import type { TagView } from '$lib/services/types';

const options: TagView[] = [
    {
        tag_id: 'tag-1',
        name: 'Vehicle',
        kind: 'sample',
        created_at: new Date('2024-01-01T00:00:00.000Z'),
        updated_at: new Date('2024-01-01T00:00:00.000Z')
    },
    {
        tag_id: 'tag-2',
        name: 'Person',
        kind: 'sample',
        created_at: new Date('2024-01-02T00:00:00.000Z'),
        updated_at: new Date('2024-01-02T00:00:00.000Z')
    }
];

describe('TagAssignInput', () => {
    it('filters options and selects an existing tag from the dropdown', async () => {
        const onSelect = vi.fn();

        render(TagAssignInput, {
            props: {
                options,
                busy: false,
                onSelect
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');

        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'veh' } });
        await fireEvent.click(screen.getByRole('button', { name: 'Vehicle' }));

        expect(onSelect).toHaveBeenCalledWith('Vehicle');
        expect(input).toHaveValue('');
        expect(screen.queryByRole('button', { name: 'Vehicle' })).not.toBeInTheDocument();
    });

    it('creates a trimmed tag name on Enter when there is no exact match', async () => {
        const onSelect = vi.fn();

        render(TagAssignInput, {
            props: {
                options,
                busy: false,
                onSelect
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');

        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: '  New Tag  ' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onSelect).toHaveBeenCalledWith('New Tag');
        expect(input).toHaveValue('');
    });

    it('clears the query and closes the dropdown on Escape', async () => {
        render(TagAssignInput, {
            props: {
                options,
                busy: false,
                onSelect: vi.fn()
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');

        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'veh' } });

        expect(screen.getByRole('button', { name: 'Vehicle' })).toBeInTheDocument();

        await fireEvent.keyDown(input, { key: 'Escape' });

        expect(input).toHaveValue('');
        expect(screen.queryByRole('button', { name: 'Vehicle' })).not.toBeInTheDocument();
        expect(screen.queryByText('Create "veh"')).not.toBeInTheDocument();
    });
});
