import { fromStore } from 'svelte/store';
import type { PaneAPI } from 'paneforge';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Keeps a collapsible pane and its session preference synchronized. */
export function useCollapsiblePane(storageKey: string) {
    const collapsedStore = useSessionStorage<boolean>(storageKey, false);
    const collapsed = fromStore(collapsedStore);
    let pane = $state<PaneAPI>();
    // Paneforge reports the first layout of a pane as a change. That report must restore the
    // stored preference, not overwrite it.
    let hasLayout = false;

    const restoreStoredState = () => {
        if (collapsed.current) pane?.collapse();
        else pane?.expand();
    };

    /** Records a collapse or expand that the pane reports. */
    const setCollapsed = (isCollapsed: boolean) => {
        if (hasLayout) {
            collapsedStore.set(isCollapsed);
            return;
        }
        hasLayout = true;
        if (isCollapsed !== collapsed.current) restoreStoredState();
    };

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
            hasLayout = false;
        },
        get collapsed() {
            return collapsed.current;
        },
        setCollapsed,
        toggle
    };
}
