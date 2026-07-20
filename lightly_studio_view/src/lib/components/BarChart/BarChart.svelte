<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as echarts from 'echarts/core';
    import { BarChart as EchartsBarChart, LineChart as EchartsLineChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
    import { CanvasRenderer } from 'echarts/renderers';
    import {
        buildEchartsOption,
        unionCategories,
        type BarChartOrientation
    } from './buildEchartsOption';
    import type {
        CategoryCount,
        ChartMode,
        ChartNormalize,
        ChartScale,
        ChartSeries
    } from './types';

    echarts.use([
        EchartsBarChart,
        EchartsLineChart,
        GridComponent,
        TooltipComponent,
        LegendComponent,
        CanvasRenderer
    ]);

    interface Props {
        /**
         * Single-series categories rendered in the given order. Ignored when
         * `series` is provided.
         */
        data?: CategoryCount[];
        /**
         * Multiple overlaid series (e.g. one per compared tag). When provided,
         * `data` is ignored and the shared series palette colors each series.
         */
        series?: ChartSeries[];
        /** Chart form (default 'bar'). */
        mode?: ChartMode;
        /** Count vs within-series percentage (default 'count'). */
        normalize?: ChartNormalize;
        /** Value-axis scale (default 'linear'). */
        scale?: ChartScale;
        /** Bar orientation (default 'vertical'). */
        orientation?: BarChartOrientation;
        /**
         * Caps the chart width in px. Vertical bars scroll horizontally once they
         * exceed it; horizontal bars fill it. Defaults to the parent width.
         */
        maxWidthPx?: number;
        /**
         * Caps the chart height in px (default 320). Horizontal bars scroll
         * vertically once they exceed it; vertical bars fill it.
         */
        maxHeightPx?: number;
        /**
         * Denominator for tooltip percentages. Pass the sum over all
         * categories when `data` is a subset (e.g. top-N); defaults to the
         * sum of `data`.
         */
        totalCount?: number;
        /** Called with the clicked category. */
        onBarClick?: (item: CategoryCount) => void;
    }

    const {
        data,
        series,
        mode = 'bar',
        normalize = 'count',
        scale = 'linear',
        orientation = 'vertical',
        maxWidthPx,
        maxHeightPx = 320,
        totalCount,
        onBarClick
    }: Props = $props();

    // One code path: wrap a single `data` array into an unlabelled series.
    const effectiveSeries = $derived<ChartSeries[]>(
        series ?? [{ id: 'default', label: '', data: data ?? [] }]
    );
    const categoryCount = $derived(unionCategories(effectiveSeries).length);
    // Extra thickness per overlaid series keeps grouped bars readable.
    const seriesCount = $derived(effectiveSeries.length);

    let container: HTMLDivElement | undefined = $state();
    let chart: echarts.ECharts | null = $state(null);

    const isHorizontal = $derived(orientation === 'horizontal');
    // Histograms have a small, fixed bin count and should fill the panel rather
    // than scroll at a fixed bar thickness (that pattern is for many-category
    // bar charts).
    const isHistogram = $derived(mode === 'histogram');

    // Bars keep a fixed thickness so many categories overflow into scroll instead
    // of squeezing into unreadability (same pattern as FiftyOne's histograms
    // panel). This extent sizes the category axis (width when vertical, height
    // when horizontal); the +40/+60px covers the axis gutters.
    const BAR_THICKNESS_PX = 28;
    const barsExtentPx = $derived(
        categoryCount * BAR_THICKNESS_PX * Math.max(1, seriesCount * 0.6) + (isHorizontal ? 40 : 60)
    );

    // Outer viewport. Histograms fill the available height of the flex parent
    // (min-height keeps them visible in unbounded contexts like Storybook); bar
    // charts cap the value axis and scroll the category axis past it.
    const viewportStyle = $derived(
        isHistogram
            ? [
                  'height: 100%',
                  `min-height: ${maxHeightPx}px`,
                  maxWidthPx ? `max-width: ${maxWidthPx}px` : null
              ]
                  .filter(Boolean)
                  .join('; ')
            : [
                  isHorizontal ? `max-height: ${maxHeightPx}px` : `height: ${maxHeightPx}px`,
                  maxWidthPx ? `max-width: ${maxWidthPx}px` : null
              ]
                  .filter(Boolean)
                  .join('; ')
    );

    // Inner canvas — ECharts reads these px dimensions. Histograms fill the
    // viewport (bins compress to fit); bar charts grow the category axis past
    // the viewport (scrolling) while the value axis fills 100%.
    const canvasStyle = $derived(
        isHistogram
            ? 'width: 100%; height: 100%;'
            : isHorizontal
              ? `width: 100%; height: ${barsExtentPx}px;`
              : `width: ${barsExtentPx}px; min-width: 100%; height: 100%;`
    );

    $effect(() => {
        if (!container) return;
        const instance = echarts.init(container, null, { renderer: 'canvas' });
        chart = instance;
        instance.on('click', (params: { dataIndex?: number }) => {
            if (typeof params.dataIndex !== 'number') return;
            // Click-through targets the first (primary) series' category.
            const item = effectiveSeries[0]?.data[params.dataIndex];
            if (item) onBarClick?.(item);
        });
        const resizeObserver = new ResizeObserver(() => instance.resize());
        resizeObserver.observe(container);
        return () => {
            resizeObserver.disconnect();
            instance.dispose();
            chart = null;
        };
    });

    $effect(() => {
        if (!chart) return;
        chart.setOption(
            buildEchartsOption(effectiveSeries, {
                totalCount,
                orientation,
                mode,
                normalize,
                scale
            }),
            true
        );
    });

    onDestroy(() => chart?.dispose());
</script>

{#if categoryCount === 0}
    <div class="p-8 text-center text-sm text-muted-foreground" data-testid="bar-chart-empty">
        No data to display.
    </div>
{:else}
    <div
        class="w-full dark:[color-scheme:dark] {isHistogram
            ? 'overflow-hidden'
            : isHorizontal
              ? 'overflow-y-auto'
              : 'overflow-x-auto'}"
        style={viewportStyle}
        data-testid="bar-chart"
    >
        <div bind:this={container} style={canvasStyle}></div>
    </div>
{/if}
