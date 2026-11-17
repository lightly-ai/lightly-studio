<script lang="ts">
    import MetadataFieldHeader from '$lib/components/MetadataFieldHeader/MetadataFieldHeader.svelte';
    import type { Snippet } from 'svelte';

    interface Props {
        fieldLabel: string;
        status?: string;
        expanded: boolean;
        onToggleExpanded?: () => void;
        onRemove?: () => void;
        children: Snippet;
    }

    const { fieldLabel, status, expanded, onToggleExpanded, onRemove, children }: Props = $props();
</script>

<!-- Same field layout as the metadata sliders: a header, then the values inline. -->
<div class="space-y-1" data-testid="metadata-categorical-filter">
    <MetadataFieldHeader title={fieldLabel} {status} {expanded} {onToggleExpanded} {onRemove} />
    {#if expanded}
        <!-- Indented under the chevron. -->
        <div class={onToggleExpanded ? 'pl-6' : undefined}>
            {@render children()}
        </div>
    {/if}
</div>
