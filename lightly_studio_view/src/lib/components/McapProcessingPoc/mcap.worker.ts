/// <reference lib="webworker" />

import { MessageReader } from '@foxglove/rosmsg2-serialization';
import { parse } from '@foxglove/rosmsg';
import { McapIndexedReader } from '@mcap/core';
import { decompress } from 'lz4js';
import { ZSTDDecoder } from 'zstddec';
import { HttpRangeReadable } from './httpRangeReadable';
import { decodePointCloud2, type PointCloud2Message } from './pointCloud2';
import type { WorkerRequest, WorkerSuccess } from './types';

interface OpenSource {
    url: string;
    sizeBytes: number;
    reader: McapIndexedReader;
    readable: HttpRangeReadable;
    messageReaders: Map<number, MessageReader<PointCloud2Message>>;
}

let openSource: OpenSource | undefined;
let zstdDecoder: ZSTDDecoder | undefined;

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
    try {
        const result = await readFrame(event.data);
        self.postMessage(result, { transfer: [result.points] });
    } catch (error) {
        self.postMessage({
            requestId: event.data.requestId,
            error: error instanceof Error ? error.message : String(error)
        });
    }
};

async function readFrame(request: WorkerRequest): Promise<WorkerSuccess> {
    const startedAt = performance.now();
    const cached = matchesOpenSource(request);
    const source = cached ? openSource! : await openReader(request);
    openSource = source;
    const indexMs = cached ? 0 : performance.now() - startedAt;
    source.readable.resetCounts();

    const decodeStartedAt = performance.now();
    const message = await firstMessage(source.reader, request);
    const decoded = messageReaderFor(source, message.channelId).readMessage(message.data);
    const points = decodePointCloud2(decoded);
    const now = performance.now();
    return {
        requestId: request.requestId,
        points: points.buffer as ArrayBuffer,
        pointCount: points.length / 4,
        logTimeNs: message.logTime.toString(),
        metrics: {
            totalMs: now - startedAt,
            processingMs: now - startedAt,
            indexMs,
            decodeMs: now - decodeStartedAt,
            bytesRead: source.readable.bytesRead,
            requestCount: source.readable.requestCount,
            indexCached: cached
        }
    };
}

function matchesOpenSource(request: WorkerRequest): boolean {
    return openSource?.url === request.url && openSource.sizeBytes === request.sizeBytes;
}

async function openReader(request: WorkerRequest): Promise<OpenSource> {
    const readable = new HttpRangeReadable(request.url, BigInt(request.sizeBytes));
    const reader = await McapIndexedReader.Initialize({
        readable,
        decompressHandlers: await decompressHandlers()
    });
    return {
        url: request.url,
        sizeBytes: request.sizeBytes,
        reader,
        readable,
        messageReaders: new Map()
    };
}

async function decompressHandlers() {
    if (!zstdDecoder) {
        const decoder = new ZSTDDecoder();
        await decoder.init();
        zstdDecoder = decoder;
    }
    const zstd = zstdDecoder;
    return {
        lz4: (buffer: Uint8Array, size: bigint) => decompress(buffer, Number(size)),
        zstd: (buffer: Uint8Array, size: bigint) => zstd.decode(buffer, Number(size))
    };
}

function messageReaderFor(
    source: OpenSource,
    channelId: number
): MessageReader<PointCloud2Message> {
    const existing = source.messageReaders.get(channelId);
    if (existing) return existing;
    const channel = source.reader.channelsById.get(channelId);
    const schema = channel ? source.reader.schemasById.get(channel.schemaId) : undefined;
    if (!channel || !schema || channel.messageEncoding !== 'cdr' || schema.encoding !== 'ros2msg') {
        throw new Error('The selected topic must use a ROS 2 CDR PointCloud2 schema.');
    }
    const definitions = parse(new TextDecoder().decode(schema.data), { ros2: true });
    const created = new MessageReader<PointCloud2Message>(definitions);
    source.messageReaders.set(channelId, created);
    return created;
}

async function firstMessage(reader: McapIndexedReader, request: WorkerRequest) {
    const messages = reader.readMessages({
        topics: [request.topic],
        startTime: BigInt(request.timestampNs)
    });
    const result = await messages.next();
    if (result.done) throw new Error('No point-cloud frame exists at or after the timestamp.');
    return result.value;
}
