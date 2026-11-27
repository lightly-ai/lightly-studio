import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import Camera from '@lucide/svelte/icons/camera';
import Grid2x2 from '@lucide/svelte/icons/grid-2x2';
import WorkspaceHeader from './WorkspaceHeader.svelte';

const toggles = [
    { id: 'orthographic', label: 'Orthographic views', icon: Grid2x2, isActive: false },
    { id: 'camera', label: 'Camera strip', icon: Camera, isActive: true }
];

describe('WorkspaceHeader layout toggles', () => {
    it('shows one pressed-state button per panel', () => {
        render(WorkspaceHeader, {
            sequenceId: 'seq',
            isFullscreen: false,
            onToggleFullscreen: vi.fn(),
            layoutToggles: toggles,
            onToggleLayout: vi.fn()
        });

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
        render(WorkspaceHeader, {
            sequenceId: 'seq',
            isFullscreen: false,
            onToggleFullscreen: vi.fn(),
            layoutToggles: toggles,
            onToggleLayout
        });

        await userEvent.click(screen.getByRole('button', { name: 'Camera strip' }));

        expect(onToggleLayout).toHaveBeenCalledWith('camera');
    });

    it('renders no toggle group without toggles', () => {
        render(WorkspaceHeader, {
            sequenceId: 'seq',
            isFullscreen: false,
            onToggleFullscreen: vi.fn()
        });

        expect(screen.queryByRole('group', { name: 'Workspace layout' })).toBeNull();
    });
});
