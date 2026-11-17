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
        status?: string;
        onRemove?: () => void;
        onOpenChange?: (open: boolean) => void;
        expanded: boolean;
        onToggleExpanded?: () => void;
        children: Snippet;
    }

    const {
        fieldLabel,
        layout,
        summary,
        disabled,
        loading,
        updating,
        status,
        onRemove,
        onOpenChange,
        expanded,
        onToggleExpanded,
        children: content
    }: Props = $props();
</script>

{#if layout === 'list'}
    <MetadataCategoricalFilterList {fieldLabel} {status} {expanded} {onToggleExpanded} {onRemove}>
        {#snippet children()}
            {@render content()}
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
            {@render content()}
        {/snippet}
    </MetadataCategoricalFilterDropdown>
{/if}
