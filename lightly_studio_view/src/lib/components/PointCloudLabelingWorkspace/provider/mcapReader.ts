import { MessageReader } from '@foxglove/rosmsg2-serialization';
import { parse } from '@foxglove/rosmsg';
import { McapIndexedReader } from '@mcap/core';
import { decompress } from 'lz4js';
import { ZSTDDecoder } from 'zstddec';
import { canonicalCoordinateFrame, assertCompatibleCoordinates } from '../domain';
import { HttpRangeReadable } from './httpRangeReadable';
import { decodePointCloud2 } from './pointCloud2';
import { ProviderError } from './providerError';
import { frameIdentity, type FrameLocator, type McapSource } from './source';

const maxChunkBytes = 64 * 1024 * 1024;

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
    const decoders = new Map<number, MessageReader<Parameters<typeof decodePointCloud2>[0]>>();

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
            let decoder = decoders.get(channel.id);
            if (!decoder) {
                decoder = messageReader(schema);
                decoders.set(channel.id, decoder);
            }
            const decoded = decodePointCloud2(decoder.readMessage(message.data), pointBudget);
            return {
                ...decoded,
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
                coordinateFrame: source.coordinateFrame,
                cameras: []
            };
        }
        throw new ProviderError(
            'source',
            'The requested point-cloud frame is missing from the recording.'
        );
    }

    async function listFrames(
        channelId: number,
        startTimeNs: string,
        endTimeNs: string,
        limit = 1000
    ) {
        const channel = validateRange(channelId, startTimeNs, endTimeNs, limit);
        const frames: FrameLocator[] = [];
        let lastTime = '';
        let occurrence = 0;
        for await (const message of reader.readMessages({
            topics: [channel.topic],
            startTime: BigInt(startTimeNs),
            endTime: BigInt(endTimeNs)
        })) {
            signal.throwIfAborted();
            if (message.channelId !== channelId) continue;
            if (frames.length === limit) return { frames, truncated: true };
            const logTimeNs = message.logTime.toString();
            occurrence = logTimeNs === lastTime ? occurrence + 1 : 0;
            frames.push({ channelId, logTimeNs, occurrence });
            lastTime = logTimeNs;
        }
        return { frames, truncated: false };
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
function messageReader(schema: { name: string; data: Uint8Array }) {
    try {
        return new MessageReader<Parameters<typeof decodePointCloud2>[0]>(
            parse(new TextDecoder().decode(schema.data), { ros2: true })
        );
    } catch (error) {
        throw new ProviderError(
            'schema',
            `The schema '${schema.name}' on this channel could not be parsed.`,
            error instanceof Error ? `${error.name}: ${error.message}` : String(error)
        );
    }
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
