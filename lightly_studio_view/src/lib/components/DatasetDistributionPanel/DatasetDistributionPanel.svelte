<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { Select, type SelectItem } from '$lib/components/Select';
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from './selectVisibleCounts';
    import type { DistributionConfig, DistributionSource } from './types';

    interface Props {
        /**
         * Counts for the default (class) source. Ignored when `sources` is
         * provided. Ranking and top-N selection are user-configurable.
         */
        data?: CategoryCount[];
        /**
         * Multiple selectable sources (class labels, tags, metadata keys,
         * eval …). When provided, a source selector is shown in the header and
         * `data` is ignored. The same bar-chart UI renders every source.
         */
        sources?: DistributionSource[];
        title?: string;
        /** Top classes shown by default. */
        topN?: number;
        /** Renders a close button in the header when provided. */
        onClose?: () => void;
        /** Called with the clicked class. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const {
        data,
        sources,
        title = 'Class distribution',
        topN = 20,
        onClose,
        onBarClick
    }: Props = $props();

    // Normalise to a source list so the rest of the panel has one code path.
    const resolvedSources = $derived<DistributionSource[]>(
        sources ?? [{ id: 'class', label: 'Class labels', data: data ?? [] }]
    );
    const hasSourceSelector = $derived(resolvedSources.length > 1);

    let selectedSourceId = $state<string | undefined>(undefined);
    let selectedGroupId = $state<string | undefined>(undefined);

    const activeSource = $derived(
        resolvedSources.find((source) => source.id === selectedSourceId) ?? resolvedSources[0]
    );
    const activeGroup = $derived(
        activeSource.groups?.find((group) => group.id === selectedGroupId) ??
            activeSource.groups?.[0]
    );
    const activeData = $derived<CategoryCount[]>(activeGroup?.data ?? activeSource.data ?? []);
    const valueNoun = $derived(activeSource.valueNoun ?? 'annotations');

    const sourceItems = $derived<SelectItem[]>(
        resolvedSources.map((source) => ({ value: source.id, label: source.label }))
    );
    const groupItems = $derived<SelectItem[]>(
        (activeSource.groups ?? []).map((group) => ({ value: group.id, label: group.label }))
    );

    let config: DistributionConfig = $state({ n: topN, sortBy: 'count', orientation: 'vertical' });
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);

    const visible = $derived(selectVisibleCounts(activeData, config));
    const totalCount = $derived(activeData.reduce((sum, item) => sum + item.count, 0));
</script>

<div
    class="flex h-full min-w-0 flex-1 flex-col rounded-[1vw] bg-card p-4"
    data-testid="dataset-distribution-panel"
>
    <div class="flex items-center justify-between">
        <Typography variant="h5" component="h2" className="text-foreground">
            {title}
        </Typography>
        {#if onClose}
            <Button
                variant="ghost"
                icon={X}
                ariaLabel="Close class distribution panel"
                buttonProps={{
                    size: 'sm',
                    class: 'h-8 w-8 p-0',
                    onclick: onClose,
                    'data-testid': 'dataset-distribution-close-button'
                }}
            />
        {/if}
    </div>
    {#if hasSourceSelector}
        <div
            class="mt-2 flex flex-wrap items-center gap-2"
            data-testid="dataset-distribution-source"
        >
            <span class="text-xs text-muted-foreground">Source</span>
            <Select
                items={sourceItems}
                value={activeSource.id}
                size="xs"
                class="w-40"
                testId="dataset-distribution-source-select"
                onValueChange={(value) => {
                    selectedSourceId = value;
                    selectedGroupId = undefined;
                }}
            />
            {#if groupItems.length > 0}
                <span class="text-xs text-muted-foreground"
                    >{activeSource.groupLabel ?? 'Field'}</span
                >
                <Select
                    items={groupItems}
                    value={activeGroup?.id}
                    size="xs"
                    class="w-48"
                    testId="dataset-distribution-group-select"
                    onValueChange={(value) => (selectedGroupId = value)}
                />
            {/if}
        </div>
    {/if}
    {#if activeData.length > 0}
        <PanelHeader
            {config}
            classCount={activeData.length}
            visibleClassCount={visible.length}
            {totalCount}
            {valueNoun}
            onConfigure={() => (configDialogOpen = true)}
            onShowAll={() => (config = { ...config, n: activeData.length })}
            onToggleOrientation={() =>
                (config = {
                    ...config,
                    orientation: config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                })}
            onExpand={() => (expandOpen = true)}
        />
    {/if}
    <div class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]">
        <BarChart data={visible} orientation={config.orientation} {totalCount} {onBarClick} />
    </div>
</div>
<DistributionConfigDialog
    bind:open={configDialogOpen}
    maxN={activeData.length}
    {config}
    onApply={(next) => (config = next)}
/>
<ExpandDialog
    bind:open={expandOpen}
    data={activeData}
    {config}
    {valueNoun}
    onConfigChange={(next) => (config = next)}
    {onBarClick}
/>
