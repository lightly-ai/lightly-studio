import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import Header from './Header.svelte';
import * as appState from '$app/state';
import '@testing-library/jest-dom';
import { Page } from '@sveltejs/kit';
import type { ReversibleAction } from '$lib/hooks/useGlobalStorage';
import type { CollectionView } from '$lib/api/lightly_studio_local';

import { useRootCollectionOptions } from '$lib/hooks/useRootCollection/useRootCollection';

describe('Header', () => {
    const mockCollection: CollectionView = {
        collection_id: 'test-collection',
        name: 'Test Collection',
        sample_type: 'image',
        created_at: new Date('2023-01-01'),
        updated_at: new Date('2023-01-02')
    };

    const setup = (
        props: {
            isEditingMode: boolean;
            reversibleActions?: ReversibleAction[];
            executeReversibleAction?: vi.Mock;
            collection?: CollectionView;
        } = { isEditingMode: false }
    ) => {
        const app = appState;
        const setIsEditingModeSpy = vi.fn();
        const executeReversibleActionSpy = props.executeReversibleAction || vi.fn();
        vi.spyOn(app, 'page', 'get').mockReturnValue({
            data: {
                globalStorage: {
                    isEditingMode: writable(props?.isEditingMode),
                    setIsEditingMode: setIsEditingModeSpy,
                    reversibleActions: writable(props.reversibleActions || []),
                    executeReversibleAction: executeReversibleActionSpy
                }
            },
            params: {
                collection_id: props.collection?.collection_id || 'test-collection'
            },
            route: { id: null, uid: null, pattern: '/collections/[collection_id]/samples' }
        } as unknown as Page<Record<string, string>, string | null>);

        vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => {
            const actual = await importOriginal();
            return {
                ...actual,
                readRootCollection: vi.fn()
            };
        });

        vi.mock('$lib/hooks/useRootCollection/useRootCollection', () => {
            return {
                useRootCollectionOptions: vi.fn()
            };
        });

        (useRootCollectionOptions as unknown as vi.Mock).mockReturnValue({
            rootCollection: readable({
                isSuccess: true,
                data: {
                    sample_type: 'image',
                    collection_id: props.collection?.collection_id || 'test-collection',
                    name: 'Root Collection',
                    children: []
                }
            })
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
            expect(editButton).toHaveTextContent('Edit Annotations');
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

            // Click and wait for async operation
            const clickPromise = fireEvent.click(undoButton);
            await clickPromise;

            expect(executeReversibleActionMock).toHaveBeenCalledWith('async-action');
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
});
