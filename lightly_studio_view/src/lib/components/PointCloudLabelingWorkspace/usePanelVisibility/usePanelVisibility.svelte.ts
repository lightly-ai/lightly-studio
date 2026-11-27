import { fromStore } from 'svelte/store';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Remembers in the session whether a panel without its own pane is shown. */
export function usePanelVisibility(storageKey: string, defaultVisible: boolean) {
    const store = useSessionStorage<boolean>(storageKey, defaultVisible);
    const visible = fromStore(store);

    return {
        get visible() {
            return visible.current;
        },
        setVisible: store.set,
        toggle: () => store.set(!visible.current)
    };
}
