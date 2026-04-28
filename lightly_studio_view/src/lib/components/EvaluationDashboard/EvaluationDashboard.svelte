<script lang="ts">
    import FormField from '$lib/components/FormField/FormField.svelte';
    import * as Alert from '$lib/components/ui/alert';
    import { Button } from '$lib/components/ui';
    import Input from '$lib/components/ui/input/input.svelte';
    import * as Select from '$lib/components/ui/select';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { useAnnotationCollections, useCreateEvaluation, useEvaluation, useEvaluations } from '$lib/hooks';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { ArrowLeftRight, Loader2 } from '@lucide/svelte';
    import type { EvaluationMetrics } from '$lib/api/lightly_studio_local';
    import {
        formatEvaluationLabel,
        formatMetricDelta,
        formatMetricValue,
        getAvailableSubsetNames,
        getGroundTruthCollections,
        getMetricValue,
        getPredictionCollections,
        getSelectedSubsetNames,
        metricRows
    } from './evaluationDashboard';

    let { datasetId }: { datasetId: string } = $props();

    const { collection: datasetCollection } = useCollection({ collectionId: datasetId });
    const backendDatasetId = $derived($datasetCollection.data?.dataset_id);
    const annotationCollectionsQuery = $derived(
        useAnnotationCollections({ datasetId: backendDatasetId })
    );
    const evaluationsQuery = $derived(useEvaluations({ datasetId: backendDatasetId }));
    const { tags } = useTags({ collection_id: datasetId });
    const { mutation, createEvaluation } = $derived(
        useCreateEvaluation({ datasetId: backendDatasetId ?? '' })
    );

    let selectedGroundTruth = $state('');
    let selectedPredictionNames = $state<string[]>([]);
    let selectedTagIds = $state<string[]>([]);
    let selectedEvaluationId = $state('');
    let selectedSubset = $state('all');
    let selectedModel = $state('');
    let mode = $state<'models' | 'subsets'>('models');
    let iouThreshold = $state('0.5');
    let confidenceThreshold = $state('0.0');

    const groundTruthCollections = $derived(getGroundTruthCollections($annotationCollectionsQuery.data));
    const predictionCollections = $derived(getPredictionCollections($annotationCollectionsQuery.data));
    const evaluationQuery = $derived(
        useEvaluation({
            datasetId: backendDatasetId,
            evaluationId: selectedEvaluationId || undefined
        })
    );
    const selectedEvaluation = $derived(
        $evaluationQuery.data ?? $evaluationsQuery.data?.find((item) => item.id === selectedEvaluationId)
    );
    const subsetNames = $derived(
        getSelectedSubsetNames({
            result: selectedEvaluation,
            tags: $tags,
            selectedTagIds
        })
    );
    const modelNames = $derived(selectedEvaluation ? Object.keys(selectedEvaluation.metrics) : []);

    $effect(() => {
        if (!selectedGroundTruth && groundTruthCollections.length > 0) {
            selectedGroundTruth = groundTruthCollections[0].name;
        }
    });

    $effect(() => {
        if (!selectedEvaluationId && $evaluationsQuery.data && $evaluationsQuery.data.length > 0) {
            selectedEvaluationId = $evaluationsQuery.data[0].id;
        }
    });

    $effect(() => {
        if (mode === 'models' && !subsetNames.includes(selectedSubset)) {
            selectedSubset = subsetNames[0] ?? 'all';
        }
        if (mode === 'subsets' && !modelNames.includes(selectedModel)) {
            selectedModel = modelNames[0] ?? '';
        }
    });

    const togglePrediction = (name: string) => {
        selectedPredictionNames = selectedPredictionNames.includes(name)
            ? selectedPredictionNames.filter((item) => item !== name)
            : [...selectedPredictionNames, name];
    };

    const toggleTag = (tagId: string) => {
        selectedTagIds = selectedTagIds.includes(tagId)
            ? selectedTagIds.filter((item) => item !== tagId)
            : [...selectedTagIds, tagId];
    };

    const getDifference = (metricKey: keyof EvaluationMetrics) => {
        if (!selectedEvaluation) {
            return '0.0%';
        }

        if (mode === 'models') {
            const firstModel = modelNames[0];
            const lastModel = modelNames[modelNames.length - 1];
            return formatMetricDelta(
                getMetricValue(selectedEvaluation, firstModel, selectedSubset, metricKey),
                getMetricValue(selectedEvaluation, lastModel, selectedSubset, metricKey)
            );
        }

        const firstSubset = subsetNames[0];
        const lastSubset = subsetNames[subsetNames.length - 1];
        return formatMetricDelta(
            getMetricValue(selectedEvaluation, selectedModel, firstSubset, metricKey),
            getMetricValue(selectedEvaluation, selectedModel, lastSubset, metricKey)
        );
    };

    const handleCompute = async () => {
        const created = await createEvaluation({
            gt_collection_name: selectedGroundTruth,
            prediction_collection_names: selectedPredictionNames,
            iou_threshold: Number(iouThreshold),
            confidence_threshold: Number(confidenceThreshold)
        });
        selectedEvaluationId = created.id;
    };
