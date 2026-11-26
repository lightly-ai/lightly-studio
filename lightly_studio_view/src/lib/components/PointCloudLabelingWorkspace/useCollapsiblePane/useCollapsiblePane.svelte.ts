import { fromStore } from 'svelte/store';
import type { PaneAPI } from 'paneforge';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Keeps a collapsible pane and its session preference synchronized. */
export function useCollapsiblePane(storageKey: string) {
    const collapsedStore = useSessionStorage<boolean>(storageKey, false);
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
