<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { X } from '@lucide/svelte';

    const { filterParams, updateConfusionCell } = useImageFilters();

    // The selected cell lives in the shared, module-level filter store, so this chip
    // stays in sync with clicks coming from the confusion matrix panel.
    const confusionCell = $derived(
        $filterParams?.mode === 'normal' ? ($filterParams.filters?.confusion_cell ?? null) : null
    );

    const clearFilter = () => {
        updateConfusionCell(null);
    };
</script>

{#if confusionCell}
    <Segment title="Confusion Matrix">
        <div
            class="flex items-center gap-2 rounded-md border border-[#3c3c3c] bg-muted px-2 py-2"
            data-testid="confusion-cell-filter-item-chip"
        >
            <Checkbox
                checked={true}
                aria-label="Confusion cell filter"
                onCheckedChange={(nextChecked) => {
                    if (nextChecked !== true) clearFilter();
                }}
            />
            <dl
                class="grid min-w-0 flex-1 grid-cols-[max-content_minmax(0,1fr)] items-baseline gap-x-2 gap-y-1 text-sm"
            >
                {#each [{ role: 'Ground truth', value: confusionCell.gt_label, missing: 'No ground truth' }, { role: 'Prediction', value: confusionCell.pred_label, missing: 'No prediction' }] as field (field.role)}
                    <dt class="text-xs text-muted-foreground">{field.role}</dt>
                    <dd class="[overflow-wrap:anywhere]">
                        {#if field.value == null}
                            <em class="text-muted-foreground">{field.missing}</em>
                        {:else}
                            <span class="font-medium">{field.value}</span>
                        {/if}
                    </dd>
                {/each}
            </dl>
            <button
                type="button"
                class="shrink-0 text-muted-foreground hover:text-foreground"
                onclick={clearFilter}
                title="Clear confusion matrix filter"
                aria-label="Clear confusion matrix filter"
            >
                <X class="size-4" />
            </button>
        </div>
    </Segment>
{/if}
