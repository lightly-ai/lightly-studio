import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useTags } from '$lib/hooks';
import ClearAllFiltersButton from './ClearAllFiltersButton.svelte';

describe('ClearAllFiltersButton', () => {
    it('shows and clears active parent image tags in the captions view', async () => {
        const tags = useTags({ collection_id: 'parent-images-id', autoLoad: false });
        tags.setTagSelected('tag-1', true);

        render(ClearAllFiltersButton, {
            props: {
                collectionId: 'parent-images-id',
                isCaptions: true,
                isImages: false,
                isVideos: false,
                isVideoFrames: false
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Clear all filters' }));

        expect(get(tags.tagsSelected).size).toBe(0);
        expect(screen.queryByRole('button', { name: 'Clear all filters' })).toBeNull();
    });
});
