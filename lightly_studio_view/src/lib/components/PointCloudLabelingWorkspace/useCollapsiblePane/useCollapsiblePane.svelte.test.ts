import { flushSync } from 'svelte';
import { afterEach, expect, it, vi } from 'vitest';
import type { PaneAPI } from 'paneforge';
import { useCollapsiblePane } from './useCollapsiblePane.svelte';

const storageKey = 'lightlyStudio_pointCloudTestPaneCollapsed';
let dispose = () => {};
afterEach(() => {
    dispose();
    sessionStorage.removeItem(storageKey);
});

it('restores a collapsed preference after the pane binds and persists subsequent toggles', () => {
    sessionStorage.setItem(storageKey, 'true');
    let hook!: ReturnType<typeof useCollapsiblePane>;
    dispose = $effect.root(() => {
        hook = useCollapsiblePane(storageKey);
    });
    flushSync();
    expect(() => hook.toggle()).not.toThrow();
    let collapsed = false;
    const pane = {
        isCollapsed: () => collapsed,
        isExpanded: () => !collapsed,
        collapse: vi.fn(() => {
            collapsed = true;
            hook.setCollapsed(true);
        }),
        expand: vi.fn(() => {
            collapsed = false;
            hook.setCollapsed(false);
        })
    };
    hook.pane = pane as unknown as PaneAPI;
    flushSync();
    expect(pane.collapse).toHaveBeenCalledOnce();
    expect(hook.collapsed).toBe(true);

    hook.toggle();
    flushSync();
    expect(pane.expand).toHaveBeenCalledOnce();
    expect(sessionStorage.getItem(storageKey)).toBe('false');
    hook.toggle();
    flushSync();
    expect(sessionStorage.getItem(storageKey)).toBe('true');
    dispose();

    dispose = $effect.root(() => {
        hook = useCollapsiblePane(storageKey);
    });
    expect(hook.collapsed).toBe(true);
});
