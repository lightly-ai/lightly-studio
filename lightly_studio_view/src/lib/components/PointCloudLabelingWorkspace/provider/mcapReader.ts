import { MessageReader } from '@foxglove/rosmsg2-serialization';
import { parse } from '@foxglove/rosmsg';
import { McapIndexedReader, type TypedMcapRecords } from '@mcap/core';
import { decompress } from 'lz4js';
import { ZSTDDecoder } from 'zstddec';
import { canonicalCoordinateFrame, assertCompatibleCoordinates } from '../domain';
import { fuseClouds } from './fuseClouds';
import { HttpRangeReadable } from './httpRangeReadable';
import { decodePointCloud2 } from './pointCloud2';
import { ProviderError } from './providerError';
import { frameIdentity, type FrameLocator, type McapSource } from './source';
import {
    buildTransformGraph,
    resolveTransforms,
    type TransformGraph,
    type TransformMessage
} from './transformTree';

type Channel = TypedMcapRecords['Channel'];

const maxChunkBytes = 64 * 1024 * 1024;
/** Where ROS 2 publishes the sensor extrinsics that place each lidar on the vehicle. */
const TF_STATIC_TOPIC = '/tf_static';
/**
 * How far from the anchor sweep another channel's sweep may sit and still be the same moment.
 *
 * Lidars on one vehicle are not triggered together, so their sweeps land milliseconds apart.
 * 50 ms is under one period at the 10 Hz these sensors run at, which is what makes "the
 * nearest sweep in the window" unambiguous.
 */
const FUSION_WINDOW_NS = 50_000_000n;
/** MCAP record framing: one opcode byte plus a little-endian u64 content length. */
const RECORD_HEADER_BYTES = 9;
const MESSAGE_INDEX_OPCODE = 0x07;
/** One message index entry: a u64 log time and a u64 offset into the chunk. */
const INDEX_ENTRY_BYTES = 16;

