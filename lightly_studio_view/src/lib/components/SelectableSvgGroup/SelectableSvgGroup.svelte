<script lang="ts">
    import type { BoundingBox } from '$lib/types';
    import type { Snippet } from 'svelte';

    let {
        children,
        onSelect,
        box,
        isSelected = false,
        groupId
    }: {
        onSelect: (groupId: string) => void;
        isSelected?: boolean;
        groupId: string;
        children: Snippet;
        box: BoundingBox;
    } = $props();

    const x = $derived(box.x);
    const y = $derived(box.y);
    const width = $derived(box.width);
    const height = $derived(box.height);
    const handleSelect = () => {
        onSelect(groupId);
    };

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handleSelect();
        }
    }
</script>

<g
    onclick={handleSelect}
    role="button"
    style:cursor="pointer"
    class="group"
    class:selected={isSelected}
    tabindex="0"
    data-testid="selectable-svg-group"
    data-group-id={groupId}
    onkeydown={handleKeyDown}
>
    {@render children()}

    {#if isSelected}
        <rect
            {x}
            {y}
            {width}
            {height}
            fill="none"
            stroke="hsl(var(--primary))"
            stroke-width="3"
            pointer-events="none"
            vector-effect="non-scaling-stroke"
        />
    {/if}
</g>

<style>
    .group {
        outline: 0;
    }
</style>
