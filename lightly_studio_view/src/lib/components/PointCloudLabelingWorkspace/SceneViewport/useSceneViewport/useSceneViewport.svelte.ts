import { onDestroy, untrack } from 'svelte';
import { fromStore } from 'svelte/store';
import { useActiveViewportContext } from '../activeViewportContext';
import type { resolveSceneViewportProps } from '../resolveSceneViewportProps';
import type { Bounds3 } from '../../domain';
const IGNORED_KEY_TARGETS =
    'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="slider"]';

/** Manages viewport activation, keyboard navigation, cursor state, and retained ground bounds. */
export function useSceneViewport(getProps: () => ReturnType<typeof resolveSceneViewportProps>) {
    const navigationId = Symbol('scene-viewport');
    const activeViewport = useActiveViewportContext();
    const active = fromStore(activeViewport);
    const isActive = $derived(active.current === navigationId);
    $effect(() => {
        if (getProps().isScaleSource && active.current === null) activeViewport.set(navigationId);
    });
    onDestroy(() => {
        if (active.current === navigationId) activeViewport.set(null);
    });

    $effect(() => {
        const handleKeydown = (event: KeyboardEvent) => {
            if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
            if (!isActive) return;
            const handler =
                event.key === 'ArrowLeft'
                    ? getProps().onPreviousTick
                    : event.key === 'ArrowRight'
                      ? getProps().onNextTick
                      : undefined;
            if (!handler) return;
            const target = event.target;
            if (target instanceof HTMLElement && target.closest(IGNORED_KEY_TARGETS)) return;
            event.preventDefault();
            handler();
        };
        window.addEventListener('keydown', handleKeydown);
        return () => window.removeEventListener('keydown', handleKeydown);
    });

    // The ground plane keeps the bounds it was placed with, so it stays put while ticks change.
    // It is placed again only when `getProps().fitKey` changes, e.g. for another coordinate frame.
    let groundPlaneBounds = $state<Bounds3>(untrack(() => getProps().pointCloudBounds));
    let groundPlaneKey = untrack(() => getProps().fitKey);
    $effect(() => {
        const key = getProps().fitKey;
        const bounds = getProps().pointCloudBounds;
        untrack(() => {
            if (key === groundPlaneKey && !isEmptyBounds(groundPlaneBounds)) return;
            groundPlaneKey = key;
            groundPlaneBounds = bounds;
        });
    });

    let cursorX = $state(0);
    let cursorY = $state(0);
    let viewport = $state<HTMLDivElement | undefined>();

    function isEmptyBounds(bounds: Bounds3): boolean {
        return bounds.min.every((value, axis) => value === bounds.max[axis]);
    }

    function handleMouseMove(event: MouseEvent) {
        const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
        cursorX = event.clientX - rect.left;
        cursorY = event.clientY - rect.top;
    }

    return {
        navigationId,
        get isActive() {
            return isActive;
        },
        get groundPlaneBounds() {
            return groundPlaneBounds;
        },
        get cursorX() {
            return cursorX;
        },
        get cursorY() {
            return cursorY;
        },
        get viewport() {
            return viewport;
        },
        set viewport(value) {
            viewport = value;
        },
        activate: () => activeViewport.set(navigationId),
        handleMouseMove
    };
}
