import { fireEvent, render, screen } from '@testing-library/svelte';
import { expect, it, vi } from 'vitest';
import SceneNavigationControls from './SceneNavigationControls.svelte';
import { listenToSceneNavigation } from '../../PointCloudViewer/sceneNavigation';

it('shows controls for the active projection and releases held input when it loses activity', async () => {
    const navigationId = Symbol('top');
    const onNavigation = vi.fn();
    const unsubscribe = listenToSceneNavigation(onNavigation);
    const { rerender, unmount } = render(SceneNavigationControls, {
        props: { isActive: true, allowRotation: false, navigationId }
    });
    try {
        expect(screen.getByRole('button', { name: 'Move forward (W)' })).toBeTruthy();
        expect(screen.queryByRole('button', { name: 'Rotate left (Q)' })).toBeNull();
        await fireEvent.keyDown(window, { key: 'w' });
        expect(onNavigation).toHaveBeenLastCalledWith({
            action: 'forward',
            phase: 'start',
            navigationId
        });
        await rerender({ isActive: false });
        expect(screen.queryAllByRole('button')).toHaveLength(0);
        expect(onNavigation).toHaveBeenLastCalledWith({
            action: 'forward',
            phase: 'stop',
            navigationId
        });
    } finally {
        unmount();
        unsubscribe();
    }
});
