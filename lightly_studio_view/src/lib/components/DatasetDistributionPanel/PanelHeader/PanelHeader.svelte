<script lang="ts">
    import {
        Maximize2 as Maximize2Icon,
        Settings as SettingsIcon,
        BarChart3 as BarChart3Icon,
        BarChartHorizontal as BarChartHorizontalIcon,
        Percent as PercentIcon,
        Hash as HashIcon,
        ChartNoAxesColumn as LinearScaleIcon,
        ChartNoAxesColumnDecreasing as LogScaleIcon
    } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { DISTRIBUTION_SORT_LABELS, type DistributionConfig } from '../types';

    interface Props {
        config: DistributionConfig;
        classCount: number;
        visibleClassCount: number;
        totalCount: number;
        /** Noun for the total count summary (e.g. 'annotations', 'samples'). */
        valueNoun?: string;
        onConfigure: () => void;
        /** Quick action showing all classes; rendered only while a subset is visible. */
        onShowAll?: () => void;
        /** Toggles between vertical and horizontal bar layouts. */
        onToggleOrientation?: () => void;
        /** Toggles counts vs percentages; rendered only when provided (metadata sources). */
        onToggleNormalize?: () => void;
        /** Toggles the value axis between linear and log scale. */
        onToggleScale?: () => void;
        /** Renders the expand button only when provided (omit inside the expanded view). */
        onExpand?: () => void;
        /** Prefix for button test ids, to disambiguate panel vs. expanded view. */
        testIdPrefix?: string;
    }

    let {
        config,
        classCount,
        visibleClassCount,
        totalCount,
        valueNoun = 'annotations',
        onConfigure,
        onShowAll,
        onToggleOrientation,
        onToggleNormalize,
        onToggleScale,
        onExpand,
        testIdPrefix = 'dataset-distribution'
    }: Props = $props();
</script>

<div class="mb-1 flex flex-row items-center gap-2">
    <div class="mb-2 flex-1 text-xs text-muted-foreground">
        {#if visibleClassCount < classCount}
            {config.mode === 'manual' ? 'Showing' : 'Top'}
            {visibleClassCount} of {classCount} classes
        {:else}
            {classCount}
            {classCount === 1 ? 'class' : 'classes'}
        {/if}
        · sorted by {DISTRIBUTION_SORT_LABELS[config.sortBy].toLowerCase()}
        · {totalCount.toLocaleString('en-US')}
        {valueNoun}
        {#if onShowAll && visibleClassCount < classCount}
            ·
            <button
                type="button"
                class="text-primary underline-offset-2 hover:underline"
                onclick={onShowAll}
                data-testid={`${testIdPrefix}-show-all`}
            >
                Show all
            </button>
        {/if}
    </div>
    {#if onToggleNormalize}
        <Button
            variant="ghost"
            icon={config.normalize === 'percentage' ? HashIcon : PercentIcon}
            ariaLabel={config.normalize === 'percentage' ? 'Show counts' : 'Show percentages'}
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onToggleNormalize,
                'data-testid': `${testIdPrefix}-toggle-normalize`
            }}
        />
    {/if}
    {#if onToggleScale}
        <Button
            variant="ghost"
            icon={config.scale === 'log' ? LogScaleIcon : LinearScaleIcon}
            ariaLabel={config.scale === 'log' ? 'Switch to linear scale' : 'Switch to log scale'}
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onToggleScale,
                title: config.scale === 'log' ? 'Log scale' : 'Linear scale',
                'data-testid': `${testIdPrefix}-toggle-scale`
            }}
        />
    {/if}
    {#if onToggleOrientation}
        <Button
            variant="ghost"
            icon={config.orientation === 'horizontal' ? BarChart3Icon : BarChartHorizontalIcon}
            ariaLabel={config.orientation === 'horizontal'
                ? 'Switch to vertical bars'
                : 'Switch to horizontal bars'}
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onToggleOrientation,
                'data-testid': `${testIdPrefix}-toggle-orientation`
            }}
        />
    {/if}
    <Button
        variant="ghost"
        icon={SettingsIcon}
        ariaLabel="Configure distribution classes"
        buttonProps={{
            size: 'sm',
            class: 'h-8 gap-1',
            onclick: onConfigure,
            'data-testid': `${testIdPrefix}-configure`
        }}
    />
    {#if onExpand}
        <Button
            variant="ghost"
            icon={Maximize2Icon}
            ariaLabel="Expand class distribution"
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onExpand,
                'data-testid': `${testIdPrefix}-expand`
            }}
        />
    {/if}
</div>
