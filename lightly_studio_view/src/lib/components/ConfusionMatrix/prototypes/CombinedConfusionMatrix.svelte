<script lang="ts">
    import { SlidersHorizontal as SlidersIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import ConfusionMatrix from '../ConfusionMatrix.svelte';
    import type { ConfusionMatrix as ConfusionMatrixData } from '../types';
    import ClassSetDialog from './ClassSetDialog.svelte';
    import {
        buildSubMatrix,
        CLASS_SORT_LABELS,
        getRealClasses,
        rankClasses,
        type ClassSetConfig,
        type ColorConfig
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

    let config: ClassSetConfig = $state({
        mode: 'topN',
        n: topN,
        sortBy: 'most-confused',
        manualClasses: []
    });
    let color: ColorConfig = $state({ intensity: 1, logScale: true });
    let configDialogOpen = $state(false);

    const realClasses = $derived(getRealClasses(matrix));
    const isLarge = $derived(realClasses.length > classCountThreshold);
    const baseClasses = $derived(
        config.mode === 'topN'
            ? rankClasses(matrix, config.sortBy).slice(0, config.n)
            : config.manualClasses
    );
    const visibleClasses = $derived(realClasses.filter((c) => baseClasses.includes(c)));
    const subMatrix = $derived(buildSubMatrix(matrix, visibleClasses));

    const applyConfig = (nextConfig: ClassSetConfig, nextColor: ColorConfig) => {
        config = nextConfig;
        color = nextColor;
    };
</script>

{#if !isLarge}
    <ConfusionMatrix {matrix} {showLegend} />
{:else}
    <!-- Row 1: controls -->
    <div class="mb-1 flex flex-row items-center gap-2">
        <!-- Row 2: explanation of the current view -->
        <div class="mb-2 flex-1 text-xs text-muted-foreground">
            {#if config.mode === 'topN'}
                Top {config.n} of {realClasses.length} classes · sorted by {CLASS_SORT_LABELS[
                    config.sortBy
                ].toLowerCase()}
            {:else}
                Manual selection · {visibleClasses.length} of {realClasses.length} classes
            {/if}
            {#if visibleClasses.length < realClasses.length}
                · rest aggregated as “(other)”
            {/if}
            {#if color.intensity !== 1 || !color.logScale}
                · {color.logScale ? 'log' : 'linear'} coloring at {color.intensity.toFixed(1)}×
            {/if}
        </div>
        <Button
            variant="ghost"
            icon={SlidersIcon}
            buttonProps={{
                size: 'sm',
                class: 'h-8 gap-1',
                onclick: () => (configDialogOpen = true),
                'data-testid': 'confusion-matrix-configure'
            }}
        >
            Configure
        </Button>
    </div>

    <ConfusionMatrix
        matrix={subMatrix}
        {showLegend}
        colorIntensity={color.intensity}
        logScale={color.logScale}
    />
    <ClassSetDialog
        bind:open={configDialogOpen}
        allClasses={realClasses}
        {config}
        {color}
        onApply={applyConfig}
    />
{/if}
