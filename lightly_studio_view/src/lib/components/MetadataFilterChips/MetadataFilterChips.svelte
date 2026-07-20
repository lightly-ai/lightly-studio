<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useMetadataFilterChips } from './useMetadataFilterChips.svelte';

    interface Props {
        collectionId?: string;
    }

    const { collectionId }: Props = $props();

    const hook = useMetadataFilterChips(collectionId);
</script>

{#if hook.chips.length > 0}
    <Segment title="Metadata filters">
        <div class="space-y-2">
            {#each hook.chips as chip (chip.key)}
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
                            {hook.formatValue(chip.key, chip.range.min)} – {hook.formatValue(
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
