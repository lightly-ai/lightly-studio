import { describe, it, expect, vi } from 'vitest';
import { get } from 'svelte/store';
import type { ArrowData } from '../useArrowData/useArrowData';

type Point = { x: number; y: number };

vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: vi.fn()
}));

vi.mock('../getCategoryBySelection/getCategoryBySelection', () => ({
    getCategoryBySelection: vi.fn((selection) => (prevValue: number, index: number) => {
        // Mock implementation: first two points are inside the polygon (keep prevValue), rest
        // are outside (demoted to EXCLUDED_BY_FILTERS_CATEGORY = 1).
        if (!selection) return prevValue;
        return index < 2 ? prevValue : 1;
    })
}));

// Import after mocks are set up
const { usePlotData } = await import('./usePlotData');

describe('usePlotData', () => {
    // color_categories + fulfils_filter resolve to categories [2, 3, 1, 4]: sample1 has no
    // categories (-> unassigned INCLUDED 2), sample2 takes the first of its two categories (3),
    // sample3 is filtered out (-> EXCLUDED 1), sample4 takes its only category (4).
    const createMockArrowData = (): ArrowData => ({
        x: new Float32Array([1.0, 2.0, 3.0, 4.0]),
        y: new Float32Array([5.0, 6.0, 7.0, 8.0]),
        fulfils_filter: new Uint8Array([1, 1, 0, 1]),
        color_categories: [[], [3, 5], [], [4]],
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
            category: new Uint8Array([2, 3, 1, 4])
        });
        expect(get(result.selectedSampleIds)).toEqual([]);
    });

    it('falls back to the next visible category when one is hidden', () => {
        const mockData = createMockArrowData();
        // sample2 belongs to categories [3, 4]; sample4 only to [5].
        mockData.color_categories = [[], [3, 4], [], [5]];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            hiddenCategories: new Set([3, 5])
        });

        const data = get(result.data) as { category: Uint8Array };
        // sample2 falls back from hidden 3 to visible 4; sample4's only category is hidden -> unassigned 2.
        expect(Array.from(data.category)).toEqual([2, 4, 1, 2]);
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

        // First two points are in polygon (keep previous categories), last two are outside (demoted to 1)
        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray[0]).toBe(2); // in polygon, keeps INCLUDED_BY_FILTERS_CATEGORY
        expect(categoryArray[1]).toBe(3); // in polygon, preserves color category
        expect(categoryArray[2]).toBe(1); // outside polygon, demoted to EXCLUDED_BY_FILTERS_CATEGORY
        expect(categoryArray[3]).toBe(1); // outside polygon, demoted to EXCLUDED_BY_FILTERS_CATEGORY
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
        // Based on our mock, first two non-excluded categories should be selected
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

    it('should set all categories to INCLUDED (2) when hasActiveFilter is false', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            hasActiveFilter: false
        });

        const data = get(result.data);
        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray).toEqual([2, 2, 2, 2]);
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
        expect(categoryArray).toEqual([2, 2, 1, 1]);
        expect(get(result.selectedSampleIds)).toEqual(['sample1', 'sample2']);
    });

    it('keeps included and colored categories selectable during range selection', () => {
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

    it('does not select an in-lasso point routed to HIDDEN_CATEGORY', () => {
        const mockData = createMockArrowData();
        // sample1 and sample3 are filtered out; hiding EXCLUDED routes them to HIDDEN (0).
        mockData.fulfils_filter = new Uint8Array([0, 1, 0, 1]);
        const mockSelection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: mockSelection,
            hiddenCategories: new Set([1])
        });

        const data = get(result.data) as { category: Uint8Array };
        // Only sample2 is selectable; the rest are Excluded, then hidden (row 1) -> HIDDEN (0).
        expect(Array.from(data.category)).toEqual([0, 3, 0, 0]);
        expect(get(result.selectedSampleIds)).toEqual(['sample2']);
    });

    it('does not select an in-lasso point hidden via the "No category" legend row', () => {
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
            hiddenCategories: new Set([2]) // hide "Included by filters / No category"
        });

        const data = get(result.data) as { category: Uint8Array };
        // sample1 is in-lasso but "No category" (2) -> routed to HIDDEN (0); sample2 keeps color 3.
        expect(Array.from(data.category)).toEqual([0, 3, 1, 1]);
        // The hidden sample1 must not be committed to the filter, only the visible sample2.
        expect(get(result.selectedSampleIds)).toEqual(['sample2']);
    });

    it('keeps highlighted-path HIDDEN points hidden rather than demoting them', () => {
        const mockData = createMockArrowData();
        mockData.fulfils_filter = new Uint8Array([0, 1, 0, 1]);

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            highlightedSampleIds: ['sample1', 'sample2'],
            hiddenCategories: new Set([1])
        });

        const data = get(result.data) as { category: Uint8Array };
        // Only highlighted+passing sample2 keeps its color; the rest are Excluded, then hidden -> 0.
        expect(Array.from(data.category)).toEqual([0, 3, 0, 0]);
    });

    it('should preserve highlighted color categories and demote other samples', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            highlightedSampleIds: ['sample2', 'sample3']
        });

        const data = get(result.data) as { category: Uint8Array };
        // sample2 is highlighted -> keeps 3; sample3 is already EXCLUDED (1) -> stays 1;
        // sample1 and sample4 are not highlighted -> demoted to EXCLUDED 1.
        expect(Array.from(data.category)).toEqual([1, 3, 1, 1]);
    });

    it('hides "No category" points by their displayed bucket, not their pre-demotion identity', () => {
        const mockData = createMockArrowData();
        // All pass the filter, so demotion is purely highlight-driven; sample1/sample3 have no
        // annotation (would be "No category" 2 if Included).
        mockData.fulfils_filter = new Uint8Array([1, 1, 1, 1]);

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            highlightedSampleIds: ['sample2'],
            hiddenCategories: new Set([2]) // hide "No category"
        });

        const data = get(result.data) as { category: Uint8Array };
        // Un-highlighted points demote to Excluded and render as Excluded; hiding "No category" (2)
        // must not touch them. (The pre-fix pipeline produced [0, 3, 0, 0].)
        expect(Array.from(data.category)).toEqual([1, 3, 1, 1]);
    });

    it('hides all points when "Included by filters" is hidden and there is no active filter', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            hasActiveFilter: false,
            hiddenCategories: new Set([2])
        });

        const data = get(result.data) as { category: Uint8Array };
        // Without a filter every point is "Included by filters" (2); hiding that row routes
        // them all to HIDDEN (0) instead of staying visible.
        expect(Array.from(data.category)).toEqual([0, 0, 0, 0]);
    });

    it('highlights points inside a committed region when there is no live range selection', () => {
        const mockData = createMockArrowData();
        const region: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null,
            highlightRegion: region
        });

        const data = get(result.data) as { category: Uint8Array };
        // First two points are inside the region (keep their category); the rest are demoted to
        // EXCLUDED (1), so the plot reflects the committed selection.
        expect(Array.from(data.category)).toEqual([2, 3, 1, 1]);
        // The resolved ids live server-side; the region path must not recompute them client-side.
        expect(get(result.selectedSampleIds)).toEqual([]);
    });

    it('prefers the live range selection over a committed region', () => {
        const mockData = createMockArrowData();
        const selection: Point[] = [
            { x: 0, y: 0 },
            { x: 2, y: 0 },
            { x: 2, y: 6 },
            { x: 0, y: 6 }
        ];

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: selection,
            highlightRegion: selection
        });

        // The range-selection branch still populates selectedSampleIds for the pending commit.
        expect(get(result.selectedSampleIds)).toEqual(['sample1', 'sample2']);
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
