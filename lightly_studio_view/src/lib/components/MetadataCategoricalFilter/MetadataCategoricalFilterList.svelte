<script lang="ts">
    import MetadataFieldHeader from '$lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte';
    import type { Snippet } from 'svelte';

    interface Props {
        fieldLabel: string;
        status?: string;
        expanded: boolean;
        onToggleExpanded?: () => void;
        onRemove?: () => void;
        checked?: boolean;
        summary?: string;
        onClearField?: () => void;
        children: Snippet;
    }

    const {
        fieldLabel,
        status,
        expanded,
        onToggleExpanded,
        onRemove,
        checked,
        summary,
        onClearField,
        children
    }: Props = $props();
</script>

<!-- Same field layout as the metadata sliders: a header, then the values inline. -->
<div class="space-y-1" data-testid="metadata-categorical-filter">
    <MetadataFieldHeader
        title={fieldLabel}
        {status}
        {expanded}
        {onToggleExpanded}
        {onRemove}
        {checked}
        {summary}
        onClear={onClearField}
    />
    {#if expanded}
        <div class="pl-6">
            {@render children()}
        </div>
    {/if}
</div>