/** Indexed recording session; instantiated and used exclusively inside a worker. */
export async function openMcap(source: McapSource, signal: AbortSignal) {
    validateSource(source);
    const readable = new HttpRangeReadable(source, signal);
    const zstd = new ZSTDDecoder();
    const reader = await McapIndexedReader.Initialize({
        readable,
        decompressHandlers: decompressHandlers(zstd),
        messageIndexCacheSizeBytes: 8 * 1024 * 1024
    });
    if (reader.chunkIndexes.some((chunk) => chunk.uncompressedSize > BigInt(maxChunkBytes))) {
        throw new ProviderError(
            'limit',
            'The recording contains chunks larger than the memory limit.'
        );
    }
    // Only now, once the index says the recording actually uses Zstandard. The decoder
    // instantiates WebAssembly, which a recording of lz4-only chunks never needs, and which
    // must not be able to fail an open that would otherwise have succeeded.
    if (reader.chunkIndexes.some((chunk) => chunk.compression === 'zstd')) {
        await initZstd(zstd);
    }
    const topics = Array.from(reader.channelsById.values()).map((channel) => {
        const schema = reader.schemasById.get(channel.schemaId);
        return {
            channelId: channel.id,
            topic: channel.topic,
            schema: schema?.name ?? '',
            supported: isSupported(channel.messageEncoding, schema),
            messageCount:
                reader.statistics?.channelMessageCounts.get(channel.id)?.toString() ?? null
        };
    });
    const metadata = {
        topics,
        firstLogTimeNs: reader.statistics?.messageStartTime.toString() ?? null,
        lastLogTimeNs: reader.statistics?.messageEndTime.toString() ?? null
    };
    const decoders = new Map<number, MessageReader>();
    const lidarChannels = Array.from(reader.channelsById.values()).filter((channel) =>
        isSupported(channel.messageEncoding, reader.schemasById.get(channel.schemaId))
    );
    /** Read at most once per recording: extrinsics are static, and every frame needs them. */
    let publishedTransforms: Promise<TransformGraph> | undefined;

    async function loadFrame(locator: FrameLocator, pointBudget: number) {
        validateLocator(locator);
        const channel = reader.channelsById.get(locator.channelId);
        const schema = channel && reader.schemasById.get(channel.schemaId);
        if (!channel || !schema || !isSupported(channel.messageEncoding, schema)) {
            throw new ProviderError(
                'schema',
                'Select a ROS 2 CDR sensor_msgs/msg/PointCloud2 channel.'
            );
        }
        let occurrence = 0;
        for await (const message of reader.readMessages({
            topics: [channel.topic],
            startTime: BigInt(locator.logTimeNs),
            endTime: BigInt(locator.logTimeNs),
            validateCrcs: true
        })) {
            signal.throwIfAborted();
            if (message.channelId !== locator.channelId || occurrence++ !== locator.occurrence)
                continue;
            return fuseFrame(channel, message, locator, pointBudget);
        }
        throw new ProviderError(
            'source',
            'The requested point-cloud frame is missing from the recording.'
        );
    }

    /**
     * Builds one frame from every lidar channel, aligned into a single coordinate frame.
     *
     * A vehicle's sensors cover the scene between them, so reading only the channel a frame
     * is listed on leaves everything the other sensors saw empty. The anchor message still
     * decides the frame's identity, timestamp and stream, which keeps listing, navigation
     * and annotation identity unchanged by what is fused into it.
     */
    async function fuseFrame(
        channel: Channel,
        message: TypedMcapRecords['Message'],
        locator: FrameLocator,
        pointBudget: number
    ) {
        const budget = Math.max(1, Math.floor(pointBudget / lidarChannels.length));
        const anchor = decodeCloud(channel, message.data, budget);
        const siblings = await readSiblings(channel.id, message.logTime, budget);
        const { targetFrameId, transforms } = await alignment(anchor.frameId);
        const fused = fuseClouds([anchor, ...siblings], transforms);
        return {
            positions: fused.positions,
            sourcePointCount: fused.sourcePointCount,
            id: frameIdentity(source, locator),
            source: {
                recordingId: source.recordingId,
                streamId: String(channel.id),
                messageId: JSON.stringify([locator.logTimeNs, locator.occurrence]),
                publishedAt: {
                    nanoseconds: message.publishTime.toString(),
                    clockId: source.publishClockId
                }
            },
            timestamp: { nanoseconds: message.logTime.toString(), clockId: source.logClockId },
            coordinateFrame: canonicalCoordinateFrame(targetFrameId),
            cameras: []
        };
    }

    /** The sweep nearest the anchor's log time on each of the other lidar channels. */
    async function readSiblings(anchorChannelId: number, anchorTime: bigint, budget: number) {
        const others = lidarChannels.filter((channel) => channel.id !== anchorChannelId);
        if (others.length === 0) return [];
        const nearest = new Map<number, { delta: bigint; data: Uint8Array }>();
        for await (const message of reader.readMessages({
            topics: others.map((channel) => channel.topic),
            startTime: anchorTime > FUSION_WINDOW_NS ? anchorTime - FUSION_WINDOW_NS : 0n,
            endTime: anchorTime + FUSION_WINDOW_NS,
            validateCrcs: true
        })) {
            signal.throwIfAborted();
            if (!others.some((channel) => channel.id === message.channelId)) continue;
            const delta = absoluteDelta(message.logTime, anchorTime);
            const best = nearest.get(message.channelId);
            if (best && best.delta <= delta) continue;
            // Copied: the iterator hands out views over a chunk it is free to reuse.
            nearest.set(message.channelId, { delta, data: message.data.slice() });
        }
        // Decoded after the window closes, so a channel costs one decode however many of its
        // sweeps the window happened to hold.
        return Array.from(nearest, ([channelId, { data }]) =>
            decodeCloud(reader.channelsById.get(channelId)!, data, budget)
        );
    }

    /**
     * Resolves where each sensor frame sits, and which frame the fused points end up in.
     *
     * One lidar needs no transform at all, so a single-channel recording never reads
     * `/tf_static`. With several, the frame the caller asked for is the target when
     * `/tf_static` knows it, and the anchor's own frame otherwise -- a recording whose
     * vehicle frame is named differently still renders in a frame that is real, with
     * whatever other sensors resolve into it.
     */
    async function alignment(anchorFrameId: string) {
        const frameId = anchorFrameId || source.coordinateFrame.id;
        if (lidarChannels.length < 2) {
            return { targetFrameId: frameId, transforms: resolveTransforms(new Map(), frameId) };
        }
        const graph = await (publishedTransforms ??= readTransformGraph());
        const targetFrameId = graph.has(source.coordinateFrame.id)
            ? source.coordinateFrame.id
            : frameId;
        return { targetFrameId, transforms: resolveTransforms(graph, targetFrameId) };
    }

    async function readTransformGraph(): Promise<TransformGraph> {
        const channel = Array.from(reader.channelsById.values()).find(
            (candidate) => candidate.topic === TF_STATIC_TOPIC
        );
        if (!channel) {
            throw new ProviderError(
                'source',
                `This recording has ${lidarChannels.length} lidar channels but no ${TF_STATIC_TOPIC} saying where they sit, so they cannot be aligned into one scene.`
            );
        }
        const messages: TransformMessage[] = [];
        for await (const message of reader.readMessages({
            topics: [channel.topic],
            validateCrcs: true
        })) {
            signal.throwIfAborted();
            messages.push(decoderFor(channel).readMessage<TransformMessage>(message.data));
        }
        return buildTransformGraph(messages);
    }

    function decodeCloud(channel: Channel, data: Uint8Array, budget: number) {
        return decodePointCloud2(
            decoderFor(channel).readMessage<Parameters<typeof decodePointCloud2>[0]>(data),
            budget
        );
    }

    function decoderFor(channel: Channel): MessageReader {
        const existing = decoders.get(channel.id);
        if (existing) return existing;
        const schema = reader.schemasById.get(channel.schemaId);
        if (!schema || schema.encoding !== 'ros2msg') {
            throw new ProviderError(
                'schema',
                `The channel '${channel.topic}' does not carry a ros2msg schema to decode.`
            );
        }
        const created = messageReader(schema);
        decoders.set(channel.id, created);
        return created;
    }

    async function listFrames(
        channelId: number,
        startTimeNs: string,
        endTimeNs: string,
        limit = 1000
    ) {
        validateRange(channelId, startTimeNs, endTimeNs, limit);
        const start = BigInt(startTimeNs);
        const end = BigInt(endTimeNs);
        const frames: FrameLocator[] = [];
        let lastTime = '';
        let occurrence = 0;
        for (const chunk of chunksCovering(channelId, start, end)) {
            signal.throwIfAborted();
            for (const logTime of await readMessageTimes(chunk, channelId)) {
                if (logTime < start || logTime > end) continue;
                if (frames.length === limit) return { frames, truncated: true };
                const logTimeNs = logTime.toString();
                occurrence = logTimeNs === lastTime ? occurrence + 1 : 0;
                frames.push({ channelId, logTimeNs, occurrence });
                lastTime = logTimeNs;
            }
        }
        return { frames, truncated: false };
    }

    /**
     * Chunks whose time span overlaps the window and that carry this channel, in file order.
     *
     * Chunk indexes are already in memory from the summary, so narrowing by time costs
     * nothing and keeps the reads below proportional to the window rather than the recording.
     */
    function chunksCovering(channelId: number, start: bigint, end: bigint) {
        return reader.chunkIndexes
            .filter(
                (chunk) =>
                    chunk.messageEndTime >= start &&
                    chunk.messageStartTime <= end &&
                    chunk.messageIndexOffsets.has(channelId)
            )
            .sort((left, right) => Number(left.chunkStartOffset - right.chunkStartOffset));
    }

    /**
     * Reads one chunk's message index and returns this channel's log times, in order.
     *
     * The index region sits outside the chunk and is never compressed, so listing a window
     * reads a few kilobytes per chunk instead of decompressing the chunks themselves. That is
     * the whole point of doing this by hand rather than iterating messages and dropping their
     * payloads.
     */
    async function readMessageTimes(
        chunk: (typeof reader.chunkIndexes)[number],
        channelId: number
    ): Promise<bigint[]> {
        let regionStart: bigint | undefined;
        for (const offset of chunk.messageIndexOffsets.values()) {
            if (regionStart === undefined || offset < regionStart) regionStart = offset;
        }
        if (regionStart === undefined) return [];
        const region = await readable.read(regionStart, chunk.messageIndexLength);
        return parseMessageIndexTimes(region, channelId);
    }

    function validateRange(
        channelId: number,
        startTimeNs: string,
        endTimeNs: string,
        limit: number
    ) {
        validateLocator({ channelId, logTimeNs: startTimeNs, occurrence: 0 });
        validateLocator({ channelId, logTimeNs: endTimeNs, occurrence: 0 });
        const channel = reader.channelsById.get(channelId);
        if (
            !channel ||
            BigInt(startTimeNs) > BigInt(endTimeNs) ||
            !Number.isInteger(limit) ||
            limit < 1 ||
            limit > 1000
        ) {
            throw new ProviderError('source', 'The requested frame range is invalid.');
        }
        return channel;
    }

    return { metadata, loadFrame, listFrames, readable };
}

