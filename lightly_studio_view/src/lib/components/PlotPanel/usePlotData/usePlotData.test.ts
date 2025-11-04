import { describe, it, expect, vi } from 'vitest';
import { get } from 'svelte/store';
import type { ArrowData } from '../useArrowData/useArrowData';

type Point = { x: number; y: number };

vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: vi.fn()
}));

vi.mock('../getCategoryBySelection/getCategoryBySelection', () => ({
    getCategoryBySelection: vi.fn((selection) => (prevValue: number, index: number) => {
        // Mock implementation: if point is in first half of array, mark as selected (2)
        if (selection && prevValue === 1 && index < 2) {
            return 2;
        }
        return prevValue;
    })
}));

// Import after mocks are set up
const { usePlotData } = await import('./usePlotData');

describe('usePlotData', () => {
    const createMockArrowData = (): ArrowData => ({
        x: new Float32Array([1.0, 2.0, 3.0, 4.0]),
        y: new Float32Array([5.0, 6.0, 7.0, 8.0]),
        fulfils_filter: new Uint8Array([1, 1, 0, 1]),
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

    it('should set plot data with original categories when no range selection', () => {
        const mockData = createMockArrowData();

        const result = usePlotData({
            arrowData: mockData,
            rangeSelection: null
        });

        const data = get(result.data);
        expect(data).toEqual({
            x: mockData.x,
            y: mockData.y,
            category: mockData.fulfils_filter
        });
        expect(get(result.selectedSampleIds)).toEqual([]);
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

        // Based on our mock, first two points with category 1 should become 2
        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray[0]).toBe(2); // was 1, is selected
        expect(categoryArray[1]).toBe(2); // was 1, is selected
        expect(categoryArray[2]).toBe(0); // stays 0
        expect(categoryArray[3]).toBe(1); // stays 1 (not in selection range per mock)
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
        // Based on our mock, first two samples should be selected
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
