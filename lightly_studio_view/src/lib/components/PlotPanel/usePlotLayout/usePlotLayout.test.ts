import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { clearPlotLayout, usePlotLayout } from './usePlotLayout';

const mocks = vi.hoisted(() => ({ embedTextAxes: vi.fn() }));

vi.mock('../PlotTextAxesInputs/embedTextAxes', () => ({ embedTextAxes: mocks.embedTextAxes }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const AXES = { x: [1, 0], y: [0, 1] };
const MARKERS = [{ label: 'young sad', embedding: [0.5, 0.5] }];
const TEXT_LAYOUT = { axes: AXES, markers: MARKERS };
const TEXT_AXES = {
    x: { negative: 'young', positive: 'old' },
    y: { negative: 'sad', positive: 'happy' }
};

describe('usePlotLayout', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        clearPlotLayout('collection-a');
        clearPlotLayout('collection-b');
    });

    it('keeps the layout of a collection for the next plot', async () => {
        mocks.embedTextAxes.mockResolvedValue(TEXT_LAYOUT);
        const layout = usePlotLayout('collection-a');
        layout.plotLayout.set('text');

        layout.textAxesDraft.update((draft) => ({ ...draft, xNegative: 'young' }));
        await layout.commitTextAxes(TEXT_AXES);

        // A reopened plot calls the hook again.
        const reopened = usePlotLayout('collection-a');
        expect(get(reopened.plotAxes)).toEqual(AXES);
        expect(get(reopened.plotMarkers)).toEqual(MARKERS);
        expect(get(reopened.textAxesDraft).xNegative).toBe('young');

        // PaCMAP has no axes and no markers, and another collection starts in PaCMAP.
        reopened.plotLayout.set('pacmap');
        expect(get(reopened.plotAxes)).toBeNull();
        expect(get(reopened.plotMarkers)).toEqual([]);
        expect(get(usePlotLayout('collection-b').plotLayout)).toBe('pacmap');
    });

    it('keeps the committed axes and shows the error when the texts fail to embed', async () => {
        mocks.embedTextAxes.mockResolvedValueOnce(TEXT_LAYOUT);
        const layout = usePlotLayout('collection-a');
        layout.plotLayout.set('text');
        await layout.commitTextAxes(TEXT_AXES);

        mocks.embedTextAxes.mockRejectedValueOnce(new Error('Cannot embed text.'));
        expect(await layout.commitTextAxes(TEXT_AXES)).toBe(false);

        expect(toast.error).toHaveBeenCalledWith('Cannot embed text.');
        expect(get(layout.plotAxes)).toEqual(AXES);
    });
});