</script>

<div class="flex flex-col gap-6">
    <section class="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div class="mb-4 flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-semibold">Evaluation</h1>
                <p class="text-sm text-muted-foreground">
                    Compute and compare stored model runs on the current dataset.
                </p>
            </div>
            <Button
                onclick={handleCompute}
                disabled={!selectedGroundTruth || selectedPredictionNames.length === 0 || $mutation.isPending}
            >
                {#if $mutation.isPending}
                    <Loader2 class="mr-2 size-4 animate-spin" />
                {/if}
                Compute
            </Button>
        </div>

        <div class="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            <FormField label="Ground Truth">
                <Select.Root type="single" bind:value={selectedGroundTruth}>
                    <Select.Trigger class="w-full">
                        {selectedGroundTruth || 'Select a ground-truth collection'}
                    </Select.Trigger>
                    <Select.Content>
                        {#each groundTruthCollections as collection}
                            <Select.Item value={collection.name} label={collection.name}>
                                {collection.name}
                            </Select.Item>
                        {/each}
                    </Select.Content>
                </Select.Root>
            </FormField>

            <FormField
                label="Predictions"
                description="Select one or more prediction collections to include in the next run."
            >
                <div class="min-h-24 rounded-md border border-input bg-background p-3">
                    <div class="flex flex-wrap gap-2">
                        {#each predictionCollections as collection}
                            <button
                                type="button"
                                class={`rounded-full border px-3 py-1 text-sm transition ${
                                    selectedPredictionNames.includes(collection.name)
                                        ? 'border-primary bg-primary text-primary-foreground'
                                        : 'border-border bg-background text-foreground'
                                }`}
                                onclick={() => togglePrediction(collection.name)}
                            >
                                {collection.name}
                            </button>
                        {/each}
                    </div>
                </div>
            </FormField>

            <FormField
                label="Subsets"
                description='Controls which tag-specific subsets are shown in the result table. "all" is always included.'
            >
                <div class="min-h-24 rounded-md border border-input bg-background p-3">
                    <div class="flex flex-wrap gap-2">
                        {#each $tags as tag}
                            <button
                                type="button"
                                class={`rounded-full border px-3 py-1 text-sm transition ${
                                    selectedTagIds.includes(tag.tag_id)
                                        ? 'border-primary bg-primary text-primary-foreground'
                                        : 'border-border bg-background text-foreground'
                                }`}
                                onclick={() => toggleTag(tag.tag_id)}
                            >
                                {tag.name}
                            </button>
                        {/each}
                    </div>
                </div>
            </FormField>

            <FormField label="IoU Threshold">
                <Input bind:value={iouThreshold} type="number" min="0" max="1" step="0.01" />
            </FormField>

            <FormField label="Confidence Threshold">
                <Input
                    bind:value={confidenceThreshold}
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                />
            </FormField>

            <FormField
                label="Past Runs"
                description="Pick a persisted result to inspect. The latest run is selected automatically."
            >
                <Select.Root type="single" bind:value={selectedEvaluationId}>
                    <Select.Trigger class="w-full">
                        {selectedEvaluation
                            ? formatEvaluationLabel(selectedEvaluation)
                            : 'Select a saved evaluation'}
                    </Select.Trigger>
                    <Select.Content>
                        {#each $evaluationsQuery.data ?? [] as evaluation}
                            <Select.Item
                                value={evaluation.id}
                                label={formatEvaluationLabel(evaluation)}
                            >
                                {formatEvaluationLabel(evaluation)}
                            </Select.Item>
                        {/each}
                    </Select.Content>
                </Select.Root>
            </FormField>
        </div>

        {#if $annotationCollectionsQuery.isLoading}
            <p class="mt-4 text-sm text-muted-foreground">Loading annotation collections…</p>
        {:else if !$annotationCollectionsQuery.isLoading && groundTruthCollections.length === 0 && predictionCollections.length === 0}
            <p class="mt-4 text-sm text-muted-foreground">
                No annotation collections found for this dataset. Run the modified prediction example first so it registers one ground-truth collection and one or more prediction collections.
            </p>
        {/if}
    </section>

    {#if $mutation.error}
        <Alert.Root variant="destructive">
            <Alert.Title>Evaluation failed</Alert.Title>
            <Alert.Description>{String($mutation.error)}</Alert.Description>
        </Alert.Root>
    {/if}

    <section class="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold">Results</h2>
                {#if selectedEvaluation}
                    <p class="text-sm text-muted-foreground">
                        Last computed {new Date(selectedEvaluation.created_at).toLocaleString()} ·
                        IoU {selectedEvaluation.iou_threshold} · confidence {selectedEvaluation.confidence_threshold}
                    </p>
                {/if}
            </div>

            <div class="flex flex-wrap items-center gap-3">
                <Button variant="outline" onclick={() => (mode = mode === 'models' ? 'subsets' : 'models')}>
                    <ArrowLeftRight class="mr-2 size-4" />
                    {mode === 'models' ? 'Model View' : 'Subset View'}
                </Button>

                {#if mode === 'models' && subsetNames.length > 0}
                    <Select.Root type="single" bind:value={selectedSubset}>
                        <Select.Trigger class="w-[220px]">
                            {selectedSubset}
                        </Select.Trigger>
                        <Select.Content>
                            {#each subsetNames as subsetName}
                                <Select.Item value={subsetName} label={subsetName}>
                                    {subsetName}
                                </Select.Item>
                            {/each}
                        </Select.Content>
                    </Select.Root>
                {/if}

                {#if mode === 'subsets' && modelNames.length > 0}
                    <Select.Root type="single" bind:value={selectedModel}>
                        <Select.Trigger class="w-[220px]">
                            {selectedModel || 'Select a model'}
                        </Select.Trigger>
                        <Select.Content>
                            {#each modelNames as modelName}
                                <Select.Item value={modelName} label={modelName}>
                                    {modelName}
                                </Select.Item>
                            {/each}
                        </Select.Content>
                    </Select.Root>
                {/if}
            </div>
        </div>

        {#if selectedEvaluation}
            <div class="overflow-x-auto">
                <table class="min-w-full border-collapse text-sm">
                    <thead>
                        <tr class="border-b border-border">
                            <th class="px-4 py-3 text-left font-medium text-muted-foreground">Metric</th>
                            {#if mode === 'models'}
                                {#each modelNames as modelName}
                                    <th class="px-4 py-3 text-left font-medium text-muted-foreground">
                                        {modelName}
                                    </th>
                                {/each}
                            {:else}
                                {#each subsetNames as subsetName}
                                    <th class="px-4 py-3 text-left font-medium text-muted-foreground">
                                        {subsetName}
                                    </th>
                                {/each}
                            {/if}
                            <th class="px-4 py-3 text-left font-medium text-muted-foreground">
                                Difference
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each metricRows as metric}
                            <tr class="border-b border-border/60 last:border-b-0">
                                <td class="px-4 py-3 font-medium">{metric.label}</td>
                                {#if mode === 'models'}
                                    {#each modelNames as modelName}
                                        <td class="px-4 py-3">
                                            {formatMetricValue(
                                                getMetricValue(
                                                    selectedEvaluation,
                                                    modelName,
                                                    selectedSubset,
                                                    metric.key
                                                )
                                            )}
                                        </td>
                                    {/each}
                                {:else}
                                    {#each subsetNames as subsetName}
                                        <td class="px-4 py-3">
                                            {formatMetricValue(
                                                getMetricValue(
                                                    selectedEvaluation,
                                                    selectedModel,
                                                    subsetName,
                                                    metric.key
                                                )
                                            )}
                                        </td>
                                    {/each}
                                {/if}
                                <td class="px-4 py-3 text-muted-foreground">
                                    {getDifference(metric.key)}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else}
            <div class="rounded-lg border border-dashed border-border p-8 text-sm text-muted-foreground">
                No evaluation selected yet. Compute a run or choose one from the saved results.
            </div>
        {/if}
    </section>
</div>
