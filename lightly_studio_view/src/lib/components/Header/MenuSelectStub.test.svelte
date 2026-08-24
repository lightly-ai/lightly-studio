<script lang="ts">
    import type { Component } from 'svelte';

    interface Item {
        value: string;
        label: string;
        icon?: Component;
    }

    const { items, onValueChange }: { items: Item[]; onValueChange: (value: string) => void } =
        $props();
</script>

{#each items as item (item.value)}
    <button onclick={() => onValueChange(item.value)}>{item.label}</button>
{/each}
