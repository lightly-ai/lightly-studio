<script lang="ts">
    import { Maximize2 as Maximize2Icon } from '@lucide/svelte';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { Input } from '$lib/components/ui/input/index.js';
    import ConfusionMatrix from '../ConfusionMatrix.svelte';
    import type { ConfusionMatrix as ConfusionMatrixData } from '../types';
    import TopNConfusionMatrix from './TopNConfusionMatrix.svelte';
    import { buildSubMatrix, filterClasses, getRealClasses } from './topNMatrix';

    interface Props {
        matrix: ConfusionMatrixData;
        topN?: number;
        classCountThreshold?: number;
        showLegend?: boolean;
    }

    const { matrix, topN = 12, classCountThreshold = 30, showLegend = false }: Props = $props();

    let open = $state(false);
    let query = $state('');

    const realClasses = $derived(getRealClasses(matrix));
    const matchingClasses = $derived(filterClasses(realClasses, query));
    const dialogMatrix = $derived(
        matchingClasses.length < realClasses.length
            ? buildSubMatrix(matrix, matchingClasses)
            : matrix
    );

    $effect(() => {
        if (!open) query = '';
    });
</script>

<TopNConfusionMatrix {matrix} {topN} {classCountThreshold} {showLegend} />
<div class="mt-1 flex justify-end">
    <Button
        variant="outline"
        size="sm"
        onclick={() => (open = true)}
        data-testid="confusion-matrix-expand"
    >
        <Maximize2Icon />
        Full matrix
    </Button>
</div>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Confusion matrix · all {realClasses.length} classes</Dialog.Title>
            <Dialog.Description>
                Scroll or pinch inside the chart to zoom · hover a cell for details
            </Dialog.Description>
        </Dialog.Header>
        <div class="flex items-center gap-2">
            <Input
                bind:value={query}
                placeholder="Filter classes, e.g. car, truck, bus"
                class="h-8 max-w-[260px]"
                data-testid="confusion-matrix-class-filter"
            />
            {#if query.trim()}
                <span class="text-xs text-muted-foreground">
                    {matchingClasses.length} matching · rest aggregated as “(other)”
                </span>
            {/if}
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto">
            <ConfusionMatrix matrix={dialogMatrix} {showLegend} zoomable />
        </div>
    </Dialog.Content>
</Dialog.Root>
