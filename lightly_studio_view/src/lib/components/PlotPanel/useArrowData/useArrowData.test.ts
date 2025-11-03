import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useArrowData } from './useArrowData';
import { Table, tableFromIPC } from 'apache-arrow';

vi.mock('apache-arrow', () => ({
    tableFromIPC: vi.fn()
}));

describe('useArrowData', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('successfully reads Arrow data with all required columns', async () => {
        const mockData = {
            x: [1, 2, 3],
            y: [4, 5, 6],
            fulfils_filter: [true, false, true],
            sample_id: ['a', 'b', 'c']
        };

        const mockTable = {
            getChild: vi.fn((col: string) => ({
                toArray: () => mockData[col as keyof typeof mockData]
            }))
        };

        vi.mocked(tableFromIPC).mockResolvedValue(mockTable as unknown as Table);

        const mockBlob = {
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8))
        } as Blob;
        const { data, error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(data)).toEqual(mockData);
        expect(get(error)).toBeUndefined();
    });

    it('sets error when table is null', async () => {
        vi.mocked(tableFromIPC).mockResolvedValue(null as unknown as Table);

        const mockBlob = {
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8))
        } as Blob;
        const { data, error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(data)).toBeUndefined();
        expect(get(error)).toBe('Failed to read Arrow table from embeddings data.');
    });

    it('sets error when required column is missing', async () => {
        const mockTable = {
            getChild: vi.fn((_col: string) => {
                if (_col === 'x') return null;
                return {
                    toArray: () => [1, 2, 3]
                };
            })
        };

        vi.mocked(tableFromIPC).mockResolvedValue(mockTable as unknown as Table);

        const mockBlob = {
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8))
        } as Blob;
        const { error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(error)).toBe('Missing required column "x" in Arrow data.');
    });

    it('sets error when arrayBuffer conversion fails', async () => {
        const mockBlob = {
            arrayBuffer: vi.fn().mockRejectedValue(new Error('Failed to read blob'))
        } as Blob;

        const { data, error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(data)).toBeUndefined();
        expect(get(error)).toBe('Error reading Arrow data: Error: Failed to read blob');
    });

    it('sets error when tableFromIPC throws', async () => {
        vi.mocked(tableFromIPC).mockRejectedValue(new Error('Invalid Arrow format'));

        const mockBlob = {
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8))
        } as Blob;
        const { data, error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(data)).toBeUndefined();
        expect(get(error)).toBe('Error reading Arrow data: Error: Invalid Arrow format');
    });

    it('handles empty blob', async () => {
        const mockTable = {
            getChild: vi.fn(() => ({
                toArray: () => []
            }))
        };

        vi.mocked(tableFromIPC).mockResolvedValue(mockTable as unknown as Table);

        const mockBlob = {
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(0))
        } as Blob;
        const { data, error } = useArrowData({ blobData: mockBlob });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(data)).toEqual({
            x: [],
            y: [],
            fulfils_filter: [],
            sample_id: []
        });
        expect(get(error)).toBeUndefined();
    });

    it('returns writable stores that can be subscribed to', () => {
        const mockBlob = new Blob([new ArrayBuffer(8)]);
        const { data, error } = useArrowData({ blobData: mockBlob });

        expect(typeof data.subscribe).toBe('function');
        expect(typeof error.subscribe).toBe('function');
    });
});
