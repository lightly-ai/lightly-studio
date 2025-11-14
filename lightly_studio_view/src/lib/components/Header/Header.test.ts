import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import Header from './Header.svelte';
import * as appState from '$app/state';
import '@testing-library/jest-dom';
import { Page } from '@sveltejs/kit';
import type { ReversibleAction } from '$lib/hooks/useGlobalStorage';

import { readRootDataset } from '$lib/api/lightly_studio_local';

describe('Header', () => {
    const setup = (
        props: {
            isEditingMode: boolean;
            reversibleActions?: ReversibleAction[];
            executeReversibleAction?: vi.Mock;
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
                dataset_id: 'test-dataset'
            },
            route: { id: null, uid: null, pattern: '/datasets/[dataset_id]/samples' }
        } as unknown as Page<Record<string, string>, string | null>);

        vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => {
            const actual = await importOriginal();
            return {
                ...actual,
                readRootDataset: vi.fn()
            };
        });

        (readRootDataset as vi.Mock).mockResolvedValue({
            data: { sample_type: 'image', dataset_id: '1' }
        });

        return { setIsEditingModeSpy, executeReversibleActionSpy };
    };

    beforeEach(setup);

    describe('Edit Mode button', () => {
        it('renders Edit Annotations button when not in editing mode', () => {
            render(Header);

            const editButton = screen.getByTestId('header-editing-mode-button');

            expect(editButton).toBeInTheDocument();
            expect(editButton).toHaveTextContent('Edit Annotations');
        });

        it('renders Finish Editing button when in editing mode', () => {
            setup({
                isEditingMode: true
            });

            render(Header);

            const doneButton = screen.getByTestId('header-editing-mode-button');
            expect(doneButton).toBeInTheDocument();
            expect(doneButton).toHaveTextContent('Finish Editing');
        });

        it('calls setIsEditingMode with true when isEditingMode is false', () => {
            const { setIsEditingModeSpy } = setup();

            render(Header);
            const editButton = screen.getByTestId('header-editing-mode-button');

            fireEvent.click(editButton);

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(true);
        });

        it('calls setIsEditingMode with false when isEditingMode is true', () => {
            const { setIsEditingModeSpy } = setup({
                isEditingMode: true
            });

            render(Header);
            const doneButton = screen.getByTestId('header-editing-mode-button');

            fireEvent.click(doneButton);

            expect(setIsEditingModeSpy).toHaveBeenCalledWith(false);
        });
    });

    describe('Undo button', () => {
        it('should not render undo button when not in editing mode', () => {
            setup({ isEditingMode: false });

            render(Header);

            const undoButton = screen.queryByTestId('header-reverse-action-button');
            expect(undoButton).not.toBeInTheDocument();
        });

        it('should render disabled undo button when in editing mode with no reversible actions', () => {
            setup({
                isEditingMode: true,
                reversibleActions: []
            });

            render(Header);

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

            setup({
                isEditingMode: true,
                reversibleActions: [mockAction]
            });

            render(Header);

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

            setup({
                isEditingMode: true,
                reversibleActions: [mockAction],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header);

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

            setup({
                isEditingMode: true,
                reversibleActions: [mockAction2, mockAction1] // Most recent first
            });

            render(Header);

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

            setup({
                isEditingMode: true,
                reversibleActions: [mockAction],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header);

            const undoButton = screen.getByTestId('header-reverse-action-button');

            // Click and wait for async operation
            const clickPromise = fireEvent.click(undoButton);
            await clickPromise;

            expect(executeReversibleActionMock).toHaveBeenCalledWith('async-action');
        });

        it('should not call executeReversibleAction when no actions are available', async () => {
            const executeReversibleActionMock = vi.fn();

            setup({
                isEditingMode: true,
                reversibleActions: [],
                executeReversibleAction: executeReversibleActionMock
            });

            render(Header);

            const undoButton = screen.getByTestId('header-reverse-action-button');
            await fireEvent.click(undoButton);

            expect(executeReversibleActionMock).not.toHaveBeenCalled();
        });
    });
});