/**
 * Builds a CDR reader for a channel's schema.
 *
 * A real recording can carry a schema this parser rejects -- a concatenated definition
 * missing a referenced message type, most often -- which is a problem with the recording's
 * schema rather than with its payload, so it is reported as one.
 */
function messageReader(schema: { name: string; data: Uint8Array }): MessageReader {
    try {
        return new MessageReader(parse(new TextDecoder().decode(schema.data), { ros2: true }));
    } catch (error) {
        throw new ProviderError(
            'schema',
            `The schema '${schema.name}' on this channel could not be parsed.`,
            error instanceof Error ? `${error.name}: ${error.message}` : String(error)
        );
    }
}

/**
 * Extracts one channel's log times from a chunk's message index region.
 *
 * The region is a sequence of MCAP records: a one-byte opcode, a little-endian u64 content
 * length, then the content. A MessageIndex's content is the channel id, then a
 * length-prefixed array of (log time, offset) pairs, of which only the times are wanted.
 * `@mcap/core` parses these internally but exposes neither its reader nor the parsed
 * indexes, and its public path to them decompresses the chunk as well.
 */
function parseMessageIndexTimes(region: Uint8Array, channelId: number): bigint[] {
    const view = new DataView(region.buffer, region.byteOffset, region.byteLength);
    const times: bigint[] = [];
    let at = 0;
    while (at + RECORD_HEADER_BYTES <= region.byteLength) {
        const opcode = view.getUint8(at);
        const contentStart = at + RECORD_HEADER_BYTES;
        const contentEnd = contentStart + Number(view.getBigUint64(at + 1, true));
        if (contentEnd > region.byteLength || contentEnd <= contentStart) break;
        if (opcode === MESSAGE_INDEX_OPCODE && view.getUint16(contentStart, true) === channelId) {
            collectTimes(view, contentStart, times);
        }
        at = contentEnd;
    }
    return times.sort((left, right) => (left < right ? -1 : left > right ? 1 : 0));
}

