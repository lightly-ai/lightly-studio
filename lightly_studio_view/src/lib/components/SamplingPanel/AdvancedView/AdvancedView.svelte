<script lang="ts">
    import AddStrategyButton from '$lib/components/Sampling/AddStrategyButton.svelte';
    import StrategyCard from '$lib/components/Sampling/StrategyCard/StrategyCard.svelte';
    import type { useStrategyOptions } from '$lib/components/Sampling/useSamplingCombinationDialog/useStrategyOptions.svelte';
    import type {
        StrategyInstance,
        StrategyParams,
        StrategyType
    } from '$lib/hooks/useStrategyBuilder';
    import type { TagView } from '$lib/services/types';
    import MixBar from '../MixBar/MixBar.svelte';

    interface Props {
        instances: StrategyInstance[];
        tags: TagView[];
        strategyOptions: ReturnType<typeof useStrategyOptions>;
        onAdd: (type: StrategyType) => void;
        onRemove: (id: string) => void;
        onDuplicate: (id: string) => void;
        onUpdate: (id: string, params: Partial<StrategyParams>) => void;
        onToggleExpand: (id: string) => void;
    }

    let {
        instances,
        tags,
        strategyOptions,
        onAdd,
        onRemove,
        onDuplicate,
        onUpdate,
        onToggleExpand
    }: Props = $props();

    const SINGLE_USE_TYPES: StrategyType[] = ['diversity', 'deduplication', 'subpart_diversity'];
</script>

<div class="grid gap-3" data-testid="sampling-advanced-view">
    {#if instances.length > 0}
        <MixBar {instances} />
    {:else}
        <p class="text-xs text-muted-foreground">
            No strategies yet. Add one to describe what to sample for.
        </p>
    {/if}

    {#each instances as instance (instance.id)}
        <StrategyCard
            {instance}
            {tags}
            annotationLabels={strategyOptions.annotationLabels}
            annotationSourceOptions={strategyOptions.annotationSourceOptions}
            croppableAnnotationSourceOptions={strategyOptions.croppableAnnotationSourceOptions}
            metadataFieldNames={strategyOptions.metadataFieldNames}
            categoricalMetadataFieldNames={strategyOptions.categoricalMetadataFieldNames}
            metadataValuesByKey={strategyOptions.metadataValuesByKey}
            isDuplicateDisabled={SINGLE_USE_TYPES.includes(instance.type)}
            onRemove={() => onRemove(instance.id)}
            onDuplicate={() => onDuplicate(instance.id)}
            onUpdate={(params) => onUpdate(instance.id, params)}
            onToggleExpand={() => onToggleExpand(instance.id)}
        />
    {/each}

    <AddStrategyButton onAdd={(type) => onAdd(type)} />
</div>
