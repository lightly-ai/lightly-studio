<script lang="ts">
    import { cn } from '$lib/utils/shadcn.js';
    import type { Snippet } from 'svelte';
    import { fly } from 'svelte/transition';
    import { onDestroy } from 'svelte';

    let {
        content,
        position = 'top',
        class: className,
        triggerClass,
        children
    }: {
        content: string;
        position?: 'top' | 'bottom' | 'left' | 'right';
        class?: string;
        triggerClass?: string;
        children: Snippet;
    } = $props();

    let showTooltip = $state(false);
    let triggerRect: DOMRect | null = $state(null);
    let triggerElement: HTMLElement;

    const updateRect = () => {
        if (!triggerElement) return;
        triggerRect = triggerElement.getBoundingClientRect();
    };

    function getPositionStyles() {
        if (!triggerRect) return '';

        const offset = 6;
        const { top, left, right, bottom, width, height } = triggerRect;

        switch (position) {
            case 'top':
                return `position: fixed; left: ${left + width / 2}px; top: ${top - offset}px; transform: translate(-50%, -100%);`;
            case 'bottom':
                return `position: fixed; left: ${left + width / 2}px; top: ${bottom + offset}px; transform: translate(-50%, 0);`;
            case 'left':
                return `position: fixed; left: ${left - offset}px; top: ${top + height / 2}px; transform: translate(-100%, -50%);`;
            case 'right':
                return `position: fixed; left: ${right + offset}px; top: ${top + height / 2}px; transform: translate(0, -50%);`;
            default:
                return `position: fixed; left: ${left + width / 2}px; top: ${top - offset}px; transform: translate(-50%, -100%);`;
        }
    }

    function showTooltipHandler() {
        updateRect();
        showTooltip = true;
    }

    function hideTooltipHandler() {
        showTooltip = false;
    }

    // Keep tooltip aligned on resize/scroll; avoids clipping in scrollable side panels.
    const handleWindowChange = () => {
        if (showTooltip) updateRect();
    };

    onDestroy(() => {
        if (typeof window === 'undefined') return;
        window.removeEventListener('resize', handleWindowChange);
        window.removeEventListener('scroll', handleWindowChange, true);
    });

    $effect(() => {
        if (typeof window === 'undefined') return;

        if (!showTooltip) {
            window.removeEventListener('resize', handleWindowChange);
            window.removeEventListener('scroll', handleWindowChange, true);
            return;
        }

        window.addEventListener('resize', handleWindowChange);
        window.addEventListener('scroll', handleWindowChange, true);
        updateRect();

        return () => {
            window.removeEventListener('resize', handleWindowChange);
            window.removeEventListener('scroll', handleWindowChange, true);
        };
    });
</script>

<div
    class={cn('relative inline-block', triggerClass)}
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
