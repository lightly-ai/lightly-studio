import * as echarts from 'echarts/core';
import { CustomChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([CustomChart, GridComponent, TooltipComponent, CanvasRenderer]);

interface CreateHistogramChartOptions {
    /** Element the chart mounts into; also observed for resizes. */
    container: HTMLDivElement;
    /** Current number of bins, read lazily so it tracks data changes. */
    getBinCount: () => number;
    /** Pointer pressed on the chart, over the given bin index. */
    onDragStart: (binIndex: number) => void;
    /** Pointer moved to the given bin index while a drag is in progress. */
    onDragMove: (binIndex: number) => void;
    /** Pointer released, ending the drag. */
    onDragEnd: () => void;
}

interface HistogramChartSetup {
    /** The initialized ECharts instance, for pushing options via `setOption`. */
    chart: echarts.ECharts;
    /** Tears down listeners, the resize observer, and the chart instance. */
    destroy: () => void;
}

/** The subset of a zrender pointer event we read: the x offset within the canvas. */
interface MouseOffsetEvent {
    offsetX: number;
}

export function createHistogramChart(options: CreateHistogramChartOptions): HistogramChartSetup {
    const chart = echarts.init(options.container, null, { renderer: 'canvas' });
    const removeDragListeners = setupDragListeners(chart, options);
    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(options.container);

    return {
        chart,
        destroy: () => {
            removeDragListeners();
            resizeObserver.disconnect();
            chart.dispose();
        }
    };
}

function setupDragListeners(
    chart: echarts.ECharts,
    options: CreateHistogramChartOptions
): () => void {
    const zr = chart.getZr();
    const toBinIndex = (offsetX: number) => pixelToBinIndex(chart, offsetX, options.getBinCount());

    let dragging = false;

    const handleMouseDown = (event: MouseOffsetEvent) => {
        dragging = true;
        options.onDragStart(toBinIndex(event.offsetX));
    };
    const handleMouseMove = (event: MouseOffsetEvent) => {
        if (!dragging) return;
        options.onDragMove(toBinIndex(event.offsetX));
    };
    const handleWindowMouseMove = (event: MouseEvent) => {
        if (!dragging) return;
        const offsetX = event.clientX - options.container.getBoundingClientRect().left;
        options.onDragMove(toBinIndex(offsetX));
    };
    const handleMouseUp = () => {
        dragging = false;
        options.onDragEnd();
    };
    zr.on('mousedown', handleMouseDown);
    zr.on('mousemove', handleMouseMove);
    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
        window.removeEventListener('mousemove', handleWindowMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
    };
}

export function pixelToBinIndex(chart: echarts.ECharts, offsetX: number, binCount: number): number {
    // The x-axis is a value axis over bin indices, so the converted coordinate
    // is a fractional bin index.
    const index = Math.floor(chart.convertFromPixel({ xAxisIndex: 0 }, offsetX));
    return Math.min(Math.max(index, 0), binCount - 1);
}
