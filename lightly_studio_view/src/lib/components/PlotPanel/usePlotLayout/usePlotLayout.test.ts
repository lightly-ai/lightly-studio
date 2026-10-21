import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { clearPlotLayout, usePlotLayout } from './usePlotLayout';

const mocks = vi.hoisted(() => ({ embedTextAxes: vi.fn() }));

vi.mock('../PlotTextAxesInputs/embedTextAxes', () => ({ embedTextAxes: mocks.embedTextAxes }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const AXES = { x: [1, 0], y: [0, 1] };
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
        mocks.embedTextAxes.mockResolvedValue(AXES);
        const layout = usePlotLayout('collection-a');
        layout.plotLayout.set('text');

        layout.textAxesDraft.update((draft) => ({ ...draft, xNegative: 'young' }));
        await layout.commitTextAxes(TEXT_AXES);

        // A reopened plot calls the hook again.
        const reopened = usePlotLayout('collection-a');
        expect(get(reopened.plotAxes)).toEqual(AXES);
        expect(get(reopened.textAxesDraft).xNegative).toBe('young');

        // PaCMAP has no axes, and another collection starts in PaCMAP.
        reopened.plotLayout.set('pacmap');
        expect(get(reopened.plotAxes)).toBeNull();
        expect(get(usePlotLayout('collection-b').plotLayout)).toBe('pacmap');
    });

    it('preserves the layout until embedding succeeds and blocks duplicate submissions', async () => {
        let finish!: (axes: typeof AXES) => void;
        mocks.embedTextAxes.mockReturnValue(
            new Promise((resolve) => {
                finish = resolve;
            })
        );
        const layout = usePlotLayout('collection-a');
        const pending = layout.commitTextAxes(TEXT_AXES);
        expect(get(layout.plotLayout)).toBe('pacmap');
        expect(get(layout.plotAxes)).toBeNull();
        expect(get(layout.isEmbeddingAxes)).toBe(true);
        expect(await layout.commitTextAxes(TEXT_AXES)).toBe(false);
        expect(mocks.embedTextAxes).toHaveBeenCalledTimes(1);
        finish(AXES);
        expect(await pending).toBe(true);
        expect(get(layout.plotLayout)).toBe('text');
        expect(get(layout.appliedTextAxes)).toEqual(TEXT_AXES);
        expect(get(layout.isEmbeddingAxes)).toBe(false);
    });

    it('keeps the committed axes and shows the error when the texts fail to embed', async () => {
        mocks.embedTextAxes.mockResolvedValueOnce(AXES);
        const layout = usePlotLayout('collection-a');
        layout.plotLayout.set('text');
        await layout.commitTextAxes(TEXT_AXES);

        mocks.embedTextAxes.mockRejectedValueOnce(new Error('Cannot embed text.'));
        expect(await layout.commitTextAxes(TEXT_AXES)).toBe(false);

        expect(toast.error).toHaveBeenCalledWith('Cannot embed text.');
        expect(get(layout.plotAxes)).toEqual(AXES);
        expect(get(layout.appliedTextAxes)).toEqual(TEXT_AXES);
        expect(get(layout.isEmbeddingAxes)).toBe(false);
    });
});
