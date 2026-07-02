<script lang="ts">
    import { Maximize2 as Maximize2Icon, Settings as SettingsIcon } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { DISTRIBUTION_SORT_LABELS, type DistributionConfig } from '../types';

    interface Props {
        config: DistributionConfig;
        classCount: number;
        visibleClassCount: number;
        totalCount: number;
        onConfigure: () => void;
        /** Quick action showing all classes; rendered only while a subset is visible. */
        onShowAll?: () => void;
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
        onConfigure,
        onShowAll,
        onExpand,
        testIdPrefix = 'dataset-distribution'
    }: Props = $props();
</script>

<div class="mb-1 flex flex-row items-center gap-2">
    <div class="mb-2 flex-1 text-xs text-muted-foreground">
        {#if visibleClassCount < classCount}
            Top {visibleClassCount} of {classCount} classes
        {:else}
            {classCount}
            {classCount === 1 ? 'class' : 'classes'}
        {/if}
        · sorted by {DISTRIBUTION_SORT_LABELS[config.sortBy].toLowerCase()}
        · {totalCount.toLocaleString('en-US')} annotations
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
