<script lang="ts">
    import { untrack } from 'svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { formatMetadataValue } from '$lib/utils';
    import MetadataCategorySelector from './MetadataCategorySelector.svelte';

    type MetadataDict = {
        data: Record<string, unknown>;
    };

    const { metadata_dict } = $props();
    let selectedCategories = $state<string[] | null>(null);
    let previousAvailableIds: string[] = [];

    // Use derived value for proper reactivity when sample changes
    const metadata = $derived.by(() => {
        const customMetadata: Array<{
            id: string;
            label: string;
            value: string;
            isComplex: boolean;
        }> = [];

        if (metadata_dict && typeof metadata_dict === 'object' && 'data' in metadata_dict) {
            const metadataData = (metadata_dict as MetadataDict).data;
            if (metadataData && typeof metadataData === 'object') {
                Object.entries(metadataData).forEach(([key, value]) => {
                    const formattedValue = formatMetadataValue(value);
                    const isComplex =
                        typeof value === 'object' && value !== null && !Array.isArray(value);
                    customMetadata.push({
                        id: `metadata_${key}`,
                        label: `${key}:`,
                        value: formattedValue,
                        isComplex
                    });
                });
            }
        }
        return customMetadata;
    });
    const categoryItems = $derived(
        metadata.map(({ id, label }) => ({
            value: id,
            label: label.slice(0, -1)
        }))
    );
    const visibleMetadata = $derived(
        selectedCategories === null
            ? metadata
            : metadata.filter(({ id }) => selectedCategories?.includes(id))
    );
    $effect(() => {
        const availableIds = metadata.map(({ id }) => id);
        const currentSelection = untrack(() => selectedCategories);
        const previousIds = untrack(() => previousAvailableIds);
        if (currentSelection !== null) {
            selectedCategories = [
                ...currentSelection.filter((id) => availableIds.includes(id)),
                ...availableIds.filter((id) => !previousIds.includes(id))
            ];
        }
        previousAvailableIds = availableIds;
    });
</script>

{#if metadata.length > 0}
    <Segment title="Metadata">
        <div class="mb-3">
            <MetadataCategorySelector
                items={categoryItems}
                selectedIds={selectedCategories}
                onChange={(ids) => (selectedCategories = ids)}
            />
        </div>
        <div class="space-y-3 text-diffuse-foreground">
            {#each visibleMetadata as { label, value, id, isComplex } (label)}
                {#if isComplex}
                    <!-- Complex objects on same line with offset -->
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title={label}>{label}</span>
                        <pre
                            class="min-w-[8rem] flex-1 overflow-x-auto whitespace-pre-wrap rounded bg-muted p-2 text-sm">{value}</pre>
                    </div>
                {:else}
                    <!-- Simple values use the grid layout -->
                    <div class="flex items-start gap-3">
                        <span class="truncate text-sm font-medium" title={label}>{label}</span>
                        <span
                            class="min-w-[8rem] flex-1 break-all text-sm"
                            data-testid={`sample-metadata-${id}`}>{value}</span
                        >
                    </div>
                {/if}
            {/each}
        </div>
    </Segment>
{/if}
