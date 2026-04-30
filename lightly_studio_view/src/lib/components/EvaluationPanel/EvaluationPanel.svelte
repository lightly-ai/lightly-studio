<script lang="ts">
    import { useEvaluations } from '$lib/hooks/useEvaluations/useEvaluations';
    import { useEvaluationSampleCounts } from '$lib/hooks/useEvaluationSampleCounts/useEvaluationSampleCounts';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { type EvaluationCountMetric, useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import type {
        EvaluationResultView,
        GetEvaluationSampleCountsResponse
    } from '$lib/api/lightly_studio_local';
    import { ChevronDown, ChevronRight, X } from '@lucide/svelte';

    const EMPTY_RESULT_SAMPLE_ID = '00000000-0000-0000-0000-000000000000';

    const { datasetId }: { datasetId: string } = $props();

    const {
        activeEvaluationId,
        setActiveEvaluationId,
        setShowEvalPanel,
        evaluationSampleSort,
        setEvaluationSampleSort
    } = useGlobalStorage();
    const { updateSampleIds } = useImageFilters();

    const evaluationsQuery = $derived(useEvaluations({ datasetId }));
    const evaluations = $derived($evaluationsQuery.data ?? []);

    const collectionsQuery = $derived(useAnnotationCollections({ datasetId }));
    const collections = $derived($collectionsQuery.data ?? []);

    const collectionNameById = $derived(Object.fromEntries(collections.map((c) => [c.id, c.name])));

    const countsQuery = $derived(
        useEvaluationSampleCounts({
            datasetId,
            evaluationId: $activeEvaluationId
        })
    );
    const sampleCounts = $derived(
        (($countsQuery.data as GetEvaluationSampleCountsResponse | undefined)?.counts ??
            {}) as Record<string, Record<string, number>>
    );

    // TP/FP/FN filter state
    let minFp = $state<number | undefined>(undefined);
    let maxFp = $state<number | undefined>(undefined);
    let minFn = $state<number | undefined>(undefined);
    let maxFn = $state<number | undefined>(undefined);
    let minTp = $state<number | undefined>(undefined);
    let maxTp = $state<number | undefined>(undefined);
    let sortMetric = $state<EvaluationCountMetric | ''>('');
    let sortDirection = $state<'asc' | 'desc'>('desc');

    $effect(() => {
        if (evaluations.length === 0) {
            return;
        }

        if (
            !$activeEvaluationId ||
            !evaluations.some((evaluation) => evaluation.id === $activeEvaluationId)
        ) {
            setActiveEvaluationId(evaluations[0].id);
        }
    });

    $effect(() => {
        if (!$evaluationSampleSort) {
            sortMetric = '';
            sortDirection = 'desc';
            return;
        }

        sortMetric = $evaluationSampleSort.metric;
        sortDirection = $evaluationSampleSort.direction;
    });

    function selectEval(id: string) {
        setActiveEvaluationId(id);
        // Reset filters when switching evals
        minFp = undefined;
        maxFp = undefined;
        minFn = undefined;
        maxFn = undefined;
        minTp = undefined;
        maxTp = undefined;
        setEvaluationSampleSort(null);
        updateSampleIds([]);
    }

    function applyCountFilter() {
        const matchingSampleIds = Object.entries(sampleCounts)
            .filter(([, counts]) => {
                const fp = counts.fp ?? 0;
                const fn = counts.fn ?? 0;
                const tp = counts.tp ?? 0;
                if (minFp != null && fp < minFp) return false;
                if (maxFp != null && fp > maxFp) return false;
                if (minFn != null && fn < minFn) return false;
                if (maxFn != null && fn > maxFn) return false;
                if (minTp != null && tp < minTp) return false;
                if (maxTp != null && tp > maxTp) return false;
                return true;
            })
            .map(([sampleId]) => sampleId);
        updateSampleIds(
            matchingSampleIds.length > 0 ? matchingSampleIds : [EMPTY_RESULT_SAMPLE_ID]
        );
    }

    function clearCountFilter() {
        minFp = undefined;
        maxFp = undefined;
        minFn = undefined;
        maxFn = undefined;
        minTp = undefined;
        maxTp = undefined;
        updateSampleIds([]);
    }

    function applySort() {
        if (!sortMetric) {
            setEvaluationSampleSort(null);
            return;
        }

        setEvaluationSampleSort({
            metric: sortMetric,
            direction: sortDirection
        });
    }

    function clearSort() {
        sortMetric = '';
        sortDirection = 'desc';
        setEvaluationSampleSort(null);
    }

    function formatDate(date: Date) {
        return new Date(date).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatPct(val: number) {
        return (val * 100).toFixed(1) + '%';
    }

    function formatTaskType(taskType: string) {
        return taskType
            .split('_')
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join(' ');
    }

    function hasMetric(metrics: unknown, key: string): metrics is Record<string, number> {
        return (
            typeof metrics === 'object' &&
            metrics !== null &&
            key in metrics &&
            typeof (metrics as Record<string, unknown>)[key] === 'number'
        );
    }

    function hasPerClassMetrics(
        metrics: unknown
    ): metrics is { per_class_metrics: Record<string, Record<string, number>> } {
        return (
            typeof metrics === 'object' &&
            metrics !== null &&
            'per_class_metrics' in metrics &&
            typeof (metrics as Record<string, unknown>).per_class_metrics === 'object' &&
            (metrics as Record<string, unknown>).per_class_metrics !== null
        );
    }

    const selectedEval = $derived<EvaluationResultView | undefined>(
        evaluations.find((e) => e.id === $activeEvaluationId)
    );

    const subsets = $derived(selectedEval ? Object.keys(selectedEval.metrics) : []);

    let expandedSubset = $state<string | null>('all');
</script>

<div class="flex h-full flex-col overflow-hidden rounded-[1vw] bg-card p-4">
    <!-- Header -->
    <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Evaluation Runs</h2>
        <button
            class="text-muted-foreground hover:text-foreground"
            onclick={() => setShowEvalPanel(false)}
            title="Close"
        >
            <X class="size-4" />
        </button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
        <!-- Eval run list -->
        <div class="space-y-1">
            {#if $evaluationsQuery.isLoading}
                <p class="text-xs text-muted-foreground">Loading…</p>
            {:else if evaluations.length === 0}
                <p class="text-xs text-muted-foreground">No evaluation runs yet.</p>
            {:else}
                {#each evaluations as ev (ev.id)}
                    {@const isSelected = $activeEvaluationId === ev.id}
                    <button
                        class="w-full rounded-md px-3 py-2 text-left text-xs transition-colors {isSelected
                            ? 'bg-primary text-primary-foreground'
                            : 'hover:bg-muted'}"
                        onclick={() => selectEval(ev.id)}
                    >
                        <div class="font-medium">
                            {collectionNameById[ev.prediction_collection_id] ??
                                ev.prediction_collection_id.slice(0, 8)}
                        </div>
                        <div class="text-[10px] opacity-70">
                            {formatDate(ev.created_at)} · IoU {ev.iou_threshold}
                        </div>
                    </button>
                {/each}
            {/if}
        </div>

        {#if evaluations.length > 0 && !selectedEval}
            <div
                class="rounded-md border border-dashed border-border bg-background px-3 py-4 text-xs text-muted-foreground"
            >
                Select an evaluation run to inspect its configuration and metrics.
            </div>
        {/if}

        {#if selectedEval}
            <div class="rounded-md border border-border bg-background px-3 py-2 text-xs">
                <div class="mb-2 font-medium">Configuration</div>
                <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                    <span class="text-muted-foreground">Predictions</span>
                    <span class="truncate text-right font-mono">
                        {collectionNameById[selectedEval.prediction_collection_id] ??
                            selectedEval.prediction_collection_id.slice(0, 8)}
                    </span>
                    <span class="text-muted-foreground">Ground truth</span>
                    <span class="truncate text-right font-mono">
                        {collectionNameById[selectedEval.gt_collection_id] ??
                            selectedEval.gt_collection_id.slice(0, 8)}
                    </span>
                    <span class="text-muted-foreground">Task</span>
                    <span class="text-right font-mono">
                        {formatTaskType(selectedEval.task_type)}
                    </span>
                    <span class="text-muted-foreground">IoU</span>
                    <span class="text-right font-mono">{selectedEval.iou_threshold}</span>
                    <span class="text-muted-foreground">Confidence</span>
                    <span class="text-right font-mono">{selectedEval.confidence_threshold}</span>
                </div>
            </div>

            <!-- Metrics table -->
            <div class="rounded-md border border-border bg-background">
                <div class="border-b border-border px-3 py-2 text-xs font-medium">Metrics</div>
                {#each subsets as subset}
                    {@const metrics = selectedEval.metrics[subset]}
                    <button
                        class="w-full border-b border-border px-3 py-2 text-left text-xs last:border-b-0 hover:bg-muted"
                        onclick={() => (expandedSubset = expandedSubset === subset ? null : subset)}
                    >
                        <div class="flex items-center justify-between">
                            <span class="font-medium">{subset}</span>
                            <span class="text-muted-foreground">
                                {#if expandedSubset === subset}
                                    <ChevronDown class="size-3" />
                                {:else}
                                    <ChevronRight class="size-3" />
                                {/if}
                            </span>
                        </div>
                        {#if expandedSubset === subset}
                            <div class="mt-2 space-y-1 text-[11px]">
                                <div class="grid grid-cols-2 gap-x-4">
                                    {#if hasMetric(metrics, 'accuracy')}
                                        <span class="text-muted-foreground">Accuracy</span>
                                        <span class="text-right font-mono"
                                            >{formatPct(metrics.accuracy)}</span
                                        >
                                    {/if}
                                    {#if hasMetric(metrics, 'mAP')}
                                        <span class="text-muted-foreground">mAP</span>
                                        <span class="text-right font-mono"
                                            >{formatPct(metrics.mAP)}</span
                                        >
                                    {/if}
                                    <span class="text-muted-foreground">Precision</span>
                                    <span class="text-right font-mono"
                                        >{formatPct(metrics.precision)}</span
                                    >
                                    <span class="text-muted-foreground">Recall</span>
                                    <span class="text-right font-mono"
                                        >{formatPct(metrics.recall)}</span
                                    >
                                    <span class="text-muted-foreground">F1</span>
                                    <span class="text-right font-mono">{formatPct(metrics.f1)}</span
                                    >
                                </div>
                                {#if hasPerClassMetrics(metrics) && Object.keys(metrics.per_class_metrics).length > 0}
                                    <div class="mt-2 border-t border-border pt-2">
                                        <div class="mb-1 text-muted-foreground">Per class</div>
                                        {#each Object.entries(metrics.per_class_metrics) as [cls, cm]}
                                            <div class="grid grid-cols-2 gap-x-4">
                                                <span class="truncate text-muted-foreground"
                                                    >{cls}</span
                                                >
                                                {#if 'ap' in cm && typeof cm.ap === 'number'}
                                                    <span class="text-right font-mono"
                                                        >AP {formatPct(cm.ap)}</span
                                                    >
                                                {:else if 'f1' in cm && typeof cm.f1 === 'number'}
                                                    <span class="text-right font-mono"
                                                        >F1 {formatPct(cm.f1)}</span
                                                    >
                                                {:else}
                                                    <span class="text-right font-mono">-</span>
                                                {/if}
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </button>
                {/each}
            </div>

            <div class="rounded-md border border-border bg-background">
                <div class="border-b border-border px-3 py-2 text-xs font-medium">Sort grid</div>
                <div class="space-y-2 px-3 py-2 text-xs">
                    <div class="grid grid-cols-2 gap-2">
                        <select
                            class="rounded border border-input bg-background px-2 py-1"
                            bind:value={sortMetric}
                        >
                            <option value="">None</option>
                            <option value="fp">False positives</option>
                            <option value="fn">False negatives</option>
                            <option value="tp">True positives</option>
                        </select>
                        <select
                            class="rounded border border-input bg-background px-2 py-1"
                            bind:value={sortDirection}
                            disabled={!sortMetric}
                        >
                            <option value="desc">High to low</option>
                            <option value="asc">Low to high</option>
                        </select>
                    </div>
                    <div class="flex gap-2">
                        <button
                            class="rounded bg-primary px-2 py-1 text-xs text-primary-foreground"
                            onclick={applySort}
                        >
                            Apply
                        </button>
                        <button
                            class="rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                            onclick={clearSort}
                        >
                            Clear
                        </button>
                    </div>
                </div>
            </div>

            <!-- TP/FP/FN filter -->
            {#if Object.keys(sampleCounts).length > 0}
                <div class="rounded-md border border-border bg-background">
                    <div class="border-b border-border px-3 py-2 text-xs font-medium">
                        Filter by counts
                    </div>
                    <div class="space-y-2 px-3 py-2 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="w-6 text-muted-foreground">FP</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="min"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={minFp}
                            />
                            <span class="text-muted-foreground">–</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="max"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={maxFp}
                            />
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="w-6 text-muted-foreground">FN</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="min"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={minFn}
                            />
                            <span class="text-muted-foreground">–</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="max"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={maxFn}
                            />
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="w-6 text-muted-foreground">TP</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="min"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={minTp}
                            />
                            <span class="text-muted-foreground">–</span>
                            <input
                                type="number"
                                min="0"
                                placeholder="max"
                                class="w-14 rounded border border-input bg-background px-2 py-1 text-xs"
                                bind:value={maxTp}
                            />
                        </div>
                        <div class="flex gap-2 pt-1">
                            <button
                                class="rounded bg-primary px-2 py-1 text-xs text-primary-foreground"
                                onclick={applyCountFilter}
                            >
                                Apply
                            </button>
                            <button
                                class="rounded border border-border px-2 py-1 text-xs hover:bg-muted"
                                onclick={clearCountFilter}
                            >
                                Clear
                            </button>
                        </div>
                    </div>
                </div>
            {/if}
        {/if}
    </div>
</div>
