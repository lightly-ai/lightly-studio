<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useDimensionFilterChips } from './useDimensionFilterChips.svelte';
    import { useMetadataFilterChips } from './useMetadataFilterChips.svelte';

    interface Props {
        collectionId?: string;
        isImageCollection?: boolean;
        categoricalKeys?: string[];
        /** Whether to show chips for the image width and height filters. */
        showDimensions?: boolean;
    }

    const {
        collectionId,
        isImageCollection = false,
        categoricalKeys = [],
        showDimensions = false
    }: Props = $props();

    const hook = $derived.by(() => useMetadataFilterChips(collectionId));
    const visibleChips = $derived(
        hook.chips.filter(
            (chip) =>
                chip.kind === 'numeric' ||
                !isImageCollection ||
                (chip.active && !categoricalKeys.includes(chip.key))
        )
    );
    const dimensions = useDimensionFilterChips();
    const dimensionChips = $derived(showDimensions ? dimensions.chips : []);
</script>

{#if visibleChips.length > 0 || dimensionChips.length > 0}
    <Segment title="Metadata filters">
        <div class="space-y-2">
            {#each dimensionChips as chip (chip.key)}
                {@const title = chip.key === 'width' ? 'Width' : 'Height'}
                <FilterChip
                    testId="metadata-filter-chip-image-{chip.key}"
                    checked={chip.active}
                    {title}
                    checkboxLabel={chip.active
                        ? `Disable ${title} filter`
                        : `Enable ${title} filter`}
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
            {#each visibleChips as chip (chip.key)}
                <FilterChip
                    testId="metadata-filter-chip-{chip.key}"
                    checked={chip.active}
                    title={chip.key}
                    checkboxLabel={chip.active
                        ? `Disable ${chip.key} filter`
                        : `Enable ${chip.key} filter`}
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
    </Segment>
{/if}
