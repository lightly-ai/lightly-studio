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
        if (!triggerElement) return '';

        let positionStyle = '';
        let transform = '';
        let margin = '';

        switch (position) {
            case 'top':
                positionStyle = 'bottom: 100%; left: 50%;';
                transform = 'translateX(-50%)';
                margin = 'margin-bottom: 5px;';
                break;
            case 'bottom':
                positionStyle = 'top: 100%; left: 50%;';
                transform = 'translateX(-50%)';
                margin = 'margin-top: 5px;';
                break;
            case 'left':
                positionStyle = 'right: 100%; top: 50%;';
                transform = 'translateY(-50%)';
                margin = 'margin-right: 5px;';
                break;
            case 'right':
                positionStyle = 'left: 100%; top: 50%;';
                transform = 'translateY(-50%)';
                margin = 'margin-left: 5px;';
                break;
            default:
                positionStyle = 'bottom: 100%; left: 50%;';
                transform = 'translateX(-50%)';
                margin = 'margin-bottom: 5px;';
        }

        return `${positionStyle} transform: ${transform}; ${margin}`;
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
    onmouseenter={showTooltipHandler}
    onmouseleave={hideTooltipHandler}
    onfocusin={showTooltipHandler}
    onfocusout={hideTooltipHandler}
    onkeydown={(e) => e.key === 'Escape' && hideTooltipHandler()}
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
