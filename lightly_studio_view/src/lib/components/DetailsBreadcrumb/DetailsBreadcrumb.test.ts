import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuth from '$lib/hooks/useAuth/useAuth';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import DetailsBreadcrumb from './DetailsBreadcrumb.svelte';

vi.mock('$lib/hooks/useAuth/useAuth');
vi.mock('$app/state', () => ({
    page: {
        params: { dataset_id: 'dataset-1', collection_type: 'video', collection_id: 'collection-1' }
    }
}));

// Video and frame details both render this breadcrumb.
const props = {
    rootCollection: { name: 'Roads' } as CollectionView,
    section: 'Videos',
    subsection: 'Video',
    index: 2,
    totalCount: 7,
    navigateTo: (collectionId: string) => `/videos/${collectionId}`
};

const loginAs = (role: 'labeler' | 'viewer' | undefined) =>
    vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: !!role,
        user: role ? { role, email: 'a@b.c' } : undefined
    } as ReturnType<typeof useAuth>);

describe('DetailsBreadcrumb', () => {
    beforeEach(() => vi.clearAllMocks());

    it('shows the dataset crumbs as plain text for a labeler', () => {
        loginAs('labeler');
        render(DetailsBreadcrumb, { props });

        const breadcrumb = screen.getByTestId('details-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Home');
        expect(breadcrumb).toHaveTextContent('Roads');
        expect(breadcrumb).toHaveTextContent('Videos');
        expect(breadcrumb).toHaveTextContent('Video 2 of 7');
        expect(breadcrumb.querySelectorAll('a[href]')).toHaveLength(0);
    });

    it.each(['viewer', undefined] as const)('keeps the dataset links for role %s', (role) => {
        loginAs(role);
        render(DetailsBreadcrumb, { props });

        const hrefs = [...screen.getByTestId('details-breadcrumb').querySelectorAll('a[href]')].map(
            (link) => link.getAttribute('href')
        );
        expect(hrefs).toHaveLength(3);
        expect(hrefs[2]).toBe('/videos/collection-1');
    });
});
