import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import WorkspaceHeader from './WorkspaceHeader.svelte';

vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return {
        useGlobalStorage: () => ({
            isEditingMode: writable(false),
            setIsEditingMode: vi.fn(),
            reversibleActions: writable([]),
            executeReversibleAction: vi.fn()
        }),
        useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
        useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) }),
        usePostHog: () => ({ trackEvent: vi.fn() })
    };
});
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        isSampleDetailsSidePanelCollapsed: writable(false),
        toggleSampleDetailsSidePanelCollapsed: vi.fn()
    })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
// Plugins and Settings show from the editor role up.
vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: { role: 'editor' } })
}));
vi.mock('$lib/contexts/WorkflowFile.svelte', () => ({
    useWorkflowFileContext: () => undefined
}));

const defaultProps = {
    collectionId: 'collection-1',
    sequenceId: 'sequence-1',
    sourcePath: [{ label: 'Home', href: '/home' }, { label: 'drive.mcap' }],
    isFullscreen: false,
    onToggleFullscreen: vi.fn(),
    onToggleCameraStrip: vi.fn()
};

const visibleButtonNames = () =>
    screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label') ?? button.textContent?.trim())
        // Tooltip triggers wrap the real buttons and have no name of their own.
        .filter(Boolean);

describe('WorkspaceHeader', () => {
    it('shows the breadcrumb, edit actions, camera strip, fullscreen and side-panel toggle in one row', () => {
        render(WorkspaceHeader, { props: defaultProps });

        expect(screen.getByTestId('workspace-breadcrumb')).toHaveTextContent('drive.mcap');
        expect(screen.getByTestId('breadcrumb-edit-button')).toBeVisible();
        expect(visibleButtonNames()).toEqual([
            'Edit annotations',
            'Plugins',
            'Settings',
            'Hide camera strip',
            'Enter fullscreen',
            'Hide side panel'
        ]);
    });

    it('shows only the breadcrumb, camera strip and fullscreen in fullscreen', () => {
        render(WorkspaceHeader, { props: { ...defaultProps, isFullscreen: true } });

        expect(screen.getByTestId('workspace-breadcrumb')).toBeInTheDocument();
        expect(visibleButtonNames()).toEqual(['Hide camera strip', 'Exit fullscreen']);
    });
});
