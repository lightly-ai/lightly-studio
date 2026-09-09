import { describe, expect, it } from 'vitest';
import { decodePointCloud2 } from './pointCloud2';

function message(values = [1, 2, 3], bigEndian = false) {
    const data = new Uint8Array(values.length * 4);
    const view = new DataView(data.buffer);
    values.forEach((value, index) => view.setFloat32(index * 4, value, !bigEndian));
    return {
        width: values.length / 3,
        height: 1,
        point_step: 12,
        row_step: data.length,
        fields: ['x', 'y', 'z'].map((name, index) => ({
            name,
            offset: index * 4,
            datatype: 7,
            count: 1
        })),
        data,
        is_bigendian: bigEndian
    };
}

describe('decodePointCloud2', () => {
    it.each([true, false])('decodes coordinates with big-endian=%s', (bigEndian) => {
        expect(decodePointCloud2(message([1, -2, 3], bigEndian)).positions).toEqual(
            new Float32Array([1, -2, 3])
        );
    });

    it('handles row padding and filters non-finite points', () => {
        const input = message([1, 2, 3, 0, NaN, 4, 5, 0]);
        input.width = 1;
        input.height = 2;
        input.row_step = 16;
        expect(decodePointCloud2(input)).toEqual({
            positions: new Float32Array([1, 2, 3]),
            sourcePointCount: 2
        });
    });

    it('downsamples deterministically within the point budget', () => {
        const input = message([1, 2, 3, 4, 5, 6, 7, 8, 9]);
        expect(decodePointCloud2(input, 2)).toEqual({
            positions: new Float32Array([1, 2, 3, 7, 8, 9]),
            sourcePointCount: 3
        });
    });

    it('accepts empty clouds with declared fields', () => {
        expect(decodePointCloud2(message([])).positions.length).toBe(0);
    });

    it('rejects a malformed layout', () => {
        const input = message();
        expect(() => decodePointCloud2({ ...input, width: -1 })).toThrow(/layout is invalid/);
        expect(() => decodePointCloud2({ ...input, point_step: 1.5 })).toThrow(/layout is invalid/);
        expect(() => decodePointCloud2({ ...input, data: [] as unknown as Uint8Array })).toThrow(
            /layout is invalid/
        );
        expect(() =>
            decodePointCloud2({ ...input, fields: {} as unknown as typeof input.fields })
        ).toThrow(/layout is invalid/);
        expect(() =>
            decodePointCloud2({ ...input, is_bigendian: 0 as unknown as boolean })
        ).toThrow(/layout is invalid/);
    });

    it('rejects truncated data, invalid fields, and excessive budgets', () => {
        const input = message();
        expect(() => decodePointCloud2({ ...input, data: new Uint8Array(4) })).toThrow(
            /row layout/
        );
        expect(() => decodePointCloud2({ ...input, fields: input.fields.slice(1) })).toThrow(/'x'/);
        expect(() =>
            decodePointCloud2({ ...input, fields: input.fields.map((f) => ({ ...f, count: 2 })) })
        ).toThrow(/scalar/);
        expect(() => decodePointCloud2(input, 2_000_001)).toThrow(/point budget/);
    });
});
