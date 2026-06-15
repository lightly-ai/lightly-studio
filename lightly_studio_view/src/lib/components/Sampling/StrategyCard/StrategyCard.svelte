<script lang="ts">
    import { ChevronDown, ChevronRight, Copy, Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import {
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger
    } from '$lib/components/ui/collapsible';

    import {
        STRATEGY_LABELS,
        type MetadataWeightingParams,
        type SimilarityParams,
        type StrategyInstance,
        type StrategyParams,
        type StrategySummaryTag,
        type ClassBalancingParams
    } from '$lib/hooks/useStrategyBuilder';
    import MetadataWeightingForm from '../forms/MetadataWeightingForm/MetadataWeightingForm.svelte';
    import SimilarityForm from '../forms/SimilarityForm/SimilarityForm.svelte';
    import ClassBalancingForm from '../forms/ClassBalancingForm/ClassBalancingForm.svelte';
    import StrengthField from '../forms/StrengthField/StrengthField.svelte';
    import Typography from '$lib/components/Typography/Typography.svelte';
    interface Props {
        instance: StrategyInstance;
        tags: StrategySummaryTag[];
        annotationLabels: string[];
        annotationSourceOptions?: { id: string; name: string }[];
        metadataFieldNames?: string[];
        isDuplicateDisabled?: boolean;
        onRemove: () => void;
        onDuplicate: () => void;
        onUpdate: (params: Partial<StrategyParams>) => void;
        onToggleExpand: () => void;
    }
    let {
        instance,
        tags,
        annotationLabels,
        annotationSourceOptions = [],
        metadataFieldNames = [],
        isDuplicateDisabled = false,
        onRemove,
        onDuplicate,
        onUpdate,
        onToggleExpand
    }: Props = $props();
</script>

<div
    class="rounded-md border border-border bg-background p-3"
    data-testid={`strategy-card-${instance.id}`}
>
    <Collapsible open={instance.isExpanded} onOpenChange={() => onToggleExpand()}>
        <div class="flex items-center justify-between gap-3">
            <CollapsibleTrigger
                class="flex min-w-0 flex-1 items-center gap-2 text-left"
                data-testid={`strategy-card-toggle-${instance.id}`}
            >
                {#if instance.isExpanded}
                    <ChevronDown class="size-4 shrink-0" />
                {:else}
                    <ChevronRight class="size-4 shrink-0" />
                {/if}

                <div class="min-w-0">
                    <Typography
                        variant="subtitle2"
                        component="span"
                        className="block truncate text-foreground"
                    >
                        {STRATEGY_LABELS[instance.type]}
                    </Typography>
                </div>
            </CollapsibleTrigger>

            <div class="flex shrink-0 gap-1">
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Duplicate strategy"
                    onclick={onDuplicate}
                    disabled={isDuplicateDisabled}
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

        <CollapsibleContent forceMount>
            {#if instance.isExpanded}
                <div class="mt-3 border-t border-border pt-3">
                    {#if instance.type === 'diversity'}
                        <StrengthField
                            strength={instance.params.strength}
                            id={`diversity-strength-${instance.id}`}
                            testid={`strategy-diversity-strength-input-${instance.id}`}
                            min={0}
                            onUpdate={(strength) => onUpdate({ strength })}
                        />
                    {:else if instance.type === 'typicality'}
                        <StrengthField
                            strength={instance.params.strength}
                            id={`typicality-strength-${instance.id}`}
                            testid={`strategy-typicality-strength-input-${instance.id}`}
                            onUpdate={(strength) => onUpdate({ strength })}
                        />
                    {:else if instance.type === 'similarity'}
                        <SimilarityForm
                            params={instance.params as SimilarityParams}
                            {tags}
                            {onUpdate}
                        />
                    {:else if instance.type === 'metadata_weighting'}
                        <MetadataWeightingForm
                            params={instance.params as MetadataWeightingParams}
                            {metadataFieldNames}
                            {onUpdate}
                        />
                    {:else}
                        <ClassBalancingForm
                            instanceId={instance.id}
                            params={instance.params as ClassBalancingParams}
                            {annotationLabels}
                            {annotationSourceOptions}
                            {onUpdate}
                        />
                    {/if}
                </div>
            {/if}
        </CollapsibleContent>
    </Collapsible>
</div>
