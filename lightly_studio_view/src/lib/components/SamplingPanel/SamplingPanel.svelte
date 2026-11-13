<script lang="ts">
    import { untrack } from 'svelte';
    import { ArrowLeft, ArrowRight, X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { useStrategyOptions } from '$lib/components/Sampling/useSamplingCombinationDialog/useStrategyOptions.svelte';
    import { useTags } from '$lib/hooks';
    import { useClearAllFilters } from '$lib/components/ClearAllFiltersButton/useClearAllFilters';
    import {
        cloneStrategyParams,
        createStrategyInstance,
        generateStrategyInstanceId,
        type StrategyInstance,
        type StrategyParams,
        type StrategyType
    } from '$lib/hooks/useStrategyBuilder';
    import AdvancedView from './AdvancedView/AdvancedView.svelte';
    import GoalGrid from './GoalGrid/GoalGrid.svelte';
    import GoalInput from './GoalInput/GoalInput.svelte';
    import {
        buildGoalInstances,
        getGoal,
        withGoalInput,
        type GoalInputKind,
        type SamplingGoalId
    } from './samplingGoals';
    import { useSamplingPreview } from './useSamplingPreview/useSamplingPreview';

    interface Props {
        collectionId: string;
        sampleCount: number;
        totalSampleCount: number;
        onClose: () => void;
    }

    let { collectionId, sampleCount, totalSampleCount, onClose }: Props = $props();

    const strategyOptions = useStrategyOptions(() => collectionId);
    const { tags, loadTags, setTagSelected } = useTags({
        collection_id: untrack(() => collectionId)
    });
    const { draftSampleIds, isRunning, isKeeping, runPreview, keepAsTag, discardDraft } =
        useSamplingPreview();

    let isAdvanced = $state(false);
    let goalId = $state<SamplingGoalId>('varied');
    let goalInputValue = $state<string | undefined>(undefined);
    let instances = $state<StrategyInstance[]>(buildGoalInstances('varied', undefined));
    let nSamples = $state(untrack(() => Math.min(200, sampleCount)));
    let tagName = $state('');

    // A draft filters the grid to its own picks, so the candidate count is frozen while
    // it is open. Sampling again still runs over the same candidates.
    let inputSampleCount = $state(untrack(() => sampleCount));
    $effect(() => {
        if (!$draftSampleIds) inputSampleCount = sampleCount;
    });

    const unavailableReasons = $derived({
        similar: $tags.length === 0 ? 'Create a sample tag with examples first.' : undefined,
        balance: !strategyOptions.hasAnnotationLabels
            ? 'Add annotations to your samples first.'
            : undefined,
        balance_metadata: !strategyOptions.hasCategoricalMetadataFields
            ? 'Index a text or boolean metadata field first.'
            : undefined
    });

    const { hasActiveFilters, clearAllFilters } = useClearAllFilters({
        collectionId: untrack(() => collectionId),
        isImages: true,
        isVideos: false,
        isVideoFrames: false
    });
    const candidateCount = $derived(inputSampleCount);

    const inputKind = $derived(getGoal(goalId).requires as GoalInputKind | undefined);
    const isGoalInputMissing = $derived(!isAdvanced && !!inputKind && !goalInputValue);
    const canPreview = $derived(
        instances.length > 0 && nSamples >= 1 && nSamples <= candidateCount && !isGoalInputMissing
    );

    /** The only option, when a goal's input has exactly one, so nobody has to pick it. */
    function onlyOption(kind: GoalInputKind | undefined): string | undefined {
        const options =
            kind === 'tag'
                ? $tags.map((tag) => tag.tag_id)
                : kind === 'annotation_source'
                  ? strategyOptions.annotationSourceOptions.map((source) => source.id)
                  : kind === 'metadata_field'
                    ? strategyOptions.categoricalMetadataFieldNames
                    : [];
        return options.length === 1 ? options[0] : undefined;
    }

    function selectGoal(nextGoalId: SamplingGoalId) {
        goalId = nextGoalId;
        goalInputValue = onlyOption(getGoal(nextGoalId).requires as GoalInputKind | undefined);
        instances = buildGoalInstances(nextGoalId, goalInputValue);
    }

    function setGoalInput(value: string | undefined) {
        goalInputValue = value;
        instances = instances.map((instance) => withGoalInput(instance, value));
    }

    function updateParams(id: string, params: Partial<StrategyParams>) {
        instances = instances.map((instance) =>
            instance.id === id
                ? ({ ...instance, params: { ...instance.params, ...params } } as StrategyInstance)
                : instance
        );
    }

    function duplicateStrategy(id: string) {
        const source = instances.find((instance) => instance.id === id);
        if (!source) return;
        instances = [
            ...instances,
            {
                ...source,
                id: generateStrategyInstanceId(),
                params: cloneStrategyParams(source.type, source.params)
            } as StrategyInstance
        ];
    }

    function addStrategy(type: StrategyType) {
        instances = [...instances, withGoalInput(createStrategyInstance(type), goalInputValue)];
    }
</script>

<div class="flex h-full w-96 flex-col gap-4 overflow-y-auto p-4" data-testid="sampling-panel">
    <div class="flex items-center justify-between">
        <h2 class="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            {#if isAdvanced}
                <button
                    type="button"
                    aria-label="Back to goals"
                    class="text-muted-foreground hover:text-foreground"
                    onclick={() => (isAdvanced = false)}
                >
                    <ArrowLeft class="size-4" />
                </button>
                Sample · advanced
            {:else}
                Sample
            {/if}
        </h2>
        <Button variant="ghost" icon={X} ariaLabel="Close" buttonProps={{ onclick: onClose }} />
    </div>

    <div class="grid gap-1 rounded-md bg-muted/40 px-3 py-2" data-testid="sampling-panel-scope">
        <span class="text-xs text-foreground">
            Sampling from
            <strong class="font-medium">
                {candidateCount.toLocaleString()}
                {candidateCount === 1 ? 'image' : 'images'}
            </strong>
            {#if $hasActiveFilters}
                · what your filters match
            {:else}
                · the whole collection
            {/if}
        </span>
        {#if $hasActiveFilters}
            <button
                type="button"
                class="justify-self-start text-xs text-primary underline-offset-4 hover:underline"
                data-testid="sampling-panel-scope-clear"
                onclick={clearAllFilters}
            >
                Clear the filters to use all {totalSampleCount.toLocaleString()}
            </button>
        {/if}
    </div>

    {#if isAdvanced}
        <AdvancedView
            {instances}
            tags={$tags}
            {strategyOptions}
            onAdd={addStrategy}
            onRemove={(id) => (instances = instances.filter((instance) => instance.id !== id))}
            onDuplicate={duplicateStrategy}
            onUpdate={updateParams}
            onToggleExpand={(id) =>
                (instances = instances.map((instance) =>
                    instance.id === id
                        ? { ...instance, isExpanded: !instance.isExpanded }
                        : instance
                ))}
        />
    {:else}
        <GoalGrid selectedGoalId={goalId} {unavailableReasons} onSelect={selectGoal} />
        {#if inputKind}
            <GoalInput
                kind={inputKind}
                tags={$tags}
                annotationSources={strategyOptions.annotationSourceOptions}
                metadataFieldNames={strategyOptions.categoricalMetadataFieldNames}
                value={goalInputValue}
                onValueChange={setGoalInput}
            />
        {/if}
    {/if}

    <div class="grid gap-2">
        <Label for="sampling-panel-count">How many samples</Label>
        <Input
            id="sampling-panel-count"
            type="number"
            min="1"
            max={candidateCount}
            bind:value={nSamples}
        />
        {#if nSamples > candidateCount}
            <span class="text-xs text-destructive-text">
                Only {candidateCount.toLocaleString()} samples to choose from.
            </span>
        {/if}
    </div>

    {#if !isAdvanced}
        <button
            type="button"
            class="flex items-center gap-1 text-left text-xs text-primary underline-offset-4 hover:underline"
            data-testid="sampling-panel-advanced"
            onclick={() => (isAdvanced = true)}
        >
            Advanced <ArrowRight class="size-3" />
        </button>
    {/if}

    <div class="mt-auto grid gap-2 border-t border-border pt-4">
        {#if $draftSampleIds}
            <p class="text-xs text-foreground" data-testid="sampling-panel-draft-count">
                Showing {$draftSampleIds.length.toLocaleString()} picked samples in the grid.
            </p>
            <Input placeholder="Name for the new tag" bind:value={tagName} />
            <div class="flex gap-2">
                <Button
                    variant="default"
                    isPending={$isKeeping}
                    buttonProps={{
                        disabled: !tagName.trim(),
                        onclick: () =>
                            keepAsTag(collectionId, tagName.trim(), async (tagId) => {
                                await loadTags();
                                setTagSelected(tagId, true);
                                tagName = '';
                            }),
                        'data-testid': 'sampling-panel-keep'
                    }}
                >
                    Keep as tag
                </Button>
                <Button variant="outline" buttonProps={{ onclick: discardDraft }}>Discard</Button>
            </div>
        {/if}
        <Button
            variant={$draftSampleIds ? 'outline' : 'default'}
            isPending={$isRunning}
            disabledReason={isGoalInputMissing ? 'Answer the question above first.' : undefined}
            buttonProps={{
                disabled: !canPreview,
                onclick: () => runPreview({ collectionId, instances, nSamplesToSelect: nSamples }),
                'data-testid': 'sampling-panel-preview'
            }}
        >
            {$draftSampleIds ? 'Preview again' : 'Preview'}
        </Button>
    </div>
</div>
