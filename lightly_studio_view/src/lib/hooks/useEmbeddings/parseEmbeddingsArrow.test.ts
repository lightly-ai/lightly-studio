import { describe, it, expect, vi, beforeEach } from 'vitest';
import { parseEmbeddingsArrow } from './parseEmbeddingsArrow';
import { Table, tableFromIPC } from 'apache-arrow';

vi.mock('apache-arrow', () => ({
    tableFromIPC: vi.fn()
}));

describe('parseEmbeddingsArrow', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // Builds a getChild mock where color_categories behaves like an Arrow list<uint8> vector
    // (read row by row via get/length) and other columns expose a flat toArray().
    const createGetChild = (columns: Record<string, unknown>) =>
        vi.fn((col: string) => {
            if (col === 'color_categories') {
                const rows = columns[col] as number[][];
                return {
                    length: rows.length,
                    get: (row: number) => rows[row]
                };
            }
            return { toArray: () => columns[col] };
        });

    it('successfully reads Arrow data with all required columns', () => {
        const mockData = {
            x: [1, 2, 3],
            y: [4, 5, 6],
            fulfils_filter: [true, false, true],
            color_categories: [[2, 3], [2], []],
            sample_id: ['a', 'b', 'c']
        };

        const mockTable = {
            schema: {
                metadata: new Map([['color_legend', '{"2":"Train","3":"Validation"}']])
            },
            getChild: createGetChild(mockData)
        };

        vi.mocked(tableFromIPC).mockReturnValue(mockTable as unknown as Table);

        const { columns, legend } = parseEmbeddingsArrow(new ArrayBuffer(8));

        expect(columns).toEqual(mockData);
        expect(legend).toEqual(
            new Map([
                [2, 'Train'],
                [3, 'Validation']
            ])
        );
    });

    it('throws when a required column is missing', () => {
        const mockTable = {
            getChild: vi.fn((_col: string) => {
                if (_col === 'x') return null;
                return {
                    toArray: () => [1, 2, 3]
                };
            })
        };

        vi.mocked(tableFromIPC).mockReturnValue(mockTable as unknown as Table);

        const parse = () => parseEmbeddingsArrow(new ArrayBuffer(8));

        expect(parse).toThrow('Missing required column "x" in Arrow data.');
    });

    it('throws when tableFromIPC throws', () => {
        vi.mocked(tableFromIPC).mockImplementation(() => {
            throw new Error('Invalid Arrow format');
        });

        const parse = () => parseEmbeddingsArrow(new ArrayBuffer(8));

        expect(parse).toThrow('Invalid Arrow format');
    });

    it('handles empty blob', () => {
        const mockTable = {
            schema: {
                metadata: undefined
            },
            getChild: vi.fn(() => ({
                toArray: () => []
            }))
        };

        vi.mocked(tableFromIPC).mockReturnValue(mockTable as unknown as Table);

        const { columns, legend } = parseEmbeddingsArrow(new ArrayBuffer(0));

        expect(columns).toEqual({
            x: [],
            y: [],
            fulfils_filter: [],
            color_categories: [],
            sample_id: []
        });
        expect(legend).toEqual(new Map());
    });

    it('falls back to an empty color legend when metadata is malformed', () => {
        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const mockData = {
            x: [1, 2, 3],
            y: [4, 5, 6],
            fulfils_filter: [true, false, true],
            color_categories: [[2, 3], [2], []],
            sample_id: ['a', 'b', 'c']
        };
        const mockTable = {
            schema: {
                metadata: new Map([['color_legend', '{"2":"Train"']])
            },
            getChild: createGetChild(mockData)
        };

        vi.mocked(tableFromIPC).mockReturnValue(mockTable as unknown as Table);

        const { columns, legend } = parseEmbeddingsArrow(new ArrayBuffer(8));

        expect(columns).toEqual(mockData);
        expect(legend).toEqual(new Map());
        expect(warnSpy).toHaveBeenCalledWith(
            'Invalid color_legend metadata in Arrow data.',
            expect.any(SyntaxError)
        );
    });
});
