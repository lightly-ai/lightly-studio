import { describe, expect, it } from 'vitest';
import {
    PLOT_COMPUTE_CONFIRM_THRESHOLD,
    formatElapsed,
    getPlotComputeView,
    isPlotRequestEnabled,
    type PlotComputeView
} from './plotComputeGate';

type GateInput = Parameters<typeof getPlotComputeView>[0];

const defaultInput: GateInput = {
    status: undefined,
    isStatusError: false,
    isAxesLayout: false,
    isComputeStarted: false
};

describe('getPlotComputeView', () => {
    it.each<[Partial<GateInput>, PlotComputeView]>([
        [{ isAxesLayout: true }, 'plot'],
        [
            { isAxesLayout: true, status: { is_computed: false, embedding_count: 2_000_000 } },
            'plot'
        ],
        [{}, 'checking'],
        // The status cache can expire while a started compute still runs on the server.
        [{ isComputeStarted: true }, 'computing'],
        [{ isStatusError: true }, 'error'],
        [{ status: { is_computed: true, embedding_count: null } }, 'plot'],
        [{ status: { is_computed: false, embedding_count: 250_000 } }, 'prompt'],
        [{ status: { is_computed: false, embedding_count: 249_999 } }, 'computing'],
        [
            { status: { is_computed: false, embedding_count: 2_000_000 }, isComputeStarted: true },
            'computing'
        ],
        [{ status: { is_computed: false, embedding_count: 0 } }, 'computing']
    ])('getPlotComputeView(%o) is %s', (input, expected) => {
        expect(getPlotComputeView({ ...defaultInput, ...input })).toBe(expected);
    });

    it('uses 250,000 as the threshold', () => {
        expect(PLOT_COMPUTE_CONFIRM_THRESHOLD).toBe(250_000);
    });
});

describe('isPlotRequestEnabled', () => {
    it.each<[PlotComputeView, boolean]>([
        ['checking', false],
        ['error', false],
        ['prompt', false],
        ['computing', true],
        ['plot', true]
    ])('isPlotRequestEnabled(%s) is %s', (view, expected) => {
        expect(isPlotRequestEnabled(view)).toBe(expected);
    });
});

describe('formatElapsed', () => {
    it.each([
        [0, '0:00'],
        [999, '0:00'],
        [222_000, '3:42'],
        [3_725_000, '62:05']
    ])('formatElapsed(%d) is %s', (ms, expected) => {
        expect(formatElapsed(ms)).toBe(expected);
    });
});
