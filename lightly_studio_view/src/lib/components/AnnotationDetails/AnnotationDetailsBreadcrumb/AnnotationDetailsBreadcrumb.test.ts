import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuth from '$lib/hooks/useAuth/useAuth';
import type { Collection } from '$lib/services/types';
import AnnotationDetailsBreadcrumb from './AnnotationDetailsBreadcrumb.svelte';

vi.mock('$lib/hooks/useAuth/useAuth');
vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1',
            collection_type: 'image',
            collection_id: 'collection-1',
            annotationId: 'annotation-1'
        }
    }
}));
vi.mock('$lib/hooks/useAdjacentAnnotations/useAdjacentAnnotations', () => ({
    useAdjacentAnnotations: () => ({
        query: { data: { current_sample_position: 4, total_count: 9 } }
    })
}));

const rootCollection = { name: 'Roads' } as Collection;

const loginAs = (role: 'labeler' | 'admin' | undefined) =>
    vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: !!role,
        user: role ? { role, email: 'a@b.c' } : undefined
    } as ReturnType<typeof useAuth>);

const links = () =>
    screen.getByTestId('annotation-details-position').closest('nav')!.querySelectorAll('a[href]');

describe('AnnotationDetailsBreadcrumb', () => {
    beforeEach(() => vi.clearAllMocks());

    it('sends a labeler home to Projects and shows the other crumbs as plain text', () => {
        loginAs('labeler');
        render(AnnotationDetailsBreadcrumb, { props: { rootCollection } });

        const nav = screen.getByTestId('annotation-details-position').closest('nav')!;
        expect(nav).toHaveTextContent('Home');
        expect(nav).toHaveTextContent('Roads');
        expect(nav).toHaveTextContent('Annotations');
        expect(nav).toHaveTextContent('Sample 4 of 9');
        const home = nav.querySelectorAll('a[href]');
        expect(home).toHaveLength(1);
        expect(home[0]).toHaveTextContent('Home');
        expect(home[0]).toHaveAttribute('href', '/workspace/projects');
        expect(home[0]).toHaveAttribute('data-sveltekit-reload');
    });

    it.each(['admin', undefined] as const)('keeps the dataset links for role %s', (role) => {
        loginAs(role);
        render(AnnotationDetailsBreadcrumb, { props: { rootCollection } });

        expect(links()).toHaveLength(3);
    });
});
