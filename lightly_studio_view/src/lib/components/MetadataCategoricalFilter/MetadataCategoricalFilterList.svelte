<script lang="ts">
    import MetadataFieldHeader from '$lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte';
    import type { Snippet } from 'svelte';

    interface Props {
        fieldLabel: string;
        updating: boolean;
        expanded: boolean;
        onToggleExpanded?: () => void;
        onRemove?: () => void;
        children: Snippet;
    }

    const { fieldLabel, updating, expanded, onToggleExpanded, onRemove, children }: Props =
        $props();
</script>

<!-- Same field layout as the metadata sliders: a header, then the values inline. -->
<div class="space-y-1" data-testid="metadata-categorical-filter">
    <MetadataFieldHeader
        title={fieldLabel}
        status={updating ? 'Updating…' : undefined}
        {expanded}
        {onToggleExpanded}
        {onRemove}
    />
    {#if expanded}
        {@render children()}
    {/if}
</div>
