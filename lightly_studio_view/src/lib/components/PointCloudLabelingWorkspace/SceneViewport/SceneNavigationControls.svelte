<script lang="ts">
    import { onMount } from 'svelte';
    import {
        ArrowDown,
        ArrowLeft,
        ArrowRight,
        ArrowUp,
        RotateCcw,
        RotateCw
    } from '@lucide/svelte';
    import {
        navigateScene,
        startSceneNavigation,
        stopSceneNavigation,
        type SceneNavigationAction
    } from '$lib/components/PointCloudViewer/sceneNavigation';

    const controls: {
        action: SceneNavigationAction;
        label: string;
        icon: typeof ArrowUp;
        key?: string;
    }[] = [
        { action: 'rotate-left', label: 'Rotate left (Q)', icon: RotateCcw, key: 'Q' },
        { action: 'forward', label: 'Move forward (W)', icon: ArrowUp, key: 'W' },
        { action: 'rotate-right', label: 'Rotate right (E)', icon: RotateCw, key: 'E' },
        { action: 'left', label: 'Move left (A)', icon: ArrowLeft, key: 'A' },
        { action: 'backward', label: 'Move backward (S)', icon: ArrowDown, key: 'S' },
        { action: 'right', label: 'Move right (D)', icon: ArrowRight, key: 'D' }
    ];
    const keyActions: Record<string, SceneNavigationAction> = {
        w: 'forward',
        a: 'left',
        s: 'backward',
        d: 'right',
        q: 'rotate-left',
        e: 'rotate-right'
    };
    let holdDelay: ReturnType<typeof setTimeout> | undefined;
    let holdAction: SceneNavigationAction | undefined;
    let holdRepeated = false;
    const pressedKeys = new Set<string>();

    function startHold(action: SceneNavigationAction) {
        stopHold();
        holdRepeated = false;
        holdDelay = setTimeout(() => {
            holdRepeated = true;
            holdAction = action;
            startSceneNavigation(action);
        }, 180);
    }

    function stopHold() {
        if (holdDelay) clearTimeout(holdDelay);
        if (holdAction) stopSceneNavigation(holdAction);
        holdDelay = undefined;
        holdAction = undefined;
    }

    onMount(() => {
        const handleKeydown = (event: KeyboardEvent) => {
            if (event.altKey || event.ctrlKey || event.metaKey) return;
            const target = event.target;
            if (
                target instanceof HTMLElement &&
                target.closest('input, textarea, select, [contenteditable="true"]')
            ) {
                return;
            }
            const key = event.key.toLowerCase();
            const action = keyActions[key];
            if (!action || pressedKeys.has(key)) return;
            pressedKeys.add(key);
            event.preventDefault();
            startSceneNavigation(action);
        };
        const handleKeyup = (event: KeyboardEvent) => {
            const key = event.key.toLowerCase();
            const action = keyActions[key];
            if (!action || !pressedKeys.has(key)) return;
            pressedKeys.delete(key);
            stopSceneNavigation(action);
        };
        const stopPressedKeys = () => {
            for (const key of pressedKeys) stopSceneNavigation(keyActions[key]);
            pressedKeys.clear();
        };
        window.addEventListener('keydown', handleKeydown);
        window.addEventListener('keyup', handleKeyup);
        window.addEventListener('blur', stopPressedKeys);
        return () => {
            window.removeEventListener('keydown', handleKeydown);
            window.removeEventListener('keyup', handleKeyup);
            window.removeEventListener('blur', stopPressedKeys);
            stopPressedKeys();
            stopHold();
        };
    });
</script>

<div
    class="absolute bottom-3 right-3 z-10 grid grid-cols-3 gap-1 rounded-md border bg-background/80 p-1 shadow"
>
    {#each controls as control (control.action)}
        <button
            type="button"
            class="relative flex size-8 items-center justify-center rounded hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={control.label}
            title={control.label}
            onpointerdown={(event) => {
                if (event.button === 0) startHold(control.action);
            }}
            onpointerup={stopHold}
            onpointerleave={stopHold}
            onpointercancel={stopHold}
            onclick={() => {
                if (holdRepeated) {
                    holdRepeated = false;
                    return;
                }
                navigateScene(control.action);
            }}
        >
            <control.icon size={16} />
            {#if control.key}
                <span class="absolute bottom-0 right-0.5 text-[9px] font-semibold leading-none">
                    {control.key}
                </span>
            {/if}
        </button>
    {/each}
</div>
