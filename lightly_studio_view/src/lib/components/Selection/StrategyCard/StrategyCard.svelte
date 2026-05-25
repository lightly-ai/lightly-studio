<script lang="ts">
    import { ChevronDown, ChevronRight, Copy, Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import ClassBalancingForm from './ClassBalancingForm/ClassBalancingForm.svelte';
    import DiversityForm from './DiversityForm/DiversityForm.svelte';
    import MetadataWeightingForm from './MetadataWeightingForm/MetadataWeightingForm.svelte';
    import SimilarityForm from './SimilarityForm/SimilarityForm.svelte';
    import TypicalityForm from './TypicalityForm/TypicalityForm.svelte';
    import {
        STRATEGY_LABELS,
        getStrategyParameterSummary,
        type DiversityParams,
        type MetadataWeightingParams,
        type SimilarityParams,
        type StrategyInstance,
        type StrategyParams,
        type StrategySummaryTag,
        type TypicalityParams,
        type ClassBalancingParams
    } from '../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        instance: StrategyInstance;
        tags: StrategySummaryTag[];
        annotationLabels: string[];
        onRemove: () => void;
        onDuplicate: () => void;
        onUpdate: (params: Partial<StrategyParams>) => void;
        onToggleExpand: () => void;
    }

    let { instance, tags, annotationLabels, onRemove, onDuplicate, onUpdate, onToggleExpand }: Props = $props();

    const summary = $derived(getStrategyParameterSummary(instance, tags));
</script>

<div
    class="rounded-md border border-border bg-background p-3"
    data-testid={`strategy-card-${instance.id}`}
>
    <div class="flex items-start justify-between gap-3">
        <button
            type="button"
            class="flex min-w-0 flex-1 items-start gap-2 text-left"
            onclick={onToggleExpand}
            data-testid={`strategy-card-toggle-${instance.id}`}
        >
            {#if instance.isExpanded}
                <ChevronDown class="mt-0.5 size-4 shrink-0" />
            {:else}
                <ChevronRight class="mt-0.5 size-4 shrink-0" />
            {/if}

            <div class="min-w-0">
                <p class="truncate text-sm font-medium text-foreground">
                    {STRATEGY_LABELS[instance.type]}
                </p>
                {#if summary}
                    <p class="truncate text-sm text-muted-foreground">{summary}</p>
                {/if}
            </div>
        </button>

        <div class="flex shrink-0 gap-1">
            <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Duplicate strategy"
                onclick={onDuplicate}
                data-testid={`strategy-card-duplicate-${instance.id}`}
            >
                <Copy class="size-4" />
            </Button>
            <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Remove strategy"
                onclick={onRemove}
                data-testid={`strategy-card-remove-${instance.id}`}
            >
                <Trash2 class="size-4" />
            </Button>
        </div>
    </div>

    {#if instance.isExpanded}
        <div class="mt-3 border-t border-border pt-3">
            {#if instance.type === 'diversity'}
                <DiversityForm params={instance.params as DiversityParams} {onUpdate} />
            {:else if instance.type === 'typicality'}
                <TypicalityForm params={instance.params as TypicalityParams} {onUpdate} />
            {:else if instance.type === 'similarity'}
                <SimilarityForm params={instance.params as SimilarityParams} {tags} {onUpdate} />
            {:else if instance.type === 'metadata_weighting'}
                <MetadataWeightingForm
                    params={instance.params as MetadataWeightingParams}
                    {onUpdate}
                />
            {:else}
                <ClassBalancingForm
                    params={instance.params as ClassBalancingParams}
                    {annotationLabels}
                    {onUpdate}
                />
            {/if}
        </div>
    {/if}
</div>
