import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BreadcrumbHeaderActions from './BreadcrumbHeaderActions.svelte';

const isEditingMode = writable(false);

vi.mock('$lib/hooks', () => ({
    useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
    useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isEditingMode,
        setIsEditingMode: vi.fn(),
        reversibleActions: writable([]),
        executeReversibleAction: vi.fn()
    })
}));
vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: vi.fn() })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'editor' } })
}));

describe('BreadcrumbHeaderActions keyboard focus', () => {
    beforeEach(() => {
        isEditingMode.set(false);
    });

    it('stops on each action button once when tabbing', async () => {
        const user = userEvent.setup();
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await user.tab();
        expect(screen.getByRole('button', { name: 'Edit annotations' })).toHaveFocus();
        await user.tab();
        expect(screen.getByRole('button', { name: 'Plugins' })).toHaveFocus();
        await user.tab();
        expect(screen.getByRole('button', { name: 'Settings' })).toHaveFocus();
    });

    it('reaches the disabled undo action and shows its reason once', async () => {
        isEditingMode.set(true);
        const user = userEvent.setup();
        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        await user.tab();
        expect(document.activeElement).toHaveAccessibleName('Undo');
        expect(screen.getAllByRole('tooltip').map((tooltip) => tooltip.textContent)).toEqual([
            'No action to undo'
        ]);
        await user.tab();
        expect(screen.getByRole('button', { name: 'Finish Editing' })).toHaveFocus();
    });
});
