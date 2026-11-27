import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import '@testing-library/jest-dom';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import BreadcrumbHeaderActions from './BreadcrumbHeaderActions.svelte';

const mocks = vi.hoisted(() => ({
    setIsEditingMode: vi.fn(),
    executeReversibleAction: vi.fn(),
    openOperatorsDialog: vi.fn(),
    openSettingsDialog: vi.fn(),
    trackEvent: vi.fn(),
    userRole: 'labeler' as string | undefined
}));

const isEditingMode = writable(false);
const reversibleActions = writable<ReversibleAction[]>([]);

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode,
        setIsEditingMode: mocks.setIsEditingMode,
        reversibleActions,
        executeReversibleAction: mocks.executeReversibleAction
    })
}));
vi.mock('$lib/hooks/useOperatorsDialog/useOperatorsDialog', () => ({
    useOperatorsDialog: () => ({ openOperatorsDialog: mocks.openOperatorsDialog })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: mocks.openSettingsDialog })
}));
vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) })
}));
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: mocks.trackEvent })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: mocks.userRole ? { role: mocks.userRole } : undefined })
}));

describe('BreadcrumbHeaderActions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.userRole = 'labeler';
        isEditingMode.set(false);
        reversibleActions.set([]);
    });

    it('turns edit mode on and tracks the event when Edit is clicked', async () => {
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-edit-button'));

        expect(mocks.setIsEditingMode).toHaveBeenCalledWith(true);
        expect(mocks.trackEvent).toHaveBeenCalledWith('edit_mode_started', {
            collection_id: 'collection-1',
            triggered_by: 'click'
        });
    });

    it('turns edit mode off when Finish Editing is clicked', async () => {
        isEditingMode.set(true);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-finish-editing-button'));

        expect(mocks.setIsEditingMode).toHaveBeenCalledWith(false);
        expect(mocks.trackEvent).not.toHaveBeenCalled();
    });

    it('runs the latest reversible action when Undo is clicked', async () => {
        isEditingMode.set(true);
        reversibleActions.set([
            {
                id: 'action-2',
                description: 'Delete annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            },
            {
                id: 'action-1',
                description: 'Add annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-undo-button'));

        expect(mocks.executeReversibleAction).toHaveBeenCalledWith('action-2');
        expect(mocks.trackEvent).toHaveBeenCalledWith('edit_undo', {
            collection_id: 'collection-1',
            triggered_by: 'click'
        });
    });

    it('disables Undo when there is no reversible action', () => {
        isEditingMode.set(true);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(screen.getByTestId('breadcrumb-undo-button')).toBeDisabled();
    });

    it('disables Undo while an undo runs', async () => {
        isEditingMode.set(true);
        reversibleActions.set([
            {
                id: 'action-1',
                description: 'Delete annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        let finishUndo = () => {};
        mocks.executeReversibleAction.mockReturnValueOnce(
            new Promise<void>((resolve) => (finishUndo = resolve))
        );
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });
        const undoButton = screen.getByTestId('breadcrumb-undo-button');

        await fireEvent.click(undoButton);
        expect(undoButton).toBeDisabled();

        finishUndo();
        await vi.waitFor(() => expect(undoButton).not.toBeDisabled());
    });

    it('toggles edit mode when the edit shortcut is pressed', async () => {
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.keyDown(window, { key: 'e' });

        expect(mocks.setIsEditingMode).toHaveBeenCalledWith(true);
        expect(mocks.trackEvent).toHaveBeenCalledWith('edit_mode_started', {
            collection_id: 'collection-1',
            triggered_by: 'keyboard_shortcut'
        });
    });

    it('runs undo when Ctrl+Z is pressed', async () => {
        reversibleActions.set([
            {
                id: 'action-1',
                description: 'Add annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.keyDown(window, { key: 'z', ctrlKey: true });

        expect(mocks.executeReversibleAction).toHaveBeenCalledWith('action-1');
    });

    it('runs undo when Cmd+Z is pressed', async () => {
        reversibleActions.set([
            {
                id: 'action-1',
                description: 'Add annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.keyDown(window, { key: 'Z', metaKey: true });

        expect(mocks.executeReversibleAction).toHaveBeenCalledWith('action-1');
    });

    it('ignores shortcuts typed in an input element', async () => {
        reversibleActions.set([
            {
                id: 'action-1',
                description: 'Add annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });
        const input = document.createElement('input');
        document.body.appendChild(input);

        await fireEvent.keyDown(input, { key: 'e' });
        await fireEvent.keyDown(input, { key: 'z', ctrlKey: true });

        expect(mocks.setIsEditingMode).not.toHaveBeenCalled();
        expect(mocks.executeReversibleAction).not.toHaveBeenCalled();
        input.remove();
    });

    it('hides Edit and Undo and ignores shortcuts for a user below labeler', async () => {
        mocks.userRole = 'viewer';
        reversibleActions.set([
            {
                id: 'action-1',
                description: 'Add annotation',
                execute: vi.fn(),
                timestamp: new Date(),
                groupId: 'group-1'
            }
        ]);
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.keyDown(window, { key: 'e' });
        await fireEvent.keyDown(window, { key: 'z', ctrlKey: true });

        expect(screen.queryByTestId('breadcrumb-edit-button')).not.toBeInTheDocument();
        expect(screen.queryByTestId('breadcrumb-undo-button')).not.toBeInTheDocument();
        expect(mocks.setIsEditingMode).not.toHaveBeenCalled();
        expect(mocks.executeReversibleAction).not.toHaveBeenCalled();
    });

    it('opens the Plugins dialog when Plugins is clicked', async () => {
        mocks.userRole = 'admin';
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-plugins-button'));

        expect(mocks.openOperatorsDialog).toHaveBeenCalled();
    });

    it('opens the Settings dialog when Settings is clicked', async () => {
        mocks.userRole = 'admin';
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-settings-button'));

        expect(mocks.openSettingsDialog).toHaveBeenCalled();
    });

    it('hides Plugins and Settings from a labeler', () => {
        mocks.userRole = 'labeler';
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(screen.getByTestId('breadcrumb-edit-button')).toBeInTheDocument();
        expect(screen.queryByTestId('breadcrumb-plugins-button')).not.toBeInTheDocument();
        expect(screen.queryByTestId('breadcrumb-settings-button')).not.toBeInTheDocument();
    });

    it('shows Plugins and Settings to an editor', () => {
        mocks.userRole = 'editor';
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(screen.getByTestId('breadcrumb-plugins-button')).toBeInTheDocument();
        expect(screen.getByTestId('breadcrumb-settings-button')).toBeInTheDocument();
    });
});
