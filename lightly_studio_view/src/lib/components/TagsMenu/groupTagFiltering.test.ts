import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useGroupTagFilter } from '$lib/hooks/useGroupTagFilter';
import { useTagExclusions } from '$lib/hooks/useTagExclusions';
import TagsMenu from './TagsMenu.svelte';

vi.mock('$lib/hooks', async () => ({
    ...(await vi.importActual('$lib/hooks')),
    usePostHog: () => ({ trackEvent: vi.fn() })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({ default: () => ({ user: undefined }) }));
vi.mock('$lib/api/lightly_studio_local', async () => ({
    ...(await vi.importActual('$lib/api/lightly_studio_local')),
    readTags: vi.fn(() => new Promise(() => {}))
}));

describe('group tag filtering', () => {
    it('cycles filters, combines exclusions and keeps other collections unchanged', async () => {
        const collectionId = 'group-filter-cycle';
        useGlobalStorage().tags.set({
            [collectionId]: [
                {
                    tag_id: 'accepted',
                    name: 'Accepted',
                    created_at: new Date(0),
                    updated_at: new Date(0)
                },
                {
                    tag_id: 'changes',
                    name: 'Needs changes',
                    created_at: new Date(0),
                    updated_at: new Date(0)
                }
            ]
        });
        const filter = useGroupTagFilter(collectionId);
        render(TagsMenu, { collection_id: collectionId, gridType: 'groups' });
        const accepted = screen.getByRole('checkbox', { name: 'Accepted' });
        await fireEvent.click(accepted);
        expect(accepted).toHaveAttribute('aria-checked', 'true');
        expect(get(filter).sample_filter?.tag_ids).toEqual(['accepted']);
        await fireEvent.click(accepted);
        expect(accepted).toHaveAttribute('aria-checked', 'mixed');
        expect(accepted).toHaveAccessibleDescription('Excluded. Activate to clear this filter.');
        const changes = screen.getByRole('checkbox', { name: 'Needs changes' });
        await fireEvent.click(changes);
        await fireEvent.click(changes);
        expect(get(filter).excluded_tag_ids).toEqual(['accepted', 'changes']);
        expect(get(filter).sample_filter?.tag_ids).toEqual([]);
        await fireEvent.click(accepted);
        expect(accepted).toHaveAttribute('aria-checked', 'false');
        expect(get(filter).excluded_tag_ids).toEqual(['changes']);
        expect(get(useTagExclusions('another-collection').excludedTagIds).size).toBe(0);
    });
});
