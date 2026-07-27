<script lang="ts">
    import ConfusionMatrix from '../ConfusionMatrix.svelte';
    import type { ConfusionCellSelection, ConfusionMatrix as ConfusionMatrixData } from '../types';
    import ClassSetDialog from '../ClassSetDialog/ClassSetDialog.svelte';
    import type { ClassSetConfig, ColorConfig } from '../ClassSetDialog/types';
    import { buildSubMatrix, getRealClasses } from '../topNMatrix';
    import ExpandDialog from './ExpandDialog/ExpandDialog.svelte';
    import PanelHeader from './PanelHeader/PanelHeader.svelte';
    import { selectVisibleClasses } from './selectVisibleClasses';

    interface Props {
        matrix: ConfusionMatrixData;
        /** Most-confused classes shown by default. */
        topN?: number;
        showLegend?: boolean;
        /** Forwarded to the underlying chart; fires on a real class-by-class cell click. */
        onCellClick?: (cell: ConfusionCellSelection) => void;
        /** Called when the user clicks the expand button. */
        onExpand?: (data: { visibleClassCount: number; totalClassCount: number }) => void;
        /** Called when the user applies new class-filter or color settings. */
        onConfigApplied?: (data: {
            mode: 'topN' | 'manual';
            n: number;
            sortBy: string;
            visibleClassCount: number;
        }) => void;
    }

    const {
        matrix,
        topN = 5,
        showLegend = false,
        onCellClick,
        onExpand,
        onConfigApplied
    }: Props = $props();

    let config: ClassSetConfig = $state({
        mode: 'topN',
        n: topN,
        sortBy: 'most-confused',
        manualClasses: []
    });
    let color: ColorConfig = $state({ intensity: 1, logScale: true });
    let configDialogOpen = $state(false);
    let expandOpen = $state(false);

    const realClasses = $derived(getRealClasses(matrix));
    const visibleClasses = $derived(selectVisibleClasses(matrix, config));
    const subMatrix = $derived(buildSubMatrix(matrix, visibleClasses));

    const applyConfig = (nextConfig: ClassSetConfig, nextColor: ColorConfig) => {
        config = nextConfig;
        color = nextColor;
        const newVisibleClasses = selectVisibleClasses(matrix, nextConfig);
        onConfigApplied?.({
            mode: nextConfig.mode,
            n: nextConfig.n,
            sortBy: nextConfig.sortBy,
            visibleClassCount: newVisibleClasses.length
        });
    };

    const handleExpand = () => {
        onExpand?.({
            visibleClassCount: visibleClasses.length,
            totalClassCount: realClasses.length
        });
        expandOpen = true;
    };
</script>

<PanelHeader
    {config}
    {color}
    realClassCount={realClasses.length}
    visibleClassCount={visibleClasses.length}
    onConfigure={() => (configDialogOpen = true)}
    onExpand={handleExpand}
/>
<ConfusionMatrix
    matrix={subMatrix}
    {showLegend}
    colorIntensity={color.intensity}
    logScale={color.logScale}
    {onCellClick}
/>
<ClassSetDialog
    bind:open={configDialogOpen}
    allClasses={realClasses}
    {config}
    {color}
    onApply={applyConfig}
/>
<ExpandDialog bind:open={expandOpen} matrix={subMatrix} {color} {showLegend} {onCellClick} />
