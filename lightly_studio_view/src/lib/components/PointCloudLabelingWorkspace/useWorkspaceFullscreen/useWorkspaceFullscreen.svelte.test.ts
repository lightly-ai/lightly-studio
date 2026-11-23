import { flushSync } from 'svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { useWorkspaceFullscreen } from './useWorkspaceFullscreen.svelte';

let dispose = () => {};
const originalFullscreen = Object.getOwnPropertyDescriptor(document, 'fullscreenElement');
const originalExit = Object.getOwnPropertyDescriptor(document, 'exitFullscreen');
afterEach(() => {
    dispose();
    for (const [key, descriptor] of [
        ['fullscreenElement', originalFullscreen],
        ['exitFullscreen', originalExit]
    ] as const) {
        if (descriptor) Object.defineProperty(document, key, descriptor);
        else Reflect.deleteProperty(document, key);
    }
    vi.restoreAllMocks();
});

it('targets the bound workspace, tracks browser fullscreen and its portal target, and removes its listener', async () => {
    let current: Element | null = null;
    Object.defineProperty(document, 'fullscreenElement', {
        configurable: true,
        get: () => current
    });
    const exitFullscreen = vi.fn(async () => {
        current = null;
    });
    Object.defineProperty(document, 'exitFullscreen', {
        configurable: true,
        value: exitFullscreen
    });
    const removeListener = vi.spyOn(document, 'removeEventListener');
    let fullscreen!: ReturnType<typeof useWorkspaceFullscreen>;
    dispose = $effect.root(() => {
        fullscreen = useWorkspaceFullscreen();
    });
    flushSync();
    await fullscreen.toggleFullscreen();
    expect(exitFullscreen).not.toHaveBeenCalled();
    expect(fullscreen.portalTarget).toBe('body');
    const container = document.createElement('div');
    container.requestFullscreen = vi.fn(async () => {
        current = container;
    });
    fullscreen.containerEl = container;
    await fullscreen.toggleFullscreen();
    document.dispatchEvent(new Event('fullscreenchange'));
    expect(container.requestFullscreen).toHaveBeenCalledOnce();
    expect(fullscreen.isFullscreen).toBe(true);
    expect(fullscreen.portalTarget).toBe(container);

    current = document.createElement('div');
    document.dispatchEvent(new Event('fullscreenchange'));
    expect(fullscreen.isFullscreen).toBe(false);
    expect(fullscreen.portalTarget).toBe('body');
    await fullscreen.toggleFullscreen();
    expect(exitFullscreen).toHaveBeenCalledOnce();
    dispose();
    expect(removeListener).toHaveBeenCalledWith('fullscreenchange', expect.any(Function));
});
