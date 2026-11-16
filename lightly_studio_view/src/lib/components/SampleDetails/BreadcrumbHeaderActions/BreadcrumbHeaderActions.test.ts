import { fireEvent, render, screen } from '@testing-library/svelte';
import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BreadcrumbHeaderActions from './BreadcrumbHeaderActions.svelte';
import type { useWorkflowFileContext } from '$lib/contexts/WorkflowFile.svelte';

const mocks = vi.hoisted(() => ({
    isEditingMode: undefined as unknown as import('svelte/store').Writable<boolean>,
    workflow: undefined as
        | Partial<NonNullable<ReturnType<typeof useWorkflowFileContext>>>
        | undefined
}));

vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return {
        useGlobalStorage: () => ({
            isEditingMode: mocks.isEditingMode,
            setIsEditingMode: (value: boolean) => mocks.isEditingMode.set(value),
            reversibleActions: writable([]),
            executeReversibleAction: vi.fn()
        }),
        useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
        useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) }),
        usePostHog: () => ({ trackEvent: vi.fn() })
    };
});
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'labeler' } })
}));
vi.mock('$lib/contexts/WorkflowFile.svelte', () => ({
    useWorkflowFileContext: () => mocks.workflow
}));

describe('BreadcrumbHeaderActions', () => {
    beforeEach(() => {
        mocks.isEditingMode = writable(false);
        mocks.workflow = undefined;
    });

    it('lets the user start editing outside a batch', async () => {
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await fireEvent.click(screen.getByTestId('breadcrumb-edit-button'));

        expect(get(mocks.isEditingMode)).toBe(true);
    });

    it('disables editing when it is not the user’s turn on a batch file', async () => {
        mocks.workflow = { active: true, canEdit: false, locked: true };
        mocks.isEditingMode.set(true);

        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        const edit = screen.getByTestId('breadcrumb-edit-button');
        expect(edit).toBeDisabled();
        expect(edit).toHaveAccessibleName('Read-only: you can’t edit this file now');
        expect(get(mocks.isEditingMode)).toBe(false);
        await fireEvent.keyDown(window, { key: 'e' });
        expect(get(mocks.isEditingMode)).toBe(false);
    });

    it('keeps edit mode while the next batch file is still loading', () => {
        mocks.workflow = { active: true, canEdit: false, locked: false };
        mocks.isEditingMode.set(true);

        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(get(mocks.isEditingMode)).toBe(true);
    });
});
