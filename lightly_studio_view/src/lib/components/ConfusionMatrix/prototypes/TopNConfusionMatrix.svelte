<script lang="ts">
    import { Button } from '$lib/components/ui/button/index.js';
    import ConfusionMatrix from '../ConfusionMatrix.svelte';
    import type { ConfusionMatrix as ConfusionMatrixData } from '../types';
    import ClassMultiSelect from './ClassMultiSelect.svelte';
    import { buildSubMatrix, getRealClasses, rankClassesByConfusion } from './topNMatrix';

    interface Props {
        matrix: ConfusionMatrixData;
        /** Number of most-confused classes shown by default. */
        topN?: number;
        /** Below this class count the full matrix is shown unchanged. */
        classCountThreshold?: number;
        showLegend?: boolean;
    }

    const { matrix, topN = 12, classCountThreshold = 30, showLegend = false }: Props = $props();

    const realClasses = $derived(getRealClasses(matrix));
    const isLarge = $derived(realClasses.length > classCountThreshold);
    const topClasses = $derived(rankClassesByConfusion(matrix).slice(0, topN));

    // null = default top-N selection; set once the user edits the class list.
    let customSelection: string[] | null = $state(null);
    const selected = $derived(customSelection ?? topClasses);
    const subMatrix = $derived(buildSubMatrix(matrix, selected));

    const handleToggle = (className: string) => {
        customSelection = selected.includes(className)
            ? selected.filter((c) => c !== className)
            : [...selected, className];
    };
</script>

{#if !isLarge}
    <ConfusionMatrix {matrix} {showLegend} />
{:else}
    <div class="mb-2 flex items-center justify-between gap-2">
        <span class="text-xs text-muted-foreground">
            Showing {selected.length} of {realClasses.length} classes
            {customSelection ? '(custom)' : '(most confused)'} · rest aggregated as “(other)”
        </span>
        <div class="flex shrink-0 items-center gap-1">
            {#if customSelection}
                <Button variant="ghost" size="sm" onclick={() => (customSelection = null)}>
                    Reset
                </Button>
            {/if}
            <ClassMultiSelect allClasses={realClasses} {selected} onToggle={handleToggle} />
        </div>
    </div>
    <ConfusionMatrix matrix={subMatrix} {showLegend} />
{/if}
