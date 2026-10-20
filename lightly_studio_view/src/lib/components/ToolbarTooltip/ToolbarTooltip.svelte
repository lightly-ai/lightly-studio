<script lang="ts">
    import type { Snippet } from 'svelte';
    import { portal, useToolbarTooltip } from './useToolbarTooltip.svelte';

    interface Props {
        label: string;
        shortcut?: string;
        action?: string;
        verb?: string;
        hint?: string;
        position?: 'right' | 'top';
        children: Snippet;
    }

    let {
        label,
        shortcut,
        action,
        verb = 'Press',
        hint,
        position = 'right',
        children
    }: Props = $props();
    const tooltipId = $props.id();
    let triggerElement = $state<HTMLElement>();
    const tooltip = useToolbarTooltip({
        getTrigger: () => triggerElement,
        getPosition: () => position,
        tooltipId
    });
</script>

<div
    class="relative"
    role="presentation"
    bind:this={triggerElement}
    onpointerenter={tooltip.show}
    onpointerleave={tooltip.hide}
    onpointerdown={tooltip.hide}
    onfocusin={tooltip.showOnFocus}
    onfocusout={tooltip.hide}
>
    {@render children()}

    {#if tooltip.visible}
        <div
            use:portal
            id={tooltipId}
            role="tooltip"
            class="pointer-events-none fixed z-50"
            style={tooltip.style}
        >
            <div
                class="flex flex-col gap-0.5 whitespace-nowrap rounded-lg border border-white/10 bg-black px-3 py-2 text-xs text-white shadow-lg"
            >
                <span class="font-medium">{label}</span>
                {#if shortcut && action}
                    <span class="text-white/70"
                        >{verb}
                        <kbd class="rounded border border-white/10 bg-white/10 px-1">{shortcut}</kbd
                        >
                        to {action}</span
                    >
                {/if}
                {#if hint}
                    <span class="text-white/50">{hint}</span>
                {/if}
            </div>
        </div>
    {/if}
</div>
