<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';
    import type { Snippet } from 'svelte';
    import { fly } from 'svelte/transition';

    let {
        content,
        position = 'top',
        class: className,
        children
    }: {
        content: string;
        position?: 'top' | 'bottom' | 'left' | 'right';
        class?: string;
        children: Snippet;
    } = $props();

    let showTooltip = $state(false);
    let triggerElement: HTMLElement;

    function getPositionStyles() {
        if (!triggerElement) return {};

        switch (position) {
            case 'top':
                return {
                    bottom: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    marginBottom: '5px'
                };
            case 'bottom':
                return {
                    top: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    marginTop: '5px'
                };
            case 'left':
                return {
                    right: '100%',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    marginRight: '5px'
                };
            case 'right':
                return {
                    left: '100%',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    marginLeft: '5px'
                };
            default:
                return {
                    bottom: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    marginBottom: '5px'
                };
        }
    }

    function showTooltipHandler() {
        showTooltip = true;
    }

    function hideTooltipHandler() {
        showTooltip = false;
    }
</script>

<div
    class="relative inline-block"
    on:mouseenter={showTooltipHandler}
    on:mouseleave={hideTooltipHandler}
    on:focusin={showTooltipHandler}
    on:focusout={hideTooltipHandler}
    on:keydown={(e) => e.key === 'Escape' && hideTooltipHandler()}
    bind:this={triggerElement}
    tabindex="0"
    role="button"
    aria-describedby={showTooltip ? 'tooltip' : undefined}
>
    {@render children()}

    {#if showTooltip && content}
        <div
            class={cn(
                'bg-popover text-popover-foreground absolute z-50 max-w-xs rounded-md px-3 py-1.5 text-xs shadow-md',
                className
            )}
            style={getPositionStyles()}
            transition:fly={{
                y: position === 'top' ? 5 : position === 'bottom' ? -5 : 0,
                x: position === 'left' ? 5 : position === 'right' ? -5 : 0,
                duration: 200
            }}
            role="tooltip"
            id="tooltip"
        >
            {content}
        </div>
    {/if}
</div>
