import { flushSync } from 'svelte';
import { afterEach, expect, it, vi } from 'vitest';
import type { PaneAPI } from 'paneforge';
import { get } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useSidePanel } from './useSidePanel.svelte';

// The preference shared with the image details side panel.
const { isSampleDetailsSidePanelCollapsed: sharedCollapsed } = useGlobalStorage();
let dispose = () => {};
afterEach(() => {
    dispose();
    sharedCollapsed.set(false);
});

/** A paneforge pane stand-in that reports collapse and expand like the real one. */
function fakePane(hook: ReturnType<typeof useSidePanel>, initiallyCollapsed = false) {
    let collapsed = initiallyCollapsed;
    return {
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
}

function mount(getSelectedCuboidId: () => string | null = () => null) {
    let hook!: ReturnType<typeof useSidePanel>;
    dispose = $effect.root(() => {
        hook = useSidePanel(getSelectedCuboidId);
    });
    flushSync();
    return hook;
}

it('collapses the pane when the shared side-panel preference is collapsed', () => {
    sharedCollapsed.set(true);
    const hook = mount();

    const pane = fakePane(hook);
    hook.pane = pane as unknown as PaneAPI;
    flushSync();

    expect(pane.collapse).toHaveBeenCalledOnce();
    expect(hook.collapsed).toBe(true);
});

it('expands the pane when the side-panel toggle opens it', () => {
    sharedCollapsed.set(true);
    const hook = mount();
    const pane = fakePane(hook, true);
    hook.pane = pane as unknown as PaneAPI;
    flushSync();

    useGlobalStorage().toggleSampleDetailsSidePanelCollapsed();
    flushSync();

    expect(pane.expand).toHaveBeenCalledOnce();
    expect(hook.collapsed).toBe(false);
});

it('opens the collapsed panel when a cuboid is selected or created', () => {
    let selectedCuboidId = $state<string | null>(null);
    sharedCollapsed.set(true);
    const hook = mount(() => selectedCuboidId);
    const pane = fakePane(hook, true);
    hook.pane = pane as unknown as PaneAPI;
    flushSync();
    expect(get(sharedCollapsed)).toBe(true);

    selectedCuboidId = 'cuboid-1';
    flushSync();

    expect(pane.expand).toHaveBeenCalledOnce();
    expect(get(sharedCollapsed)).toBe(false);
});

it('keeps the panel collapsed when the selection is cleared', () => {
    let selectedCuboidId = $state<string | null>('cuboid-1');
    const hook = mount(() => selectedCuboidId);
    hook.pane = fakePane(hook) as unknown as PaneAPI;
    flushSync();
    sharedCollapsed.set(true);
    flushSync();

    selectedCuboidId = null;
    flushSync();

    expect(get(sharedCollapsed)).toBe(true);
});
