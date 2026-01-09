import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import NavigationMenu from './NavigationMenu.svelte';
import { SampleType, type CollectionView } from '$lib/api/lightly_studio_local';
import '@testing-library/jest-dom';
import * as useAuthModule from '$lib/hooks/useAuth/useAuth';
import * as useGlobalStorageModule from '$lib/hooks/useGlobalStorage';
import * as appState from '$app/state';
import type { Page } from '@sveltejs/kit';

vi.mock('$lib/hooks/useAuth/useAuth');
vi.mock('$lib/hooks/useGlobalStorage');

describe('NavigationMenu', () => {
    const mockSetCollection = vi.fn();

    const mockCollection: CollectionView = {
        collection_id: 'test-collection',
        name: 'Test Collection',
        sample_type: SampleType.IMAGE,
        created_at: new Date('2023-01-01'),
        updated_at: new Date('2023-01-02')
    };

    const setup = (userState: { user?: { role: string; email: string } | null } = {}) => {
        const app = appState;
        vi.spyOn(app, 'page', 'get').mockReturnValue({
            route: { id: null, uid: null, pattern: '/collections/[collection_id]/samples' }
        } as unknown as Page<Record<string, string>, string | null>);

        vi.mocked(useAuthModule.default).mockReturnValue({
            token: userState.user ? 'test-token' : undefined,
            isAuthenticated: !!userState.user,
            user: userState.user
        });

        vi.mocked(useGlobalStorageModule.useGlobalStorage).mockReturnValue({
            setCollection: mockSetCollection
        } as any);
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Menu items based on user authentication', () => {
        it('should not render Datasets menu item when user is not authenticated', () => {
            setup({ user: null });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.queryByText('Datasets')).not.toBeInTheDocument();
        });

        it('should render Datasets menu item when user is authenticated', () => {
            setup({
                user: {
                    role: 'viewer',
                    email: 'viewer@example.com'
                }
            });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.getByText('Datasets')).toBeInTheDocument();
        });

        it('should not render Users menu item when user is not authenticated', () => {
            setup({ user: null });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.queryByText('Users')).not.toBeInTheDocument();
        });

        it('should not render Users menu item when user is authenticated but not admin', () => {
            setup({
                user: {
                    role: 'viewer',
                    email: 'viewer@example.com'
                }
            });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.queryByText('Users')).not.toBeInTheDocument();
        });

        it('should render Users menu item when user is authenticated as admin', () => {
            setup({
                user: {
                    role: 'admin',
                    email: 'admin@example.com'
                }
            });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.getByText('Users')).toBeInTheDocument();
        });

        it('should render both Datasets and Users for admin users', () => {
            setup({
                user: {
                    role: 'admin',
                    email: 'admin@example.com'
                }
            });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.getByText('Datasets')).toBeInTheDocument();
            expect(screen.getByText('Users')).toBeInTheDocument();
        });

        it('should render only Datasets for non-admin authenticated users', () => {
            setup({
                user: {
                    role: 'viewer',
                    email: 'viewer@example.com'
                }
            });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.getByText('Datasets')).toBeInTheDocument();
            expect(screen.queryByText('Users')).not.toBeInTheDocument();
        });
    });

    describe('Sample type menu items', () => {
        it('should render Images menu item for IMAGE sample type', () => {
            setup({ user: null });

            render(NavigationMenu, { props: { collection: mockCollection } });

            expect(screen.getByText('Images')).toBeInTheDocument();
        });

        it('should render Videos menu item for VIDEO sample type', () => {
            setup({ user: null });

            const videoCollection: CollectionView = {
                ...mockCollection,
                sample_type: SampleType.VIDEO
            };

            render(NavigationMenu, { props: { collection: videoCollection } });

            expect(screen.getByText('Videos')).toBeInTheDocument();
        });

        it('should render Frames menu item for VIDEO_FRAME sample type', () => {
            setup({ user: null });

            const frameCollection: CollectionView = {
                ...mockCollection,
                sample_type: SampleType.VIDEO_FRAME
            };

            render(NavigationMenu, { props: { collection: frameCollection } });

            expect(screen.getByText('Frames')).toBeInTheDocument();
        });

        it('should render Annotations menu item for ANNOTATION sample type', () => {
            setup({ user: null });

            const annotationCollection: CollectionView = {
                ...mockCollection,
                sample_type: SampleType.ANNOTATION
            };

            render(NavigationMenu, { props: { collection: annotationCollection } });

            expect(screen.getByText('Annotations')).toBeInTheDocument();
        });

        it('should render Captions menu item for CAPTION sample type', () => {
            setup({ user: null });

            const captionCollection: CollectionView = {
                ...mockCollection,
                sample_type: SampleType.CAPTION
            };

            render(NavigationMenu, { props: { collection: captionCollection } });

            expect(screen.getByText('Captions')).toBeInTheDocument();
        });
    });

    describe('Menu items with nested collections', () => {
        it('should render child collection menu items', () => {
            setup({ user: null });

            const collectionWithChildren: CollectionView = {
                ...mockCollection,
                children: [
                    {
                        collection_id: 'child-1',
                        name: 'Child Collection',
                        sample_type: SampleType.VIDEO,
                        created_at: new Date(),
                        updated_at: new Date()
                    }
                ]
            };

            render(NavigationMenu, { props: { collection: collectionWithChildren } });

            expect(screen.getByText('Images')).toBeInTheDocument();
            expect(screen.getByText('Videos')).toBeInTheDocument();
        });

        it('should render all menu items including authentication-dependent ones with children', () => {
            setup({
                user: {
                    role: 'admin',
                    email: 'admin@example.com'
                }
            });

            const collectionWithChildren: CollectionView = {
                ...mockCollection,
                children: [
                    {
                        collection_id: 'child-1',
                        name: 'Child Collection',
                        sample_type: SampleType.VIDEO,
                        created_at: new Date(),
                        updated_at: new Date()
                    }
                ]
            };

            render(NavigationMenu, { props: { collection: collectionWithChildren } });

            expect(screen.getByText('Datasets')).toBeInTheDocument();
            expect(screen.getByText('Users')).toBeInTheDocument();
            expect(screen.getByText('Images')).toBeInTheDocument();
            expect(screen.getByText('Videos')).toBeInTheDocument();
        });
    });
});
