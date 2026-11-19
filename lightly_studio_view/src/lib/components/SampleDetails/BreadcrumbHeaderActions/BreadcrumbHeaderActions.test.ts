import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';

let userRole = 'editor';

vi.mock('$lib/hooks', () => ({
    useGlobalStorage: () => ({
        isEditingMode: writable(false),
        setIsEditingMode: vi.fn(),
        reversibleActions: writable([]),
        executeReversibleAction: vi.fn()
    }),
    useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
    useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) }),
    usePostHog: () => ({ trackEvent: vi.fn() })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: userRole } })
}));

import BreadcrumbHeaderActions from './BreadcrumbHeaderActions.svelte';

describe('BreadcrumbHeaderActions', () => {
    it('hides Plugins and Settings from a labeler', () => {
        userRole = 'labeler';

        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(screen.getByTestId('breadcrumb-edit-button')).toBeInTheDocument();
        expect(screen.queryByTestId('breadcrumb-plugins-button')).not.toBeInTheDocument();
        expect(screen.queryByTestId('breadcrumb-settings-button')).not.toBeInTheDocument();
    });

    it('shows Plugins and Settings to an editor', () => {
        userRole = 'editor';

        render(BreadcrumbHeaderActions, { props: { collectionId: 'collection-1' } });

        expect(screen.getByTestId('breadcrumb-plugins-button')).toBeInTheDocument();
        expect(screen.getByTestId('breadcrumb-settings-button')).toBeInTheDocument();
    });
});
