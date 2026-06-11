<script lang="ts">
    import { Palette as PaletteIcon, Plus as PlusIcon } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import ConfusionMatrix from '../ConfusionMatrix.svelte';
    import type { ConfusionMatrix as ConfusionMatrixData } from '../types';
    import AddClassDialog from './AddClassDialog.svelte';
    import ClassFilterInput from './ClassFilterInput.svelte';
    import {
        buildSubMatrix,
        filterClasses,
        getRealClasses,
        rankClassesByConfusion
    } from './topNMatrix';

    interface Props {
        matrix: ConfusionMatrixData;
        /** Number of most-confused classes shown by default. */
        topN?: number;
        /** Below this class count the full matrix is shown unchanged. */
        classCountThreshold?: number;
        showLegend?: boolean;
    }

    const { matrix, topN = 5, classCountThreshold = 30, showLegend = false }: Props = $props();

    let showAll = $state(false);
    let hiddenClasses: string[] = $state([]);
    let addedClasses: string[] = $state([]);
    let addDialogOpen = $state(false);
    let query = $state('');
    let colorIntensity = $state(1);

    const realClasses = $derived(getRealClasses(matrix));
    const isLarge = $derived(realClasses.length > classCountThreshold);
    const matchingClasses = $derived(filterClasses(realClasses, query));
    // The filter takes over only when it actually narrows the class set.
    const isFiltering = $derived(
        query.trim().length > 0 && matchingClasses.length < realClasses.length
    );
    const baseClasses = $derived(
        isFiltering
            ? matchingClasses
            : showAll
              ? realClasses
              : rankClassesByConfusion(matrix).slice(0, topN)
    );
    const visibleClasses = $derived(
        realClasses.filter(
            (c) =>
                (baseClasses.includes(c) || (!isFiltering && addedClasses.includes(c))) &&
                !hiddenClasses.includes(c)
        )
    );
    const addableClasses = $derived(realClasses.filter((c) => !visibleClasses.includes(c)));
    const subMatrix = $derived(buildSubMatrix(matrix, visibleClasses));

    const hideClass = (className: string) => {
        hiddenClasses = [...hiddenClasses, className];
    };

    const addClass = (className: string) => {
        hiddenClasses = hiddenClasses.filter((c) => c !== className);
        if (!addedClasses.includes(className)) addedClasses = [...addedClasses, className];
    };
</script>

{#if !isLarge}
    <ConfusionMatrix {matrix} {showLegend} />
{:else}
    <!-- Row 1: controls -->
    <div class="mb-1 flex items-center gap-2">
        <Button
            variant="outline"
            size="sm"
            class="h-8 gap-1"
            disabled={isFiltering || addableClasses.length === 0}
            onclick={() => (addDialogOpen = true)}
            data-testid="confusion-matrix-add-class"
        >
            <PlusIcon class="size-3.5" />
            Add class
        </Button>
        <ClassFilterInput classes={realClasses} bind:query />
        <div class="ml-auto flex shrink-0 items-center gap-1">
            <Popover.Root>
                <Popover.Trigger>
                    {#snippet child({ props }: { props: Record<string, unknown> })}
                        <Button
                            {...props}
                            variant="ghost"
                            size="sm"
                            class="h-8 w-8 p-0"
                            aria-label="Adjust color intensity"
                            data-testid="confusion-matrix-color-settings"
                        >
                            <PaletteIcon class="size-4" />
                        </Button>
                    {/snippet}
                </Popover.Trigger>
                <Popover.Content class="w-60" align="end">
                    <div class="mb-2 flex items-center justify-between">
                        <span class="text-xs font-medium">Color intensity</span>
                        <span class="text-xs tabular-nums text-muted-foreground">
                            {colorIntensity.toFixed(1)}×
                        </span>
                    </div>
                    <Slider
                        type="single"
                        bind:value={colorIntensity}
                        min={0.2}
                        max={3}
                        step={0.1}
                        data-testid="color-intensity-slider"
                    />
                    <div class="mt-2 flex items-center justify-between">
                        <span class="text-xs text-muted-foreground">paler · more intense</span>
                        {#if colorIntensity !== 1}
                            <Button
                                variant="ghost"
                                size="sm"
                                class="h-6 px-2 text-xs"
                                onclick={() => (colorIntensity = 1)}
                            >
                                Reset
                            </Button>
                        {/if}
                    </div>
                </Popover.Content>
            </Popover.Root>
            {#if hiddenClasses.length > 0}
                <Button variant="ghost" size="sm" onclick={() => (hiddenClasses = [])}>
                    Restore hidden
                </Button>
            {/if}
            <Button
                variant="outline"
                size="sm"
                disabled={isFiltering}
                onclick={() => (showAll = !showAll)}
                data-testid="confusion-matrix-show-all"
            >
                {showAll ? `Show top ${topN}` : 'Show all'}
            </Button>
        </div>
    </div>
    <!-- Row 2: explanation of the current view -->
    <div class="mb-2 text-xs text-muted-foreground">
        {#if isFiltering}
            Filter matches {visibleClasses.length} of {realClasses.length} classes
        {:else if showAll}
            Showing {visibleClasses.length} of {realClasses.length} classes
        {:else if addedClasses.length > 0 || hiddenClasses.length > 0}
            Showing {visibleClasses.length} of {realClasses.length} classes (top {topN} adjusted)
        {:else}
            Top {topN} most-confused of {realClasses.length} classes
        {/if}
        {#if hiddenClasses.length > 0}
            · {hiddenClasses.length} hidden
        {/if}
        {#if visibleClasses.length < realClasses.length}
            · rest aggregated as “(other)” · click ✕ on a row label to hide a class
        {/if}
    </div>
    <ConfusionMatrix
        matrix={subMatrix}
        {showLegend}
        removableLabels={visibleClasses}
        onLabelRemove={hideClass}
        {colorIntensity}
    />
    <AddClassDialog bind:open={addDialogOpen} classes={addableClasses} onAdd={addClass} />
{/if}
