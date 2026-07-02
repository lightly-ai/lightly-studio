<script lang="ts">
    import { X } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';
    import DistributionConfigDialog from './DistributionConfigDialog/DistributionConfigDialog.svelte';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from './selectVisibleCounts';
    import type { DistributionConfig } from './types';

    interface Props {
        /** Class counts; ranking and top-N selection are user-configurable. */
        data: CategoryCount[];
        title?: string;
        /** Top classes shown by default. */
        topN?: number;
        /** Renders a close button in the header when provided. */
        onClose?: () => void;
        /** Called with the clicked class. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const { data, title = 'Class distribution', topN = 20, onClose, onBarClick }: Props = $props();

    let config: DistributionConfig = $state({ n: topN, sortBy: 'count' });
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);

    const visible = $derived(selectVisibleCounts(data, config));
    const totalCount = $derived(data.reduce((sum, item) => sum + item.count, 0));
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
    {#if data.length > 0}
        <PanelHeader
            {config}
            classCount={data.length}
            visibleClassCount={visible.length}
            {totalCount}
            onConfigure={() => (configDialogOpen = true)}
            onExpand={() => (expandOpen = true)}
        />
    {/if}
    <div class="min-h-0 flex-1 overflow-y-auto">
        <BarChart data={visible} {onBarClick} />
    </div>
</div>
<DistributionConfigDialog
    bind:open={configDialogOpen}
    maxN={data.length}
    {config}
    onApply={(next) => (config = next)}
/>
<ExpandDialog bind:open={expandOpen} data={visible} {onBarClick} />
