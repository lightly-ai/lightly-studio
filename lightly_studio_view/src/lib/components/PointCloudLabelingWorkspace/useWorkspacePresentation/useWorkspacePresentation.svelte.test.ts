import { flushSync } from 'svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { useWorkspacePresentation } from './useWorkspacePresentation.svelte';

// No API settings hook is supplied: scene preferences must be entirely local.
vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return { useGlobalStorage: () => ({ isEditingMode: writable(true) }) };
});

const enabledKey = 'lightlyStudio_pointCloudOrthographicViewsEnabled';
const collapsedKey = 'lightlyStudio_pointCloudOrthographicViewsCollapsed';
const cleanups: (() => void)[] = [];
afterEach(() => {
    cleanups.splice(0).forEach((dispose) => dispose());
    sessionStorage.removeItem(enabledKey);
    sessionStorage.removeItem(collapsedKey);
});

function setup() {
    let presentation!: ReturnType<typeof useWorkspacePresentation>;
    cleanups.push(
        $effect.root(() => {
            presentation = useWorkspacePresentation();
        })
    );
    flushSync();
    return presentation;
}

it('shows the orthographic views expanded by default', () => {
    const presentation = setup();
    expect(presentation.orthographicViewsEnabled).toBe(true);
    expect(presentation.orthographicViewsCollapsed).toBe(false);
});

it('stores the orthographic views preferences locally and restores them in a new workspace', () => {
    const presentation = setup();
    presentation.setOrthographicViewsEnabled(false);
    presentation.setOrthographicViewsCollapsed(true);
    expect(sessionStorage.getItem(enabledKey)).toBe('false');
    expect(sessionStorage.getItem(collapsedKey)).toBe('true');
    const restored = setup();
    expect(restored.orthographicViewsEnabled).toBe(false);
    expect(restored.orthographicViewsCollapsed).toBe(true);
});
