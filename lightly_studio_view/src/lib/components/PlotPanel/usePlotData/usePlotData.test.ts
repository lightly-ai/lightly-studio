import { describe, it, expect, vi } from 'vitest';
import { get } from 'svelte/store';
import type { ArrowData } from '../useArrowData/useArrowData';

type Point = { x: number; y: number };

vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: vi.fn()
}));

vi.mock('../getCategoryBySelection/getCategoryBySelection', () => ({
    getCategoryBySelection: vi.fn((selection) => (prevValue: number, index: number) => {
        // Mock implementation: first two points are inside the polygon (keep prevValue), rest are outside (0)
        if (!selection) return prevValue;
        return index < 2 ? prevValue : 0;
    })
}));

// Import after mocks are set up
const { usePlotData } = await import('./usePlotData');

describe('usePlotData', () => {
    // color_categories + fulfils_filter resolve to categories [1, 2, 0, 3]: sample1 has no
    // categories (-> unassigned 1), sample2 takes the first of its two categories (2),
    // sample3 is filtered out (-> 0).
    const createMockArrowData = (): ArrowData => ({
        x: new Float32Array([1.0, 2.0, 3.0, 4.0]),
        y: new Float32Array([5.0, 6.0, 7.0, 8.0]),
        fulfils_filter: new Uint8Array([1, 1, 0, 1]),
        color_categories: [[], [2, 5], [], [3]],
        sample_id: ['sample1', 'sample2', 'sample3', 'sample4']
    });

    it('should return empty data when arrowData is undefined', () => {
        const result = usePlotData({
            arrowData: undefined as unknown as ArrowData,
            rangeSelection: null
        });

        expect(get(result.data)).toBeUndefined();
        expect(get(result.error)).toBeUndefined();
        expect(get(result.selectedSampleIds)).toEqual([]);
    });

    it('should set plot data with color categories when no range selection', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null
        });

        const data = get(result.data);
        expect(data).toEqual({
            x: mockData.x,
            y: mockData.y,
            category: new Uint8Array([1, 2, 0, 3])
        });
        expect(get(result.selectedSampleIds)).toEqual([]);
    });

    it('falls back to the next visible category when one is hidden', () => {
        const mockData = createMockArrowData();
        // sample2 belongs to categories [2, 3]; sample4 only to [4].
        mockData.color_categories = [[], [2, 3], [], [4]];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            hiddenCategories: new Set([2, 4])
        });

        const data = get(result.data) as { category: Uint8Array };
        // sample2 falls back from hidden 2 to visible 3; sample4's only category is hidden -> unassigned 1.
        expect(Array.from(data.category)).toEqual([1, 3, 0, 1]);
    });

    it('should update categories based on range selection', () => {
        const mockData = createMockArrowData();
        const mockSelection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: mockSelection
        });

        const data = get(result.data);
        expect(data?.category).toBeInstanceOf(Uint8Array);

        // First two points are in polygon (keep previous categories), last two are outside (demoted to 0)
        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray[0]).toBe(1); // in polygon, keeps INCLUDED_BY_FILTERS_CATEGORY
        expect(categoryArray[1]).toBe(2); // in polygon, preserves color category
        expect(categoryArray[2]).toBe(0); // outside polygon, demoted to EXCLUDED_BY_FILTERS_CATEGORY
        expect(categoryArray[3]).toBe(0); // outside polygon, demoted to EXCLUDED_BY_FILTERS_CATEGORY
    });

    it('should collect selected sample ids when range selection is applied', () => {
        const mockData = createMockArrowData();
        const mockSelection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: mockSelection
        });

        const selectedIds = get(result.selectedSampleIds);
        // Based on our mock, first two non-zero categories should be selected
        expect(selectedIds).toEqual(['sample1', 'sample2']);
    });

    it('should handle empty range selection array', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: []
        });

        const data = get(result.data);
        expect(data?.category).toBeInstanceOf(Uint8Array);
        // Empty array still triggers selection logic with our mock
        expect(get(result.selectedSampleIds)).toEqual(['sample1', 'sample2']);
    });

    it('should set all categories to 1 when hasActiveFilter is false', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            hasActiveFilter: false
        });

        const data = get(result.data);
        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray).toEqual([1, 1, 1, 1]);
        expect(get(result.selectedSampleIds)).toEqual([]);
    });

    it('should collect selected ids from range selection when hasActiveFilter is false', () => {
        const mockData = createMockArrowData();
        const mockSelection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: mockSelection,
            hasActiveFilter: false
        });

        const data = get(result.data) as { category: Uint8Array };
        const categoryArray = Array.from(data.category);
        expect(categoryArray).toEqual([1, 1, 0, 0]);
        expect(get(result.selectedSampleIds)).toEqual(['sample1', 'sample2']);
    });

    it('should keep categories 2 and above selectable during range selection', () => {
        const mockData = createMockArrowData();
        const mockSelection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: mockSelection
        });

        expect(get(result.selectedSampleIds)).toEqual(['sample1', 'sample2']);
    });

    it('should preserve highlighted non-zero color categories and demote other samples', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            highlightedSampleIds: ['sample2', 'sample3']
        });

        const data = get(result.data) as { category: Uint8Array };
        expect(Array.from(data.category)).toEqual([0, 2, 0, 0]);
    });

    it('should return error store', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null
        });

        expect(result.error).toBeDefined();
        expect(get(result.error)).toBeUndefined();
    });
});
