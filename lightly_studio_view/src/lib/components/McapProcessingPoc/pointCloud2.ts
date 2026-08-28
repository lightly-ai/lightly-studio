interface PointField {
    name: string;
    offset: number;
    datatype: number;
    count: number;
}

export interface PointCloud2Message {
    height: number;
    width: number;
    fields: PointField[];
    is_bigendian: boolean;
    point_step: number;
    row_step: number;
    data: Uint8Array;
}

interface FieldReader {
    offset: number;
    read: (view: DataView, offset: number, littleEndian: boolean) => number;
}

const DATA_READERS: Record<number, FieldReader['read']> = {
    1: (view, offset) => view.getInt8(offset),
    2: (view, offset) => view.getUint8(offset),
    3: (view, offset, littleEndian) => view.getInt16(offset, littleEndian),
    4: (view, offset, littleEndian) => view.getUint16(offset, littleEndian),
    5: (view, offset, littleEndian) => view.getInt32(offset, littleEndian),
    6: (view, offset, littleEndian) => view.getUint32(offset, littleEndian),
    7: (view, offset, littleEndian) => view.getFloat32(offset, littleEndian),
    8: (view, offset, littleEndian) => view.getFloat64(offset, littleEndian)
};

export function decodePointCloud2(message: PointCloud2Message): Float32Array {
    const readers = makeReaders(message.fields);
    const pointCount = message.height * message.width;
    const output = new Float32Array(pointCount * 4);
    const view = new DataView(
        message.data.buffer,
        message.data.byteOffset,
        message.data.byteLength
    );
    const littleEndian = !message.is_bigendian;
    let outputIndex = 0;

    for (let index = 0; index < pointCount; index += 1) {
        const inputOffset = pointOffset(message, index);
        const point = readPoint(view, inputOffset, readers, littleEndian);
        if (
            !Number.isFinite(point[0]) ||
            !Number.isFinite(point[1]) ||
            !Number.isFinite(point[2])
        ) {
            continue;
        }
        output.set(point, outputIndex);
        outputIndex += 4;
    }
    return output.slice(0, outputIndex);
}

function makeReaders(fields: PointField[]): Record<string, FieldReader> {
    const byName = new Map(fields.map((field) => [field.name, field]));
    const readers: Record<string, FieldReader> = {};
    for (const name of ['x', 'y', 'z', 'intensity']) {
        const field =
            byName.get(name) ?? (name === 'intensity' ? byName.get('reflectivity') : undefined);
        if (!field) {
            if (name === 'intensity') continue;
            throw new Error(`PointCloud2 field '${name}' is required.`);
        }
        const read = DATA_READERS[field.datatype];
        if (!read) throw new Error(`PointCloud2 field '${name}' has unsupported datatype.`);
        readers[name] = { offset: field.offset, read };
    }
    return readers;
}

function pointOffset(message: PointCloud2Message, index: number): number {
    const row = Math.floor(index / message.width);
    const column = index % message.width;
    return row * message.row_step + column * message.point_step;
}

function readPoint(
    view: DataView,
    offset: number,
    readers: Record<string, FieldReader>,
    littleEndian: boolean
): [number, number, number, number] {
    const read = (name: string): number => {
        const field = readers[name];
        return field ? field.read(view, offset + field.offset, littleEndian) : 0;
    };
    return [read('x'), read('y'), read('z'), read('intensity')];
}
