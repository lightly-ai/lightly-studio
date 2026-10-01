<script lang="ts">
    import { Maximize2 as Maximize2Icon, Settings as SettingsIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { CLASS_SORT_LABELS } from '../../topNMatrix';
    import type { ClassSetConfig, ColorConfig } from '../../ClassSetDialog/types';

    interface Props {
        /** Active class-set view (top-N vs manual, sort order). */
        config: ClassSetConfig;
        /** Cell coloring settings (log/linear scale and intensity). */
        color: ColorConfig;
        /** Total number of classes in the matrix. */
        realClassCount: number;
        /** Number of classes currently shown (rest aggregated as "(other)"). */
        visibleClassCount: number;
        /** Opens the class-filter and color configuration dialog. */
        onConfigure: () => void;
        /** Opens the expanded (full-screen) matrix view. */
        onExpand: () => void;
    }

    let { config, color, realClassCount, visibleClassCount, onConfigure, onExpand }: Props =
        $props();
</script>

<div class="mb-1 flex flex-row items-center gap-2">
    <div class="mb-2 flex-1 text-xs text-muted-foreground">
        {#if config.mode === 'topN'}
            {#if config.n < realClassCount}
                Top {config.n} of {realClassCount} classes
            {:else}
                {realClassCount}
                {realClassCount === 1 ? 'class' : 'classes'}
            {/if}
            · sorted by {CLASS_SORT_LABELS[config.sortBy].toLowerCase()}
        {:else}
            Manual selection · {visibleClassCount} of {realClassCount} classes
        {/if}
        {#if visibleClassCount < realClassCount}
            · rest aggregated as “(other)”
        {/if}
        {#if color.intensity !== 1 || !color.logScale}
            · {color.logScale ? 'log' : 'linear'} coloring at {color.intensity.toFixed(1)}×
        {/if}
    </div>
    <Button
        variant="ghost"
        icon={SettingsIcon}
        ariaLabel="Configure class filters and colors"
        buttonProps={{
            size: 'sm',
            class: 'h-8 gap-1',
            onclick: onConfigure,
            'data-testid': 'confusion-matrix-configure'
        }}
    />
    <Button
        variant="ghost"
        icon={Maximize2Icon}
        ariaLabel="Expand confusion matrix"
        buttonProps={{
            size: 'sm',
            class: 'h-8 w-8 p-0',
            onclick: onExpand,
            'data-testid': 'confusion-matrix-expand'
        }}
    />
</div>
