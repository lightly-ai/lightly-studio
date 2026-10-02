import { describe, expect, it, vi } from 'vitest';
import type { ECharts } from 'echarts/core';
import { pixelToCell } from './createHeatmapChart';

// createHeatmapChart.ts registers echarts modules at import time; stub them so
// the module loads without pulling in the real (heavy) echarts runtime.
vi.mock('echarts/core', () => ({ use: vi.fn() }));
vi.mock('echarts/charts', () => ({ HeatmapChart: {} }));
vi.mock('echarts/components', () => ({
    GridComponent: {},
    TooltipComponent: {},
    VisualMapComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

// Category axes convert to bucket indices without clamping; 10px per bucket.
const makeChart = (): ECharts =>
    ({
        convertFromPixel: (_finder: unknown, [x, y]: number[]) => [x / 10, y / 10]
    }) as unknown as ECharts;

describe('pixelToCell', () => {
    const gridSize = { xCount: 4, yCount: 3 };

    it('converts an offset inside the grid to its cell', () => {
        expect(pixelToCell(makeChart(), 21, 9, gridSize)).toEqual({ x: 2, y: 1 });
    });

    it('clamps offsets outside the grid to the edge cells', () => {
        expect(pixelToCell(makeChart(), -50, 9999, gridSize)).toEqual({ x: 0, y: 2 });
        expect(pixelToCell(makeChart(), 9999, -50, gridSize)).toEqual({ x: 3, y: 0 });
    });
});
