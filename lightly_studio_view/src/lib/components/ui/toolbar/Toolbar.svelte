<script lang="ts" module>
    import type { Component } from 'svelte';

    export type ToolbarTrigger = 'click' | 'shortcut';

    export interface ToolbarItem {
        id: string;
        label: string;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        icon: Component<any>;
        shortcut?: string;
        /** Verb describing the shortcut action, e.g. "select", "pan", "draw". */
        action?: string;
        /** Extra hint shown below the shortcut line, e.g. "Hold Space to pan temporarily". */
        hint?: string;
        visible?: boolean;
        disabledReason?: string;
    }
</script>

<script lang="ts">
    import { ToolbarTooltip } from '$lib/components/ToolbarTooltip';
    import { isTextInputTarget } from '$lib/utils';
    import { onMount, onDestroy } from 'svelte';

    interface Props {
        items: ToolbarItem[];
        activeTool: string;
        onToolChange: (tool: string, trigger: ToolbarTrigger) => void;
        shouldHandleShortcut?: (event: KeyboardEvent) => boolean;
    }

    let { items, activeTool, onToolChange, shouldHandleShortcut }: Props = $props();

    const visibleItems = $derived(items.filter((item) => item.visible !== false));

    function onKeyDown(e: KeyboardEvent) {
        if (isTextInputTarget(e.target)) return;
        if (shouldHandleShortcut && !shouldHandleShortcut(e)) return;

        const key = e.key.toLowerCase();

        for (const item of visibleItems) {
            if (!item.shortcut || item.disabledReason) continue;
            if (key === item.shortcut.toLowerCase()) {
                e.preventDefault();
                onToolChange(item.id, 'shortcut');
                return;
            }
        }
    }

    onMount(() => {
        window.addEventListener('keydown', onKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener('keydown', onKeyDown);
    });
</script>

<div class="pointer-events-none absolute left-0 top-0 z-20 p-1">
    <nav
        class="pointer-events-auto flex select-none flex-col items-stretch gap-1 rounded-lg bg-muted p-1 shadow-md"
        aria-label="Tools"
    >
        {#each visibleItems as item (item.id)}
            {@const isActive = item.id === activeTool}
            {@const isDisabled = !!item.disabledReason}
            <ToolbarTooltip
                label={item.disabledReason ?? item.label}
                shortcut={isDisabled ? undefined : item.shortcut?.toUpperCase()}
                action={item.action}
                hint={isDisabled ? undefined : item.hint}
            >
                <button
                    type="button"
                    disabled={isDisabled}
                    onclick={isDisabled ? undefined : () => onToolChange(item.id, 'click')}
                    aria-label={item.label}
                    class="flex items-center justify-center rounded-md p-2 transition-colors focus:outline-none
                        {isActive ? 'bg-black/40' : 'hover:bg-black/20'}
                        {isDisabled ? 'pointer-events-none opacity-50' : ''}"
                >
                    <item.icon
                        class="size-4 transition-colors {isActive
                            ? 'text-primary'
                            : ''} hover:text-primary"
                    />
                </button>
            </ToolbarTooltip>
        {/each}
    </nav>
</div>
