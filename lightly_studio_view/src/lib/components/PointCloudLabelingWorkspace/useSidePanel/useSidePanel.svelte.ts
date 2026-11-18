import { fromStore } from 'svelte/store';
import type { PaneAPI } from 'paneforge';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

/**
 * Keeps the workspace's right side panel in sync with the side-panel preference shared
 * with image details.
 */
export function useSidePanel(getSelectedCuboidId: () => string | null) {
    const { isSampleDetailsSidePanelCollapsed } = useGlobalStorage();
    const collapsed = fromStore(isSampleDetailsSidePanelCollapsed);
    let pane = $state<PaneAPI>();

    $effect(() => {
        if (!pane) return;
        if (collapsed.current && pane.isExpanded()) pane.collapse();
        if (!collapsed.current && pane.isCollapsed()) pane.expand();
    });

    // Selecting or creating a cuboid shows its details. The effect tracks only the
    // selection, so collapsing while a cuboid stays selected keeps the panel collapsed.
    $effect(() => {
        if (getSelectedCuboidId()) isSampleDetailsSidePanelCollapsed.set(false);
    });

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
        /** Records a collapse or expand done on the pane itself, e.g. by dragging. */
        setCollapsed: isSampleDetailsSidePanelCollapsed.set
    };
}
