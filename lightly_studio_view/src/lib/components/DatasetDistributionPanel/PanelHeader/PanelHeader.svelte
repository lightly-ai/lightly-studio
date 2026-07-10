<script lang="ts">
    import {
        Maximize2 as Maximize2Icon,
        Settings as SettingsIcon,
        BarChart3 as BarChart3Icon,
        BarChartHorizontal as BarChartHorizontalIcon
    } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { DISTRIBUTION_SORT_LABELS, type DistributionConfig } from '../types';

    interface Props {
        /** Applied view config (top-N, sort order, orientation). */
        config: DistributionConfig;
        /** Total number of classes in the source. */
        classCount: number;
        /** Number of classes currently shown after top-N selection. */
        visibleClassCount: number;
        /** Sum of counts across all classes, for the summary line. */
        totalCount: number;
        /** Noun for the total count summary (e.g. 'annotations', 'samples'). */
        valueNoun?: string;
        /** Opens the view-config dialog (top-N and sort order). */
        onConfigure: () => void;
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
        valueNoun = 'annotations',
        onConfigure,
        onShowAll,
        onToggleOrientation,
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
