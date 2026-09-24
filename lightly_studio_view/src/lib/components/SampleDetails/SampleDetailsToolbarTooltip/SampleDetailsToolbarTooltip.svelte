<script lang="ts">
    import type { Snippet } from 'svelte';

    const {
        label,
        shortcut,
        action,
        verb = 'Press',
        hint,
        position = 'right',
        children
    }: {
        label: string;
        shortcut?: string;
        action?: string;
        // Word before the key, e.g. 'Hold' for a modifier held while dragging.
        verb?: string;
        hint?: string;
        position?: 'right' | 'top';
        children: Snippet;
    } = $props();
    let visible = $state(false);
    let triggerRect = $state<DOMRect | null>(null);
    let triggerElement: HTMLElement;

    // Rendered on document.body with fixed positioning so a parent with hidden overflow, like
    // the embedding plot panel, cannot clip it.
    function portal(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                node.remove();
            }
        };
    }

    const OFFSET = 12;

    function positionStyle(rect: DOMRect): string {
        if (position === 'top') {
            return `left: ${rect.left + rect.width / 2}px; top: ${rect.top - OFFSET}px; transform: translate(-50%, -100%);`;
        }
        return `left: ${rect.right + OFFSET}px; top: ${rect.top + rect.height / 2}px; transform: translate(0, -50%);`;
    }

    function show() {
        triggerRect = triggerElement.getBoundingClientRect();
        visible = true;
    }
</script>

<div
    class="relative"
    role="region"
    bind:this={triggerElement}
    onpointerenter={show}
    onpointerleave={() => (visible = false)}
    onpointerdown={() => (visible = false)}
>
    {@render children()}

    {#if visible && triggerRect}
        <div use:portal class="pointer-events-none fixed z-50" style={positionStyle(triggerRect)}>
            <div
                class="
          flex
          flex-col
          gap-0.5 whitespace-nowrap
          rounded-lg border
          border-white/10 bg-black
          px-3
          py-2
          text-xs text-white shadow-lg
        "
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
