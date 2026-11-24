import { describe, expect, it } from 'vitest';
import { getPlotComputeView, isPlotRequestEnabled, type PlotComputeView } from './plotComputeGate';

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
        [{ isStatusError: true, isComputeStarted: true }, 'computing'],
        [{ isStatusError: true, status: { is_computed: true, embedding_count: null } }, 'plot'],
        [{ isStatusError: true, status: { is_computed: false, embedding_count: 0 } }, 'error'],
        [{ status: { is_computed: true, embedding_count: null } }, 'plot'],
        [{ status: { is_computed: false, embedding_count: 250_000 } }, 'prompt'],
        [{ status: { is_computed: false, embedding_count: 249_999 } }, 'computing'],
        [{ status: { is_computed: false, embedding_count: null } }, 'prompt'],
        [
            { status: { is_computed: false, embedding_count: 2_000_000 }, isComputeStarted: true },
            'computing'
        ],
        [{ status: { is_computed: true, embedding_count: null }, isComputeStarted: true }, 'plot'],
        [{ status: { is_computed: false, embedding_count: 0 } }, 'computing']
    ])('getPlotComputeView(%o) is %s', (input, expected) => {
        expect(getPlotComputeView({ ...defaultInput, ...input })).toBe(expected);
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
