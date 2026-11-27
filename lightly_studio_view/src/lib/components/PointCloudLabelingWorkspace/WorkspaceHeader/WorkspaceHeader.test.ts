import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import Camera from '@lucide/svelte/icons/camera';
import Grid2x2 from '@lucide/svelte/icons/grid-2x2';
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

const toggles = [
    { id: 'orthographic', label: 'Orthographic views', icon: Grid2x2, isActive: false },
    { id: 'camera', label: 'Camera strip', icon: Camera, isActive: true }
];

const defaultProps = {
    collectionId: 'collection-1',
    sequenceId: 'sequence-1',
    sourcePath: [{ label: 'Home', href: '/home' }, { label: 'drive.mcap' }],
    isFullscreen: false,
    onToggleFullscreen: vi.fn(),
    layoutToggles: toggles,
    onToggleLayout: vi.fn()
};

const visibleButtonNames = () =>
    screen
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label') ?? button.textContent?.trim())
        // Tooltip triggers wrap the real buttons and have no name of their own.
        .filter(Boolean);

describe('WorkspaceHeader', () => {
    it('shows the breadcrumb, edit actions, layout toggles and fullscreen in one row', () => {
        render(WorkspaceHeader, { props: defaultProps });

        expect(screen.getByTestId('workspace-breadcrumb')).toHaveTextContent('drive.mcap');
        expect(screen.getByTestId('breadcrumb-edit-button')).toBeVisible();
        expect(visibleButtonNames()).toEqual([
            'Edit annotations',
            'Plugins',
            'Settings',
            'Orthographic views',
            'Camera strip',
            'Enter fullscreen'
        ]);
    });

    it('shows only the breadcrumb, layout toggles and fullscreen in fullscreen', () => {
        render(WorkspaceHeader, { props: { ...defaultProps, isFullscreen: true } });

        expect(screen.getByTestId('workspace-breadcrumb')).toBeInTheDocument();
        expect(visibleButtonNames()).toEqual([
            'Orthographic views',
            'Camera strip',
            'Exit fullscreen'
        ]);
    });
});

describe('WorkspaceHeader layout toggles', () => {
    it('shows one pressed-state button per panel', () => {
        render(WorkspaceHeader, { props: defaultProps });

        expect(screen.getByRole('button', { name: 'Orthographic views' })).toHaveAttribute(
            'aria-pressed',
            'false'
        );
        expect(screen.getByRole('button', { name: 'Camera strip' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
    });

    it('reports the id of the clicked toggle', async () => {
        const onToggleLayout = vi.fn();
        render(WorkspaceHeader, { props: { ...defaultProps, onToggleLayout } });

        await userEvent.click(screen.getByRole('button', { name: 'Camera strip' }));

        expect(onToggleLayout).toHaveBeenCalledWith('camera');
    });

    it('renders no toggle group without toggles', () => {
        render(WorkspaceHeader, { props: { ...defaultProps, layoutToggles: [] } });

        expect(screen.queryByRole('group', { name: 'Workspace layout' })).toBeNull();
    });
});
