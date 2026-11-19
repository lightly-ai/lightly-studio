import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuth from '$lib/hooks/useAuth/useAuth';
import type { Collection } from '$lib/services/types';
import SampleDetailsBreadcrumb from './SampleDetailsBreadcrumb.svelte';

vi.mock('$lib/hooks/useAuth/useAuth');
vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'image',
            collection_id: 'collection-1',
            sampleId: 'sample-1'
        }
    }
}));
vi.mock('$lib/hooks/useAdjacentImages/useAdjacentImages', () => ({
    useAdjacentImages: () => ({
        query: { data: { current_sample_position: 3, total_count: 10 } }
    })
}));

const rootCollection = { name: 'Roads' } as Collection;

const loginAs = (role: 'labeler' | 'editor' | undefined) =>
    vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: !!role,
        user: role ? { role, email: 'a@b.c' } : undefined
    } as ReturnType<typeof useAuth>);

describe('SampleDetailsBreadcrumb', () => {
    beforeEach(() => vi.clearAllMocks());

    it('sends a labeler home to Projects and shows the other crumbs as plain text', () => {
        loginAs('labeler');
        render(SampleDetailsBreadcrumb, { props: { rootCollection } });

        const breadcrumb = screen.getByTestId('sample-details-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Home');
        expect(breadcrumb).toHaveTextContent('Roads');
        expect(breadcrumb).toHaveTextContent('Samples');
        expect(breadcrumb).toHaveTextContent('Sample 3 of 10');
        const home = breadcrumb.querySelectorAll('a[href]');
        expect(home).toHaveLength(1);
        expect(home[0]).toHaveTextContent('Home');
        expect(home[0]).toHaveAttribute('href', '/workspace/projects');
        expect(home[0]).toHaveAttribute('data-sveltekit-reload');
    });

    it.each(['editor', undefined] as const)('keeps the dataset links for role %s', (role) => {
        loginAs(role);
        render(SampleDetailsBreadcrumb, { props: { rootCollection } });

        const breadcrumb = screen.getByTestId('sample-details-breadcrumb');
        expect(breadcrumb.querySelectorAll('a[href]')).toHaveLength(3);
    });
});
