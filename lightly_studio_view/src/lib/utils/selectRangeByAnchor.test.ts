import { describe, expect, it, vi } from 'vitest';
import { selectRangeByAnchor } from './selectRangeByAnchor';

describe('selectRangeByAnchor', () => {
    it('selects clicked item and sets anchor on regular click', () => {
        const onSelectSample = vi.fn();

        const nextAnchor = selectRangeByAnchor({
            sampleIdsInOrder: ['a', 'b', 'c'],
            selectedSampleIds: new Set<string>(),
            clickedSampleId: 'b',
            clickedIndex: 1,
            shiftKey: false,
            anchorSampleId: null,
            onSelectSample
        });

        expect(onSelectSample).toHaveBeenCalledTimes(1);
        expect(onSelectSample).toHaveBeenCalledWith('b');
        expect(nextAnchor).toBe('b');
    });

    it('adds the full range on Shift+click when anchor exists', () => {
        const onSelectSample = vi.fn();

        const nextAnchor = selectRangeByAnchor({
            sampleIdsInOrder: ['a', 'b', 'c', 'd', 'e'],
            selectedSampleIds: new Set<string>(['b']),
            clickedSampleId: 'e',
            clickedIndex: 4,
            shiftKey: true,
            anchorSampleId: 'b',
            onSelectSample
        });

        expect(onSelectSample).toHaveBeenCalledTimes(3);
        expect(onSelectSample).toHaveBeenNthCalledWith(1, 'c');
        expect(onSelectSample).toHaveBeenNthCalledWith(2, 'd');
        expect(onSelectSample).toHaveBeenNthCalledWith(3, 'e');
        expect(nextAnchor).toBe('b');
    });

    it('falls back to regular click behavior when Shift+click has no valid anchor', () => {
        const onSelectSample = vi.fn();

        const nextAnchor = selectRangeByAnchor({
            sampleIdsInOrder: ['a', 'b', 'c'],
            selectedSampleIds: new Set<string>(),
            clickedSampleId: 'c',
            clickedIndex: 2,
            shiftKey: true,
            anchorSampleId: 'missing',
            onSelectSample
        });

        expect(onSelectSample).toHaveBeenCalledTimes(1);
        expect(onSelectSample).toHaveBeenCalledWith('c');
        expect(nextAnchor).toBe('c');
    });
});
