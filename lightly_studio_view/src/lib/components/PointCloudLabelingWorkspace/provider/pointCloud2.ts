import { ProviderError } from './providerError';

interface PointField {
    name: string;
    offset: number;
    datatype: number;
    count: number;
}

interface PointCloud2Message {
    height: number;
    width: number;
    fields: PointField[];
    is_bigendian: boolean;
    point_step: number;
    row_step: number;
    data: Uint8Array;
}

type ReadScalar = (view: DataView, offset: number, littleEndian: boolean) => number;
const scalarTypes: Record<number, { bytes: number; read: ReadScalar }> = {
    1: { bytes: 1, read: (v, o) => v.getInt8(o) },
    2: { bytes: 1, read: (v, o) => v.getUint8(o) },
    3: { bytes: 2, read: (v, o, le) => v.getInt16(o, le) },
    4: { bytes: 2, read: (v, o, le) => v.getUint16(o, le) },
    5: { bytes: 4, read: (v, o, le) => v.getInt32(o, le) },
    6: { bytes: 4, read: (v, o, le) => v.getUint32(o, le) },
    7: { bytes: 4, read: (v, o, le) => v.getFloat32(o, le) },
    8: { bytes: 8, read: (v, o, le) => v.getFloat64(o, le) }
};

/** Decode ROS PointCloud2 in its declared sensor frame; no implicit axes conversion. */
export function decodePointCloud2(message: PointCloud2Message, pointBudget = 350_000) {
    validateLayout(message, pointBudget);
    const readers = ['x', 'y', 'z'].map((name) => fieldReader(message, name));
    const sourcePointCount = message.width * message.height;
    const stride = Math.max(1, Math.ceil(sourcePointCount / pointBudget));
    const positions = new Float32Array(Math.ceil(sourcePointCount / stride) * 3);
    const view = new DataView(
        message.data.buffer,
        message.data.byteOffset,
        message.data.byteLength
    );
    let length = 0;
    for (let index = 0; index < sourcePointCount; index += stride) {
        const offset =
            Math.floor(index / message.width) * message.row_step +
            (index % message.width) * message.point_step;
        const point = readers.map((read) => Math.fround(read(view, offset, !message.is_bigendian)));
        if (!point.every(Number.isFinite)) continue;
        positions.set(point, length);
        length += 3;
    }
    return { positions: positions.slice(0, length), sourcePointCount };
}

function validateShape(message: PointCloud2Message): void {
    const dimensions = [message.width, message.height, message.point_step, message.row_step];
    if (
        !dimensions.every((value) => Number.isSafeInteger(value) && value >= 0) ||
        !(message.data instanceof Uint8Array) ||
        !Array.isArray(message.fields) ||
        typeof message.is_bigendian !== 'boolean'
    ) {
        throw new ProviderError('corrupt', 'The PointCloud2 layout is invalid.');
    }
}

function validateLayout(message: PointCloud2Message, budget: number): void {
    validateShape(message);
    if (!Number.isSafeInteger(budget) || budget < 1 || budget > 2_000_000) {
        throw new ProviderError('limit', 'The point budget must be between 1 and 2,000,000.');
    }
    if (
        message.row_step < message.width * message.point_step ||
        message.data.byteLength !== message.row_step * message.height ||
        !Number.isSafeInteger(message.width * message.height)
    ) {
        throw new ProviderError('corrupt', 'The PointCloud2 data does not match its row layout.');
    }
}

function fieldReader(message: PointCloud2Message, name: string): ReadScalar {
    const fields = message.fields.filter((field) => field.name === name);
    const field = fields[0];
    const scalar = field && scalarTypes[field.datatype];
    if (
        fields.length !== 1 ||
        !scalar ||
        field.count !== 1 ||
        !Number.isSafeInteger(field.offset) ||
        field.offset < 0 ||
        field.offset + scalar.bytes > message.point_step
    ) {
        throw new ProviderError('fields', `PointCloud2 requires one valid scalar '${name}' field.`);
    }
    return (view, offset, littleEndian) => scalar.read(view, offset + field.offset, littleEndian);
}
