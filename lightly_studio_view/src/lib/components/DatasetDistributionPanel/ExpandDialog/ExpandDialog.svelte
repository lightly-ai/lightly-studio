<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import { BarChart, type CategoryCount } from '$lib/components/BarChart';
    import DistributionConfigDialog from '../DistributionConfigDialog/DistributionConfigDialog.svelte';
    import PanelHeader from '../PanelHeader/PanelHeader.svelte';
    import { selectVisibleCounts } from '../selectVisibleCounts';
    import type { DistributionConfig } from '../types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Full class counts; the dialog applies `config` itself. */
        data: CategoryCount[];
        /** The applied view config, shared with the panel. */
        config: DistributionConfig;
        /** Noun for the header summary (e.g. 'annotations', 'samples'). */
        valueNoun?: string;
        /** Invoked when the user applies a new config from the expanded view. */
        onConfigChange: (config: DistributionConfig) => void;
        onBarClick?: (item: CategoryCount) => void;
    }

    let {
        open = $bindable(),
        data,
        config,
        valueNoun = 'annotations',
        onConfigChange,
        onBarClick
    }: Props = $props();

    let configDialogOpen = $state(false);
    // Measured height of the chart viewport; drives the chart's height budget and
    // tracks container resizes (bind:clientHeight is backed by a ResizeObserver).
    let chartHeight = $state(0);
    let clientWidth = $state(0);

    const visible = $derived(selectVisibleCounts(data, config));
    const totalCount = $derived(data.reduce((sum, item) => sum + item.count, 0));
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="flex h-[92vh] max-w-[94vw] flex-col sm:max-w-[94vw]">
        <Dialog.Header>
            <Dialog.Title>Class distribution</Dialog.Title>
            <Dialog.Description>Hover a bar for the full class name and count</Dialog.Description>
        </Dialog.Header>
        <PanelHeader
            {config}
            classCount={data.length}
            visibleClassCount={visible.length}
            {totalCount}
            {valueNoun}
            onConfigure={() => (configDialogOpen = true)}
            onShowAll={() => onConfigChange({ ...config, mode: 'topN', n: data.length })}
            onToggleOrientation={() =>
                onConfigChange({
                    ...config,
                    orientation: config.orientation === 'horizontal' ? 'vertical' : 'horizontal'
                })}
            testIdPrefix="dataset-distribution-expanded"
        />
        <div
            class="min-h-0 flex-1 overflow-y-auto dark:[color-scheme:dark]"
            bind:clientHeight={chartHeight}
        >
            <BarChart
                data={visible}
                orientation={config.orientation}
                maxHeightPx={chartHeight || undefined}
                maxWidthPx={clientWidth || undefined}
                {totalCount}
                {onBarClick}
            />
        </div>
    </Dialog.Content>
</Dialog.Root>

<DistributionConfigDialog
    bind:open={configDialogOpen}
    allClasses={data.map((item) => item.label)}
    {config}
    onApply={onConfigChange}
/>
