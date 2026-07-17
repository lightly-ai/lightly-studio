<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useMetadataFilterChips } from './useMetadataFilterChips.svelte';

    interface Props {
        collectionId?: string;
    }

    const { collectionId }: Props = $props();

    const { chips, handleToggle, handleClear, formatValue } = useMetadataFilterChips(collectionId);

    const prettify = (key: string): string => key.replace(/_/g, ' ');
</script>

{#if chips.length > 0}
    <Segment title="Metadata filters">
        <div class="space-y-2">
            {#each chips as chip (chip.key)}
                <FilterChip
                    testId="metadata-filter-chip-{chip.key}"
                    checked={chip.active}
                    title={prettify(chip.key)}
                    checkboxLabel={chip.active
                        ? `Disable ${prettify(chip.key)} filter`
                        : `Enable ${prettify(chip.key)} filter`}
                    onCheckedChange={(checked) => handleToggle(chip.key, checked)}
                    onClear={() => handleClear(chip.key)}
                >
                    {#snippet subtitle()}
                        <div class="truncate text-xs text-muted-foreground">
                            {formatValue(chip.key, chip.range.min)} – {formatValue(
                                chip.key,
                                chip.range.max
                            )}
                        </div>
                    {/snippet}
                </FilterChip>
            {/each}
        </div>
    </Segment>
{/if}
