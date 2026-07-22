import { describe, expect, it, vi } from 'vitest';
import type { ECharts } from 'echarts/core';
import { pixelToBinIndex } from './createHistogramChart';

// createHistogramChart.ts registers echarts modules at import time; stub them so
// the module loads without pulling in the real (heavy) echarts runtime.
vi.mock('echarts/core', () => ({ use: vi.fn() }));
vi.mock('echarts/charts', () => ({ CustomChart: {} }));
vi.mock('echarts/components', () => ({ GridComponent: {}, TooltipComponent: {} }));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

// The x-axis is a value axis over bin indices; 10px per bin index mirrors the
// component test's canvas geometry (20 bins over a 200px canvas).
const makeChart = (): ECharts =>
    ({
        convertFromPixel: (_finder: unknown, offsetX: number) => offsetX / 10
    }) as unknown as ECharts;

describe('pixelToBinIndex', () => {
    it('floors a fractional bin index to the containing bin', () => {
        // offsetX 25 → 2.5 → bin 2.
        expect(pixelToBinIndex(makeChart(), 25, 20)).toBe(2);
    });

    it('clamps offsets before the left edge to the first bin', () => {
        expect(pixelToBinIndex(makeChart(), -50, 20)).toBe(0);
    });

    it('clamps offsets past the right edge to the last bin', () => {
        expect(pixelToBinIndex(makeChart(), 9999, 20)).toBe(19);
    });
});
