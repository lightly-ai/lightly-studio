import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import { useEditModeControls } from './useEditModeControls';

const mocks = vi.hoisted(() => ({
    executeReversibleAction: vi.fn()
}));

const reversibleActions = writable<ReversibleAction[]>([]);

vi.mock('svelte-sonner', () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode: writable(true),
        setIsEditingMode: vi.fn(),
        reversibleActions,
        executeReversibleAction: mocks.executeReversibleAction
    })
}));
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: vi.fn() })
}));

const createAction = (description: string): ReversibleAction => ({
    id: 'action-1',
    description,
    execute: vi.fn(),
    timestamp: new Date(),
    groupId: 'group-1'
});

describe('useEditModeControls', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        reversibleActions.set([]);
    });

    it('names the reverted action after an undo', async () => {
        reversibleActions.set([createAction('Delete annotation')]);
        const { undo } = useEditModeControls(() => 'collection-1');

        await undo('click');

        expect(mocks.executeReversibleAction).toHaveBeenCalledWith('action-1');
        expect(toast).toHaveBeenCalledWith('Undone: Delete annotation');
    });

    it('shows an error and no confirmation when the undo fails', async () => {
        reversibleActions.set([createAction('Delete annotation')]);
        mocks.executeReversibleAction.mockRejectedValueOnce(new Error('network'));
        const { undo } = useEditModeControls(() => 'collection-1');

        await undo('keyboard_shortcut');

        expect(toast).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith('Failed to undo. Please try again.');
    });

    it('does nothing when there is no action to undo', async () => {
        const { undo } = useEditModeControls(() => 'collection-1');

        await undo('click');

        expect(mocks.executeReversibleAction).not.toHaveBeenCalled();
        expect(toast).not.toHaveBeenCalled();
    });
});
