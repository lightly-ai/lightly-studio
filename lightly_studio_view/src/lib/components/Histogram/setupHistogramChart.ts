import * as echarts from 'echarts/core';
import { CustomChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([CustomChart, GridComponent, TooltipComponent, CanvasRenderer]);

interface SetupHistogramChartOptions {
    container: HTMLDivElement;
    getBinCount: () => number;
    onDragStart: (binIndex: number) => void;
    onDragMove: (binIndex: number) => void;
    onDragEnd: () => void;
}

interface HistogramChartSetup {
    chart: echarts.ECharts;
    destroy: () => void;
}

interface MouseOffsetEvent {
    offsetX: number;
}

export function setupHistogramChart(options: SetupHistogramChartOptions): HistogramChartSetup {
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
    options: SetupHistogramChartOptions
): () => void {
    const zr = chart.getZr();
    const toBinIndex = (offsetX: number) => pixelToBinIndex(chart, offsetX, options.getBinCount());
    const handleMouseDown = (event: MouseOffsetEvent) =>
        options.onDragStart(toBinIndex(event.offsetX));
    const handleMouseMove = (event: MouseOffsetEvent) =>
        options.onDragMove(toBinIndex(event.offsetX));
    const handleWindowMouseMove = (event: MouseEvent) => {
        const offsetX = event.clientX - options.container.getBoundingClientRect().left;
        options.onDragMove(toBinIndex(offsetX));
    };
    zr.on('mousedown', handleMouseDown);
    zr.on('mousemove', handleMouseMove);
    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', options.onDragEnd);

    return () => {
        window.removeEventListener('mousemove', handleWindowMouseMove);
        window.removeEventListener('mouseup', options.onDragEnd);
    };
}

function pixelToBinIndex(chart: echarts.ECharts, offsetX: number, binCount: number): number {
    // The x-axis is a value axis over bin indices, so the converted coordinate
    // is a fractional bin index.
    const index = Math.floor(chart.convertFromPixel({ xAxisIndex: 0 }, offsetX));
    return Math.min(Math.max(index, 0), binCount - 1);
}
