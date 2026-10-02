import * as echarts from 'echarts/core';
import { HeatmapChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { HeatmapCell } from './types';

echarts.use([HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

interface GridSize {
    xCount: number;
    yCount: number;
}

interface CreateHeatmapChartOptions {
    /** Element the chart mounts into; also observed for resizes. */
    container: HTMLDivElement;
    /** Current number of buckets per axis, read lazily so it tracks data changes. */
    getGridSize: () => GridSize;
    /** Pointer pressed on a cell. */
    onDragStart: (cell: HeatmapCell) => void;
    /** Pointer moved to the given cell while a drag is in progress. */
    onDragMove: (cell: HeatmapCell) => void;
    /** Pointer released, ending the drag. */
    onDragEnd: () => void;
    /** An axis label was clicked, with the bucket index of the label. */
    onAxisLabelClick: (axis: 'x' | 'y', index: number) => void;
}

interface HeatmapChartSetup {
    /** The initialized ECharts instance, for pushing options via `setOption`. */
    chart: echarts.ECharts;
    /** Tears down listeners, the resize observer, and the chart instance. */
    destroy: () => void;
}

/** The subset of a zrender pointer event we read: the offset within the canvas. */
interface MouseOffsetEvent {
    offsetX: number;
    offsetY: number;
}

/** The subset of an ECharts click event we read to find axis label clicks. */
interface AxisLabelClickEvent {
    componentType?: string;
    targetType?: string;
    dataIndex?: number;
}

export function createHeatmapChart(options: CreateHeatmapChartOptions): HeatmapChartSetup {
    const chart = echarts.init(options.container, null, { renderer: 'canvas' });
    const removeDragListeners = setupDragListeners(chart, options);
    chart.on('click', (event: AxisLabelClickEvent) => {
        // On a category axis, the data index of a label is its bucket index.
        if (event.targetType !== 'axisLabel' || event.dataIndex === undefined) return;
        if (event.componentType === 'xAxis') options.onAxisLabelClick('x', event.dataIndex);
        if (event.componentType === 'yAxis') options.onAxisLabelClick('y', event.dataIndex);
    });
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

/** Converts a canvas offset to the cell under it, clamped to the grid. */
export function pixelToCell(
    chart: echarts.ECharts,
    offsetX: number,
    offsetY: number,
    { xCount, yCount }: GridSize
): HeatmapCell {
    // Category axes convert to bucket indices, but do not clamp offsets outside the grid.
    const [x, y] = chart.convertFromPixel({ gridIndex: 0 }, [offsetX, offsetY]) as number[];
    return { x: clamp(Math.round(x), xCount - 1), y: clamp(Math.round(y), yCount - 1) };
}

function setupDragListeners(
    chart: echarts.ECharts,
    options: CreateHeatmapChartOptions
): () => void {
    const toCell = (offsetX: number, offsetY: number) =>
        pixelToCell(chart, offsetX, offsetY, options.getGridSize());
    let dragging = false;

    const handleMouseDown = (event: MouseOffsetEvent) => {
        // A press outside the cells, for example on an axis label, starts no drag.
        if (!chart.containPixel({ gridIndex: 0 }, [event.offsetX, event.offsetY])) return;
        dragging = true;
        options.onDragStart(toCell(event.offsetX, event.offsetY));
    };
    // The window listener keeps the drag going when the pointer leaves the canvas.
    const handleWindowMouseMove = (event: MouseEvent) => {
        if (!dragging) return;
        const bounds = options.container.getBoundingClientRect();
        options.onDragMove(toCell(event.clientX - bounds.left, event.clientY - bounds.top));
    };
    const handleMouseUp = () => {
        if (!dragging) return;
        dragging = false;
        options.onDragEnd();
    };
    chart.getZr().on('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
        window.removeEventListener('mousemove', handleWindowMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
    };
}

function clamp(value: number, max: number): number {
    return Math.min(Math.max(value, 0), max);
}
