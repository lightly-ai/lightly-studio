import { fromStore } from 'svelte/store';
import type { PaneAPI } from 'paneforge';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Keeps camera pane visibility and its session preference synchronized. */
export function useCameraPane() {
    const collapsedStore = useSessionStorage<boolean>(
        'lightlyStudio_pointCloudCameraStripCollapsed',
        false
    );
    const collapsed = fromStore(collapsedStore);
    let pane = $state<PaneAPI>();

    $effect(() => {
        if (!pane) return;
        if (collapsed.current && pane.isExpanded()) pane.collapse();
        if (!collapsed.current && pane.isCollapsed()) pane.expand();
    });

    const toggle = () => {
        if (!pane) return;
        if (pane.isCollapsed()) pane.expand();
        else pane.collapse();
    };

    return {
        get pane() {
            return pane;
        },
        set pane(value) {
            pane = value;
        },
        get collapsed() {
            return collapsed.current;
        },
        setCollapsed: collapsedStore.set,
        toggle
    };
}
