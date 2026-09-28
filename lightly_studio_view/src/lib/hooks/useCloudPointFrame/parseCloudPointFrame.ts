import { tableFromIPC, type Table } from 'apache-arrow';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CloudPointFrame } from './types';

interface CloudPointFrameSource {
    channelId: number;
    timestampNs: string;
}

export async function parseCloudPointFrame(
    buffer: ArrayBuffer,
    source: CloudPointFrameSource
): Promise<CloudPointFrame> {
    const table = await tableFromIPC(new Uint8Array(buffer));
    const batch = packBatch(table);
    return buildFrame(table, batch, source);
}

function packBatch(table: Table): PointBatch {
    const x = table.getChild('x')?.toArray();
    const y = table.getChild('y')?.toArray();
    const z = table.getChild('z')?.toArray();
    if (!x || !y || !z || x.length !== y.length || x.length !== z.length) {
        throw new Error('Point-cloud Arrow data must contain matching x, y, and z columns.');
    }
    const intensity = table.getChild('intensity')?.toArray();
    const red = table.getChild('r')?.toArray();
    const green = table.getChild('g')?.toArray();
    const blue = table.getChild('b')?.toArray();
    if (Boolean(red) !== Boolean(green) || Boolean(red) !== Boolean(blue)) {
        throw new Error('Point-cloud Arrow data must contain all or none of r, g, and b columns.');
    }
    const positions = new Float32Array(x.length * 3);
    const intensities = new Float32Array(x.length);
    const colors = red && green && blue ? new Float32Array(x.length * 3) : undefined;
    for (let index = 0; index < x.length; index++) {
        positions[index * 3] = Number(x[index]);
        positions[index * 3 + 1] = Number(y[index]);
        positions[index * 3 + 2] = Number(z[index]);
        intensities[index] = intensity ? Number(intensity[index]) : 0;
        if (colors && red && green && blue) {
            colors[index * 3] = Number(red[index]);
            colors[index * 3 + 1] = Number(green[index]);
            colors[index * 3 + 2] = Number(blue[index]);
        }
    }
    return { positions, intensities, ...(colors ? { colors } : {}), count: x.length };
}

function buildFrame(
    table: Table,
    batch: PointBatch,
    source: CloudPointFrameSource
): CloudPointFrame {
    const metadata = table.schema.metadata;
    const boundsText = readMetadata(metadata, 'bounds');
    const timestampNs = readMetadata(metadata, 'log_time_ns') ?? source.timestampNs;
    const frameId = readMetadata(metadata, 'frame_id') ?? '';
    return {
        batch,
        channelId: source.channelId,
        timestampNs,
        frameId,
        sourcePointCount: Number(readMetadata(metadata, 'source_point_count') ?? batch.count),
        bounds: boundsText ? JSON.parse(boundsText) : null,
        channels: [{ channelId: source.channelId, timestampNs, frameId }]
    };
}

function readMetadata(
    metadata: Map<string, string | Uint8Array> | undefined,
    key: string
): string | undefined {
    const value = metadata?.get(key);
    return value instanceof Uint8Array ? new TextDecoder().decode(value) : value;
}
