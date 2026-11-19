import { beforeEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { clearPlotViewState, usePlotViewState } from './usePlotViewState';

const VIEWPORT = { x: 1, y: 2, scale: 3 };

describe('usePlotViewState', () => {
    beforeEach(() => {
        clearPlotViewState('collection-a');
        clearPlotViewState('collection-b');
    });

    it('starts with nothing hidden, no viewport, the pan tool and no color-by key', () => {
        const state = usePlotViewState('collection-a');

        expect(get(state.hiddenKeys)).toEqual(new Set());
        expect(get(state.viewport)).toBeNull();
        expect(get(state.activeTool)).toBe('pan');
        expect(get(state.selectedColorByKey)).toBeNull();
    });

    it('returns the same stores for the same collection', () => {
        const first = usePlotViewState('collection-a');
        first.activeTool.set('lasso');

        const second = usePlotViewState('collection-a');

        expect(second.activeTool).toBe(first.activeTool);
        expect(get(second.activeTool)).toBe('lasso');
    });

    it('keeps collections apart', () => {
        usePlotViewState('collection-a').viewport.set(VIEWPORT);

        expect(get(usePlotViewState('collection-b').viewport)).toBeNull();
    });

    it('forgets the collection on clearPlotViewState', () => {
        usePlotViewState('collection-a').hiddenKeys.set(new Set(['label:car']));

        clearPlotViewState('collection-a');

        expect(get(usePlotViewState('collection-a').hiddenKeys)).toEqual(new Set());
    });
});
