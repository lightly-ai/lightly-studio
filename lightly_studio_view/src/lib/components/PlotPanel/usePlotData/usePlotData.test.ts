import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import type { ArrowData } from '../useArrowData/useArrowData';

type Point = { x: number; y: number };

vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: vi.fn()
}));

vi.mock('../getCategoryBySelection/getCategoryBySelection', () => ({
    getCategoryBySelection: vi.fn((selection) => (prevValue: number, index: number) => {
        if (!selection) return prevValue;
        return index < 2 ? prevValue : 0;
    })
}));

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

        const categoryArray = Array.from(data?.category as Uint8Array);
        expect(categoryArray[0]).toBe(1);
        expect(categoryArray[1]).toBe(1);
        expect(categoryArray[2]).toBe(0);
        expect(categoryArray[3]).toBe(0);
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
