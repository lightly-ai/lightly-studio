<script lang="ts">
    import type { SelectItem } from '$lib/components/Select';

    let {
        items = [],
        onValueChange
    }: { items?: SelectItem[]; onValueChange?: (value: string) => void } = $props();
</script>

{#each items as item (item.value)}
    <button data-testid={item.testId} onclick={() => onValueChange?.(item.value)}>
        {item.label}
    </button>
{/each}
