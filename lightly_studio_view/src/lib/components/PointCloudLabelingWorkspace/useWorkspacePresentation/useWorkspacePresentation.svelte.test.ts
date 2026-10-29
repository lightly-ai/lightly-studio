import { flushSync } from 'svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { useWorkspacePresentation } from './useWorkspacePresentation.svelte';

// No API settings hook is supplied: scene preferences must be entirely local.
vi.mock('$lib/hooks', async () => {
    const { writable } = await import('svelte/store');
    return { useGlobalStorage: () => ({ isEditingMode: writable(true) }) };
});

const key = 'lightlyStudio_pointCloudShowOrthographicViews';
const cleanups: (() => void)[] = [];
afterEach(() => {
    cleanups.splice(0).forEach((dispose) => dispose());
    sessionStorage.removeItem(key);
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

it('stores orthographic visibility locally and restores it in a new workspace', () => {
    const presentation = setup();
    expect(presentation.showOrthographicViews).toBe(false);
    presentation.toggleOrthographicProjections(true);
    expect(presentation.showOrthographicViews).toBe(true);
    expect(sessionStorage.getItem(key)).toBe('true');
    expect(setup().showOrthographicViews).toBe(true);
});
