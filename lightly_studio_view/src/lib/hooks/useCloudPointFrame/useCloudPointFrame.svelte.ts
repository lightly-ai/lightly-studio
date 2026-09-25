import { tableFromIPC } from 'apache-arrow';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';

export interface CloudPointFrame {
    batch: PointBatch;
    channelId: number;
    timestampNs: string;
    frameId: string;
    sourcePointCount: number;
    bounds: { min: [number, number, number]; max: [number, number, number] } | null;
    channels: Array<{ channelId: number; timestampNs: string; frameId: string }>;
}

export interface CloudPointChannelLocator {
    channelId: number;
    timestampNs: string;
}

interface CloudPointFrameParams {
    datasetId: string;
    recordingId: string;
    channels: CloudPointChannelLocator[];
}

export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): { query: CreateQueryResult<CloudPointFrame, Error> } => {
    const query = createQuery(() => {
        const { datasetId, recordingId, channels } = getParams();
        return {
            queryKey: ['cloud-point-frame', datasetId, recordingId, channels],
            enabled: Boolean(datasetId && recordingId && channels.length),
            queryFn: async ({ signal }): Promise<CloudPointFrame> => {
                const frames = await Promise.all(
                    channels.map(async ({ channelId, timestampNs }) => {
                        const baseUrl = (
                            client.getConfig().baseUrl ?? `${globalThis.location.origin}/`
                        ).replace(/\/$/, '');
                        const url = new URL(
                            `${baseUrl}/datasets/${encodeURIComponent(datasetId)}` +
                                `/recordings/${encodeURIComponent(recordingId)}/point-cloud`
                        );
                        url.search = new URLSearchParams({
                            channel_id: String(channelId),
                            timestamp_ns: timestampNs
                        }).toString();
                        const response = await fetch(url, { signal });
                        if (!response.ok) {
                            throw new Error(`Could not load point cloud (${response.status}).`);
                        }
                        return parseCloudPointFrame(await response.arrayBuffer(), {
                            channelId,
                            timestampNs
                        });
                    })
                );
                return mergeCloudPointFrames(frames);
            }
        };
    });
    return { query };
};

export async function parseCloudPointFrame(
    buffer: ArrayBuffer,
    source: { channelId: number; timestampNs: string }
): Promise<CloudPointFrame> {
    const table = await tableFromIPC(new Uint8Array(buffer));
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
    const metadata = table.schema.metadata;
    const boundsText = readMetadata(metadata, 'bounds');
    const timestampNs = readMetadata(metadata, 'log_time_ns') ?? source.timestampNs;
    const frameId = readMetadata(metadata, 'frame_id') ?? '';
    return {
        batch: { positions, intensities, ...(colors ? { colors } : {}), count: x.length },
        channelId: source.channelId,
        timestampNs,
        frameId,
        sourcePointCount: Number(readMetadata(metadata, 'source_point_count') ?? x.length),
        bounds: boundsText ? JSON.parse(boundsText) : null,
        channels: [{ channelId: source.channelId, timestampNs, frameId }]
    };
}

function mergeCloudPointFrames(frames: CloudPointFrame[]): CloudPointFrame {
    const pointCount = frames.reduce((total, frame) => total + frame.batch.count, 0);
    const positions = new Float32Array(pointCount * 3);
    const intensities = new Float32Array(pointCount);
    const hasColors = frames.every((frame) => frame.batch.colors);
    const colors = hasColors ? new Float32Array(pointCount * 3) : undefined;
    let pointOffset = 0;
    for (const frame of frames) {
        positions.set(frame.batch.positions, pointOffset * 3);
        intensities.set(frame.batch.intensities, pointOffset);
        if (colors && frame.batch.colors) colors.set(frame.batch.colors, pointOffset * 3);
        pointOffset += frame.batch.count;
    }
    const bounds = mergeBounds(frames.map((frame) => frame.bounds));
    const first = frames[0];
    return {
        batch: { positions, intensities, ...(colors ? { colors } : {}), count: pointCount },
        channelId: first.channelId,
        timestampNs: first.timestampNs,
        frameId: frames.map((frame) => frame.frameId).join(','),
        sourcePointCount: frames.reduce((total, frame) => total + frame.sourcePointCount, 0),
        bounds,
        channels: frames.flatMap((frame) => frame.channels)
    };
}

function mergeBounds(bounds: Array<CloudPointFrame['bounds']>): CloudPointFrame['bounds'] {
    const available = bounds.filter((item) => item !== null);
    if (available.length === 0) return null;
    return {
        min: [0, 1, 2].map((axis) => Math.min(...available.map((item) => item.min[axis]))) as [
            number,
            number,
            number
        ],
        max: [0, 1, 2].map((axis) => Math.max(...available.map((item) => item.max[axis]))) as [
            number,
            number,
            number
        ]
    };
}

function readMetadata(
    metadata: Map<string, string | Uint8Array> | undefined,
    key: string
): string | undefined {
    const value = metadata?.get(key);
    return value instanceof Uint8Array ? new TextDecoder().decode(value) : value;
}
