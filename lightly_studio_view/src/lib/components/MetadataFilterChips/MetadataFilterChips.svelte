<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import { useDimensionFilterChips } from './useDimensionFilterChips.svelte';
    import { useMetadataFilterChips } from './useMetadataFilterChips.svelte';

    interface Props {
        collectionId?: string;
        /** Whether to show chips for the image width and height filters. */
        showDimensions?: boolean;
    }

    const { collectionId, showDimensions = false }: Props = $props();

    const hook = $derived.by(() => useMetadataFilterChips(collectionId));
    const dimensions = useDimensionFilterChips();
    const dimensionChips = $derived(showDimensions ? dimensions.chips : []);
    const hasChips = $derived(hook.chips.length > 0 || dimensionChips.length > 0);

    const checkboxLabel = (title: string, active: boolean) =>
        active ? `Disable ${title} filter` : `Enable ${title} filter`;
</script>

{#if hasChips}
    <div class="space-y-2" data-testid="metadata-filter-chips">
        {#each dimensionChips as chip (chip.key)}
            {@const title = chip.key === 'width' ? 'Width' : 'Height'}
            <FilterChip
                testId="metadata-filter-chip-image-{chip.key}"
                checked={chip.active}
                {title}
                checkboxLabel={checkboxLabel(title, chip.active)}
                onCheckedChange={(checked) => dimensions.handleToggle(chip.key, checked)}
                onClear={() => dimensions.handleClear(chip.key)}
            >
                {#snippet subtitle()}
                    <div class="truncate text-xs text-muted-foreground">
                        {dimensions.formatValue(chip.key, chip.range.min)} – {dimensions.formatValue(
                            chip.key,
                            chip.range.max
                        )}px
                    </div>
                {/snippet}
            </FilterChip>
        {/each}
        {#each hook.chips as chip (chip.key)}
            <FilterChip
                testId="metadata-filter-chip-{chip.key}"
                checked={chip.active}
                title={chip.key}
                checkboxLabel={checkboxLabel(chip.key, chip.active)}
                onCheckedChange={(checked) => hook.handleToggle(chip.key, checked)}
                onClear={() => hook.handleClear(chip.key)}
            >
                {#snippet subtitle()}
                    <div class="truncate text-xs text-muted-foreground">
                        {#if chip.kind === 'categorical'}
                            {hook.formatCategoricalValues(chip.values)}
                        {:else if chip.range}
                            {hook.formatValue(chip.key, chip.range.min)} – {hook.formatValue(
                                chip.key,
                                chip.range.max
                            )}
                        {/if}
                    </div>
                {/snippet}
            </FilterChip>
        {/each}
    </div>
{/if}
