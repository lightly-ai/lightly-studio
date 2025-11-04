import { describe, it, expect, vi } from 'vitest';
import type { ArrowData } from '../useArrowData/useArrowData';

type Point = { x: number; y: number };

vi.mock('../isPointInPolygon/isPointInPolygon', () => ({
    isPointInPolygon: vi.fn()
}));

// Import after mock is set up
const { getCategoryBySelection } = await import('./getCategoryBySelection');
const { isPointInPolygon } = await import('../isPointInPolygon/isPointInPolygon');

describe('getCategoryBySelection', () => {
    const createMockArrowData = (): ArrowData => ({
        x: new Float32Array([1.0, 2.0, 3.0, 4.0]),
        y: new Float32Array([5.0, 6.0, 7.0, 8.0]),
        fulfils_filter: new Uint8Array([1, 1, 0, 1]),
        sample_id: ['sample1', 'sample2', 'sample3', 'sample4']
    });

    const mockSelection: Point[] = [
        { x: 0, y: 0 },
        { x: 3, y: 0 },
        { x: 3, y: 7 },
        { x: 0, y: 7 }
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should return prevValue when selection is null', () => {
        const mockData = createMockArrowData();
        const reducer = getCategoryBySelection(null, mockData);

        expect(reducer(1, 0)).toBe(1);
        expect(reducer(2, 1)).toBe(2);
        expect(reducer(0, 2)).toBe(0);
        expect(isPointInPolygon).not.toHaveBeenCalled();
    });

    it('should return prevValue when selection is undefined', () => {
        const mockData = createMockArrowData();
        const reducer = getCategoryBySelection(undefined as unknown as Point[] | null, mockData);

        expect(reducer(1, 0)).toBe(1);
        expect(reducer(2, 1)).toBe(2);
        expect(isPointInPolygon).not.toHaveBeenCalled();
    });

    it('should return 2 when prevValue is 1 and point is in selection', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(true);

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const result = reducer(1, 0);

        expect(result).toBe(2);
        expect(isPointInPolygon).toHaveBeenCalledWith(1.0, 5.0, mockSelection);
    });

    it('should return prevValue when prevValue is 1 but point is not in selection', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(false);

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const result = reducer(1, 0);

        expect(result).toBe(1);
        expect(isPointInPolygon).toHaveBeenCalledWith(1.0, 5.0, mockSelection);
    });

    it('should return prevValue when prevValue is 0 even if point is in selection', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(true);

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const result = reducer(0, 2);

        expect(result).toBe(0);
        expect(isPointInPolygon).toHaveBeenCalledWith(3.0, 7.0, mockSelection);
    });

    it('should return prevValue when prevValue is 2 even if point is in selection', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(true);

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const result = reducer(2, 1);

        expect(result).toBe(2);
        expect(isPointInPolygon).toHaveBeenCalledWith(2.0, 6.0, mockSelection);
    });

    it('should work correctly with array reduce for multiple points', () => {
        const mockData = createMockArrowData();
        // Mock: first two points are in selection, last two are not
        vi.mocked(isPointInPolygon)
            .mockReturnValueOnce(true) // index 0
            .mockReturnValueOnce(true) // index 1
            .mockReturnValueOnce(false) // index 2
            .mockReturnValueOnce(false); // index 3

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const categories = [1, 1, 1, 1];
        const result = categories.map(reducer);

        expect(result).toEqual([2, 2, 1, 1]);
        expect(isPointInPolygon).toHaveBeenCalledTimes(4);
    });

    it('should handle mixed prevValues correctly', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(true);

        const reducer = getCategoryBySelection(mockSelection, mockData);
        const categories = [0, 1, 2, 1];
        const result = categories.map(reducer);

        // Only prevValue=1 should change to 2
        expect(result).toEqual([0, 2, 2, 2]);
    });

    it('should use correct x and y coordinates from ArrowData', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(false);

        const reducer = getCategoryBySelection(mockSelection, mockData);

        reducer(1, 0);
        expect(isPointInPolygon).toHaveBeenCalledWith(1.0, 5.0, mockSelection);

        reducer(1, 1);
        expect(isPointInPolygon).toHaveBeenCalledWith(2.0, 6.0, mockSelection);

        reducer(1, 2);
        expect(isPointInPolygon).toHaveBeenCalledWith(3.0, 7.0, mockSelection);

        reducer(1, 3);
        expect(isPointInPolygon).toHaveBeenCalledWith(4.0, 8.0, mockSelection);
    });

    it('should handle empty selection array', () => {
        const mockData = createMockArrowData();
        vi.mocked(isPointInPolygon).mockReturnValue(false);

        const reducer = getCategoryBySelection([], mockData);
        const result = reducer(1, 0);

        expect(result).toBe(1);
        expect(isPointInPolygon).toHaveBeenCalledWith(1.0, 5.0, []);
    });
});
