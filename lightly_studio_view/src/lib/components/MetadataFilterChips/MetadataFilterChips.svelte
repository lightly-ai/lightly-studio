<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useMetadataFilterChips } from './useMetadataFilterChips';

    interface Props {
        collectionId?: string;
    }

    const { collectionId }: Props = $props();

    const { chips, handleToggle, handleClear, formatValue } = useMetadataFilterChips(collectionId);
</script>

{#if $chips.length > 0}
    <Segment title="Metadata filters">
        <div class="space-y-2">
            {#each $chips as chip (chip.key)}
                <FilterChip
                    testId="metadata-filter-chip-{chip.key}"
                    checked={chip.active}
                    title={chip.key}
                    checkboxLabel={chip.active
                        ? `Disable ${chip.key} filter`
                        : `Enable ${chip.key} filter`}
                    onCheckedChange={(checked) => handleToggle(chip.key, checked)}
                    onClear={() => handleClear(chip.key)}
                >
                    {#snippet subtitle()}
                        {#if chip.range}
                            <div class="truncate text-xs text-muted-foreground">
                                {formatValue(chip.key, chip.range.min)} – {formatValue(
                                    chip.key,
                                    chip.range.max
                                )}
                            </div>
                        {/if}
                    {/snippet}
                </FilterChip>
            {/each}
        </div>
    </Segment>
{/if}
