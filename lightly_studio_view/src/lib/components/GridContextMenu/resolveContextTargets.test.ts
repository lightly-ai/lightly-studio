import { describe, expect, it } from 'vitest';
import { resolveContextTargets } from './resolveContextTargets';

describe('resolveContextTargets', () => {
    it('targets the whole selection when the clicked sample is inside it', () => {
        const selectedSampleIds = new Set(['a', 'b', 'c']);

        const result = resolveContextTargets({ clickedId: 'b', selectedSampleIds });

        expect(result.isSelectionTarget).toBe(true);
        expect([...result.ids].sort()).toEqual(['a', 'b', 'c']);
    });

    it('targets only the clicked sample when it is outside the selection', () => {
        const selectedSampleIds = new Set(['a', 'b', 'c']);

        const result = resolveContextTargets({ clickedId: 'd', selectedSampleIds });

        expect(result).toEqual({ ids: ['d'], isSelectionTarget: false });
    });

    it('targets only the clicked sample when nothing is selected', () => {
        const result = resolveContextTargets({
            clickedId: 'a',
            selectedSampleIds: new Set<string>()
        });

        expect(result).toEqual({ ids: ['a'], isSelectionTarget: false });
    });

    it('does not mutate the selection it was given', () => {
        const selectedSampleIds = new Set(['a', 'b']);

        resolveContextTargets({ clickedId: 'a', selectedSampleIds });
        resolveContextTargets({ clickedId: 'z', selectedSampleIds });

        expect([...selectedSampleIds]).toEqual(['a', 'b']);
    });
});