function collectTimes(view: DataView, contentStart: number, times: bigint[]): void {
    const recordsStart = contentStart + 2 + 4;
    const recordsEnd = recordsStart + view.getUint32(contentStart + 2, true);
    for (let at = recordsStart; at + INDEX_ENTRY_BYTES <= recordsEnd; at += INDEX_ENTRY_BYTES) {
        times.push(view.getBigUint64(at, true));
    }
}

function absoluteDelta(left: bigint, right: bigint): bigint {
    return left > right ? left - right : right - left;
}

function isSupported(encoding: string, schema: { name: string; encoding: string } | undefined) {
    return (
        encoding === 'cdr' &&
        schema?.encoding === 'ros2msg' &&
        ['sensor_msgs/msg/PointCloud2', 'sensor_msgs/PointCloud2'].includes(schema.name)
    );
}

function validateSource(source: McapSource): void {
    if (!source.recordingId || !source.version || !source.logClockId || !source.publishClockId) {
        throw new ProviderError(
            'source',
            'Recording identity, version, and clock metadata are required.'
        );
    }
    assertCompatibleCoordinates(
        source.coordinateFrame,
        canonicalCoordinateFrame(source.coordinateFrame.id)
    );
}

function validateLocator(locator: FrameLocator): void {
    if (
        !/^\d+$/.test(locator.logTimeNs) ||
        BigInt(locator.logTimeNs) > 0xffffffffffffffffn ||
        !Number.isInteger(locator.channelId) ||
        locator.channelId < 0 ||
        locator.channelId > 65535 ||
        !Number.isSafeInteger(locator.occurrence) ||
        locator.occurrence < 0
    ) {
        throw new ProviderError(
            'source',
            'The frame channel, timestamp, or occurrence is invalid.'
        );
    }
}

async function initZstd(zstd: ZSTDDecoder): Promise<void> {
    try {
        await zstd.init();
    } catch (error) {
        throw new ProviderError(
            'corrupt',
            'The Zstandard decoder for this recording could not be started.',
            error instanceof Error ? `${error.name}: ${error.message}` : String(error)
        );
    }
}

function decompressHandlers(zstd: ZSTDDecoder) {
    const checked =
        (decode: (bytes: Uint8Array, size: number) => Uint8Array) =>
        (bytes: Uint8Array, size: bigint) => {
            if (size < 0n || size > BigInt(maxChunkBytes)) {
                throw new ProviderError(
                    'limit',
                    'The decompressed MCAP chunk exceeds the memory limit.'
                );
            }
            const result = decode(bytes, Number(size));
            if (result.length !== Number(size))
                throw new ProviderError('corrupt', 'The MCAP chunk is truncated.');
            return result;
        };
    return { lz4: checked(decompress), zstd: checked((bytes, size) => zstd.decode(bytes, size)) };
}
