<script lang="ts">
    import {
        Maximize2 as Maximize2Icon,
        Settings as SettingsIcon,
        BarChart3 as BarChart3Icon,
        BarChartHorizontal as BarChartHorizontalIcon
    } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { DISTRIBUTION_SORT_LABELS, type DistributionConfig } from '../types';
    import { ValueModeSelect, type ValueMode } from './ValueModeSelect';

    interface Props {
        /** Applied view config (top-N, sort order, orientation). */
        config: DistributionConfig;
        /** Total number of classes in the source. */
        classCount: number;
        /** Number of classes currently shown after top-N selection. */
        visibleClassCount: number;
        /** Sum of counts across all classes, for the summary line. Omit to hide the count. */
        totalCount?: number;
        /** Number of compared sample-tag series; shown instead of a combined count. */
        seriesCount?: number;
        /** Noun for the total count summary (e.g. 'annotations', 'samples'). */
        valueNoun?: string;
        /** Singular/plural labels for the distributed categories. */
        categoryNoun?: string;
        categoryNounPlural?: string;
        /** Labels for the active sort mode. */
        sortLabels?: Record<keyof typeof DISTRIBUTION_SORT_LABELS, string>;
        /** Opens the view-config dialog (top-N and sort order). */
        onConfigure: () => void;
        /** Current value mode shown in the selector (default 'number'). */
        valueMode?: ValueMode;
        /** Switches the chart between raw counts and percentage distributions. */
        onValueModeChange?: (mode: ValueMode) => void;
        /** Quick action showing all classes; rendered only while a subset is visible. */
        onShowAll?: () => void;
        /** Toggles between vertical and horizontal bar layouts. */
        onToggleOrientation?: () => void;
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
        seriesCount,
        valueNoun = 'annotations',
        categoryNoun = 'class',
        categoryNounPlural = 'classes',
        sortLabels = DISTRIBUTION_SORT_LABELS,
        onConfigure,
        valueMode = 'number',
        onValueModeChange,
        onShowAll,
        onToggleOrientation,
        onExpand,
        testIdPrefix = 'dataset-distribution'
    }: Props = $props();
</script>

<div class="flex flex-row items-center gap-2">
    <div class="flex-1 text-xs text-muted-foreground">
        {#if visibleClassCount < classCount}
            {config.mode === 'manual' ? 'Showing' : 'Top'}
            {visibleClassCount} of {classCount}
            {categoryNounPlural}
        {:else}
            {classCount}
            {classCount === 1 ? categoryNoun : categoryNounPlural}
        {/if}
        · sorted by {sortLabels[config.sortBy].toLowerCase()}
        {#if totalCount !== undefined}
            · {totalCount.toLocaleString('en-US')}
            {valueNoun}
        {/if}
        {#if seriesCount !== undefined}
            · {seriesCount} sample {seriesCount === 1 ? 'tag' : 'tags'}
        {/if}
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
    {#if onValueModeChange}
        <ValueModeSelect
            value={valueMode}
            testId={`${testIdPrefix}-value-mode`}
            onChange={onValueModeChange}
        />
    {/if}
    <Button
        variant="ghost"
        icon={SettingsIcon}
        ariaLabel="Configure distribution {categoryNounPlural}"
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
            ariaLabel="Expand distribution"
            buttonProps={{
                size: 'sm',
                class: 'h-8 w-8 p-0',
                onclick: onExpand,
                'data-testid': `${testIdPrefix}-expand`
            }}
        />
    {/if}
</div>
