import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import Menu from './Menu.svelte';

const mocks = vi.hoisted(() => ({
    openClassifiersMenu: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_id: 'collection-id' } }
}));

vi.mock('$lib/hooks/useClassifiers/useClassifiersMenu', () => ({
    useClassifiersMenu: () => ({ openClassifiersMenu: mocks.openClassifiersMenu })
}));

vi.mock('$lib/hooks', () => ({
    useGlobalStorage: () => ({ filteredSampleCount: readable(0) }),
    usePostHog: () => ({ trackEvent: vi.fn() })
}));

vi.mock('$lib/components/Select', async () => ({
    Select: (await import('./MenuSelectStub.test.svelte')).default
}));

const collection: CollectionView = {
    collection_id: 'collection-id',
    dataset_id: 'dataset-id',
    name: 'Images',
    sample_type: 'image',
    created_at: new Date('2026-01-01'),
    updated_at: new Date('2026-01-01')
};

describe('Menu', () => {
    beforeEach(() => mocks.openClassifiersMenu.mockReset());

    it('describes the classifier by its user outcome', async () => {
        render(Menu, {
            props: {
                collection,
                isImages: true,
                hasEmbeddings: true,
                user: { username: 'editor', email: 'editor@example.com', role: 'editor' }
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Find similar images' }));

        expect(mocks.openClassifiersMenu).toHaveBeenCalledOnce();
        expect(screen.queryByText('Few Shot Classifier')).not.toBeInTheDocument();
    });
});
