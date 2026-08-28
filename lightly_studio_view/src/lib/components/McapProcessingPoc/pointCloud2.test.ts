import { describe, expect, it } from 'vitest';
import { decodePointCloud2, type PointCloud2Message } from './pointCloud2';

describe('decodePointCloud2', () => {
    it('decodes XYZI and removes non-finite points', () => {
        const data = new ArrayBuffer(32);
        const view = new DataView(data);
        [1, 2, 3, 4, Number.NaN, 6, 7, 8].forEach((value, index) =>
            view.setFloat32(index * 4, value, true)
        );

        const result = decodePointCloud2(message(new Uint8Array(data), 2));

        expect([...result]).toEqual([1, 2, 3, 4]);
    });

    it('uses reflectivity when intensity is absent', () => {
        const data = new ArrayBuffer(16);
        const view = new DataView(data);
        [1, 2, 3].forEach((value, index) => view.setFloat32(index * 4, value, true));
        view.setUint8(12, 42);
        const value = message(new Uint8Array(data), 1);
        value.fields[3] = { name: 'reflectivity', offset: 12, datatype: 2, count: 1 };

        expect([...decodePointCloud2(value)]).toEqual([1, 2, 3, 42]);
    });

    it('rejects a missing coordinate field', () => {
        const value = message(new Uint8Array(16), 1);
        value.fields = value.fields.filter((field) => field.name !== 'z');

        expect(() => decodePointCloud2(value)).toThrow("PointCloud2 field 'z' is required.");
    });
});

function message(data: Uint8Array, width: number): PointCloud2Message {
    return {
        height: 1,
        width,
        fields: [
            { name: 'x', offset: 0, datatype: 7, count: 1 },
            { name: 'y', offset: 4, datatype: 7, count: 1 },
            { name: 'z', offset: 8, datatype: 7, count: 1 },
            { name: 'intensity', offset: 12, datatype: 7, count: 1 }
        ],
        is_bigendian: false,
        point_step: 16,
        row_step: width * 16,
        data
    };
}
