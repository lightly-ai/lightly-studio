import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import Header from './Header.svelte';
import * as appState from '$app/state';
import '@testing-library/jest-dom';
import { Page } from '@sveltejs/kit';
import type { ReversibleAction } from '$lib/hooks/useGlobalStorage';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';

import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
import useAuth from '$lib/hooks/useAuth/useAuth';
import { toast } from 'svelte-sonner';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const { globalStorage } = vi.hoisted(() => ({
    globalStorage: { current: {} as Record<string, unknown> }
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => globalStorage.current
}));

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        readRootCollection: vi.fn()
    };
});

vi.mock('$lib/hooks/useCollection/useCollection', () => {
    return {
        useCollection: vi.fn(),
        useCollectionWithChildren: vi.fn()
    };
});

vi.mock('$lib/hooks/useHasEmbeddings/useHasEmbeddings', () => ({
    useHasEmbeddings: vi.fn()
}));

vi.mock('$lib/hooks/useAuth/useAuth', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        default: vi.fn()
    };
});

describe('Header', () => {
    const mockCollection: CollectionView = {
        collection_id: 'test-collection',
        name: 'Test Collection',
        sample_type: 'image',
        created_at: new Date('2023-01-01'),
        updated_at: new Date('2023-01-02')
    };

    interface SetupProps {
        isEditingMode: boolean;
        reversibleActions?: ReversibleAction[];
        executeReversibleAction?: vi.Mock;
        collection?: CollectionView;
        user?: { username: string; email: string; role: string } | null;
    }

    const mockPage = (props: SetupProps) => {
        const setIsEditingModeSpy = vi.fn();
        const executeReversibleActionSpy = props.executeReversibleAction || vi.fn();
        globalStorage.current = {
            isEditingMode: writable(props?.isEditingMode),
            setIsEditingMode: setIsEditingModeSpy,
            reversibleActions: writable(props.reversibleActions || []),
            executeReversibleAction: executeReversibleActionSpy
        };
        vi.spyOn(appState, 'page', 'get').mockReturnValue({
            data: {},
            params: {
                collection_id: props.collection?.collection_id || 'test-collection'
            },
            route: {
                id: null,
                uid: null,
                pattern: '/datasets/[dataset_id]/[collection_type]/[collection_id]/images'
            }
        } as unknown as Page<Record<string, string>, string | null>);
        return { setIsEditingModeSpy, executeReversibleActionSpy };
    };

    const setup = (props: SetupProps = { isEditingMode: false }) => {
        const { setIsEditingModeSpy, executeReversibleActionSpy } = mockPage(props);

        (useCollectionWithChildren as unknown as vi.Mock).mockReturnValue({
            collection: readable({
                isSuccess: true,
                data: {
                    sample_type: 'image',
                    collection_id: props.collection?.collection_id || 'test-collection',
                    name: 'Root Collection',
                    children: []
                }
            })
        });

        useHasEmbeddings.mockReturnValue(
            readable({
                data: true,
                isLoading: false,
                error: null
            })
        );

        (useAuth as unknown as vi.Mock).mockReturnValue({
            user: props.user ?? null,
            token: props.user ? 'mock-token' : undefined,
            isAuthenticated: !!props.user
        });

        return {
            setIsEditingModeSpy,
            executeReversibleActionSpy,
            collection: props.collection || mockCollection
        };
    };

    beforeEach(setup);

    describe('Edit Mode button', () => {
        it('renders Edit Annotations button when not in editing mode', () => {
            const { collection } = setup();

            render(Header, { props: { collection } });

            const editButton = screen.getByTestId('header-editing-mode-button');

            expect(editButton).toBeInTheDocument();
            expect(editButton).toHaveTextContent('Edit annotations');
        });

        it('renders Finish Editing button when in editing mode', () => {
            const { collection } = setup({
                isEditingMode: true
            });

            render(Header, { props: { collection } });

            const doneButton = screen.getByTestId('header-editing-mode-button');
            expect(doneButton).toBeInTheDocument();
            expect(doneButton).toHaveTextContent('Finish Editing');
        });

        it('calls setIsEditingMode with true when isEditingMode is false', () => {
            const { setIsEditingModeSpy, collection } = setup();

            render(Header, { props: { collection } });
            const editButton = screen.getByTestId('header-editing-mode-button');

            fireEvent.click(editButton);

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(true);
        });

        it('calls setIsEditingMode with false when isEditingMode is true', () => {
            const { setIsEditingModeSpy, collection } = setup({
                isEditingMode: true
            });

            render(Header, { props: { collection } });
            const doneButton = screen.getByTestId('header-editing-mode-button');

            fireEvent.click(doneButton);

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(false);
        });
    });

    describe('Undo button', () => {
        it('should not render undo button when not in editing mode', () => {
            const { collection } = setup({ isEditingMode: false });

            render(Header, { props: { collection } });

            const undoButton = screen.queryByTestId('header-reverse-action-button');
            expect(undoButton).not.toBeInTheDocument();
        });

        it('should render disabled undo button when in editing mode with no reversible actions', () => {
            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: []
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');
            expect(undoButton).toBeInTheDocument();
            expect(undoButton).toBeDisabled();
            expect(undoButton).toHaveAttribute('title', 'No action to undo');
        });

        it('should render enabled undo button when in editing mode with reversible actions', () => {
            const mockAction = {
                id: 'test-action',
                description: 'Test reversible action',
                execute: vi.fn(),
                timestamp: new Date()
            };

            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [mockAction]
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');
            expect(undoButton).toBeInTheDocument();
            expect(undoButton).not.toBeDisabled();
            expect(undoButton).toHaveAttribute('title', 'Test reversible action');
        });

        it('should call executeReversibleAction when undo button is clicked', async () => {
            const mockAction = {
                id: 'test-action',
                description: 'Test reversible action',
                execute: vi.fn(),
                timestamp: new Date()
            };

            const executeReversibleActionMock = vi.fn().mockResolvedValue(undefined);

            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [mockAction],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');
            await fireEvent.click(undoButton);

            expect(executeReversibleActionMock).toHaveBeenCalledWith('test-action');
        });

        it('should show most recent action description in tooltip', () => {
            const mockAction1 = {
                id: 'action-1',
                description: 'First action',
                execute: vi.fn(),
                timestamp: new Date('2023-01-01')
            };

            const mockAction2 = {
                id: 'action-2',
                description: 'Most recent action',
                execute: vi.fn(),
                timestamp: new Date('2023-01-02')
            };

            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [mockAction2, mockAction1] // Most recent first
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');
            expect(undoButton).toHaveAttribute('title', 'Most recent action');
        });

        it('should handle async executeReversibleAction calls', async () => {
            const mockAction = {
                id: 'async-action',
                description: 'Async action',
                execute: vi.fn(),
                timestamp: new Date()
            };

            const executeReversibleActionMock = vi.fn().mockImplementation(async () => {
                await new Promise((resolve) => setTimeout(resolve, 10));
            });

            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [mockAction],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');

            await fireEvent.click(undoButton);

            expect(executeReversibleActionMock).toHaveBeenCalledWith('async-action');
            await vi.waitFor(() => expect(undoButton).toHaveAttribute('aria-busy', 'false'));
        });

        it('shows a spinning loader and blocks a second undo while the undo runs', async () => {
            let finishUndo!: () => void;
            const executeReversibleActionMock = vi
                .fn()
                .mockReturnValue(new Promise<void>((resolve) => (finishUndo = resolve)));
            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [
                    {
                        id: 'slow-action',
                        description: 'Slow action',
                        execute: vi.fn(),
                        timestamp: new Date()
                    }
                ],
                executeReversibleAction: executeReversibleActionMock
            });
            render(Header, { props: { collection } });
            const undoButton = screen.getByTestId('header-reverse-action-button');

            await fireEvent.click(undoButton);
            await fireEvent.click(undoButton);

            expect(undoButton).toBeDisabled();
            expect(undoButton).toHaveAttribute('aria-busy', 'true');
            expect(undoButton.querySelector('.animate-spin')).not.toBeNull();
            expect(executeReversibleActionMock).toHaveBeenCalledOnce();

            finishUndo();
            await vi.waitFor(() => expect(undoButton).not.toBeDisabled());
            expect(undoButton.querySelector('.animate-spin')).toBeNull();
        });

        it('reports a failed undo and enables the button again', async () => {
            const executeReversibleActionMock = vi.fn().mockRejectedValue(new Error('failed'));
            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [
                    { id: 'action', description: 'Action', execute: vi.fn(), timestamp: new Date() }
                ],
                executeReversibleAction: executeReversibleActionMock
            });
            render(Header, { props: { collection } });
            const undoButton = screen.getByTestId('header-reverse-action-button');

            await fireEvent.click(undoButton);

            await vi.waitFor(() => expect(undoButton).not.toBeDisabled());
            expect(toast.error).toHaveBeenCalledWith('Failed to undo. Please try again.');
        });

        it('should not call executeReversibleAction when no actions are available', async () => {
            const executeReversibleActionMock = vi.fn();

            const { collection } = setup({
                isEditingMode: true,
                reversibleActions: [],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header, { props: { collection } });

            const undoButton = screen.getByTestId('header-reverse-action-button');
            await fireEvent.click(undoButton);

            expect(executeReversibleActionMock).not.toHaveBeenCalled();
        });
    });

    describe('Role-based gating of Edit Annotations button', () => {
        it('should show edit button for labeler role', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: { username: 'labeler', email: 'labeler@test.com', role: 'labeler' }
            });

            render(Header, { props: { collection } });

            expect(screen.getByTestId('header-editing-mode-button')).toBeInTheDocument();
        });

        it('should show edit button for editor role', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: { username: 'editor', email: 'editor@test.com', role: 'editor' }
            });

            render(Header, { props: { collection } });

            expect(screen.getByTestId('header-editing-mode-button')).toBeInTheDocument();
        });

        it('should show edit button for admin role', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: { username: 'admin', email: 'admin@test.com', role: 'admin' }
            });

            render(Header, { props: { collection } });

            expect(screen.getByTestId('header-editing-mode-button')).toBeInTheDocument();
        });

        it('should hide edit button for viewer role', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: { username: 'viewer', email: 'viewer@test.com', role: 'viewer' }
            });

            render(Header, { props: { collection } });

            expect(screen.queryByTestId('header-editing-mode-button')).not.toBeInTheDocument();
        });

        it('should show edit button when no user (OSS standalone)', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: null
            });

            render(Header, { props: { collection } });

            expect(screen.getByTestId('header-editing-mode-button')).toBeInTheDocument();
        });
    });

    describe('Role-based gating of keyboard shortcuts', () => {
        it('should not toggle edit mode via keyboard for viewer role', async () => {
            const { setIsEditingModeSpy, collection } = setup({
                isEditingMode: false,
                user: { username: 'viewer', email: 'viewer@test.com', role: 'viewer' }
            });

            render(Header, { props: { collection } });

            await fireEvent.keyDown(window, { key: 'e' });

            expect(setIsEditingModeSpy).not.toHaveBeenCalled();
        });

        it('should toggle edit mode via keyboard for labeler role', async () => {
            const { setIsEditingModeSpy, collection } = setup({
                isEditingMode: false,
                user: { username: 'labeler', email: 'labeler@test.com', role: 'labeler' }
            });

            render(Header, { props: { collection } });

            await fireEvent.keyDown(window, { key: 'e' });

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(true);
        });

        it('should toggle edit mode via keyboard when no user (OSS standalone)', async () => {
            const { setIsEditingModeSpy, collection } = setup({
                isEditingMode: false,
                user: null
            });

            render(Header, { props: { collection } });

            await fireEvent.keyDown(window, { key: 'e' });

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(true);
        });
    });

    describe('User Avatar', () => {
        it('should render user avatar for enterprise version (user logged in)', () => {
            const mockUser = {
                username: 'testuser',
                email: 'test@test.com',
                role: 'admin'
            };

            const { collection } = setup({
                isEditingMode: false,
                user: mockUser
            });

            render(Header, { props: { collection } });

            const userAvatar = screen.getByTestId('header-user-avatar');
            expect(userAvatar).toBeInTheDocument();
        });

        it('should not render user avatar for OSS version (no user logged in)', () => {
            const { collection } = setup({
                isEditingMode: false,
                user: null
            });

            render(Header, { props: { collection } });

            const userAvatar = screen.queryByTestId('header-user-avatar');
            expect(userAvatar).not.toBeInTheDocument();
        });
    });
});
