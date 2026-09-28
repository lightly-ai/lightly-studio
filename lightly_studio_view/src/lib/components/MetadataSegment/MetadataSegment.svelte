<script lang="ts">
    import { untrack } from 'svelte';
    import { ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { formatMetadataValue } from '$lib/utils';

    type MetadataDict = {
        data: Record<string, unknown>;
    };

    const { metadata_dict } = $props();
    let selectedCategories = $state<string[] | null>(null);

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
    const categoryLabel = $derived(
        selectedCategories === null || selectedCategories.length === metadata.length
            ? 'All categories'
            : `${selectedCategories.length} categories selected`
    );

    $effect(() => {
        const availableIds = metadata.map(({ id }) => id);
        const currentSelection = untrack(() => selectedCategories);
        if (currentSelection !== null) {
            selectedCategories = [
                ...currentSelection.filter((id) => availableIds.includes(id)),
                ...availableIds.filter((id) => !currentSelection.includes(id))
            ];
        }
    });
</script>

{#if metadata.length > 0}
    <Segment title="Metadata">
        <div class="mb-3">
            <Popover.Root>
                <Popover.Trigger>
                    {#snippet child({ props })}
                        <Button
                            {...props}
                            variant="outline"
                            size="sm"
                            class="h-8 w-full justify-between px-3 text-xs font-normal"
                            role="combobox"
                            aria-label="Choose metadata categories"
                            data-testid="metadata-category-select"
                        >
                            <span class="truncate">{categoryLabel}</span>
                            <ChevronDown class="ml-2 size-4 shrink-0 opacity-50" />
                        </Button>
                    {/snippet}
                </Popover.Trigger>
                <Popover.Content class="w-[min(320px,calc(100vw-2rem))] p-2" align="start">
                    <MultiSelectList
                        items={categoryItems}
                        selectedIds={selectedCategories ?? categoryItems.map(({ value }) => value)}
                        onChange={(ids) => (selectedCategories = ids)}
                        showSelectAll
                        itemNoun="category"
                        itemNounPlural="categories"
                        searchTestId="metadata-category-search"
                    />
                </Popover.Content>
            </Popover.Root>
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
