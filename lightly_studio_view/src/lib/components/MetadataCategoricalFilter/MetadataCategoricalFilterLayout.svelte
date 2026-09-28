<script lang="ts">
    import type { Snippet } from 'svelte';
    import MetadataCategoricalFilterDropdown from './MetadataCategoricalFilterDropdown.svelte';
    import MetadataCategoricalFilterList from './MetadataCategoricalFilterList.svelte';

    interface Props {
        fieldLabel: string;
        layout: 'dropdown' | 'list';
        summary: string;
        disabled: boolean;
        loading: boolean;
        updating: boolean;
        onRemove?: () => void;
        onOpenChange: (open: boolean) => void;
        children: Snippet;
    }

    const {
        fieldLabel,
        layout,
        summary,
        disabled,
        loading,
        updating,
        onRemove,
        onOpenChange,
        children
    }: Props = $props();
</script>

{#if layout === 'list'}
    <MetadataCategoricalFilterList
        {fieldLabel}
        {summary}
        {disabled}
        {loading}
        {updating}
        {onRemove}
        {onOpenChange}
    >
        {#snippet children()}
            {@render children()}
        {/snippet}
    </MetadataCategoricalFilterList>
{:else}
    <MetadataCategoricalFilterDropdown
        {fieldLabel}
        {summary}
        {disabled}
        {loading}
        {updating}
        {onRemove}
        {onOpenChange}
    >
        {#snippet children()}
            {@render children()}
        {/snippet}
    </MetadataCategoricalFilterDropdown>
{/if}
