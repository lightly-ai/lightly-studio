import type { CameraFrame } from '../domain';
import type { CameraEncoding } from './cameraChannels';
import {
    decodeCompressedImage,
    decodeRawImage,
    type CompressedImageMessage,
    type RawImageMessage
} from './cameraImages';
import { chunksForTarget, type VideoChunk } from './videoChunks';
import { createVideoStream } from './videoStream';

export interface CameraChannel {
    readonly channelId: number;
    readonly topic: string;
    readonly encoding: CameraEncoding;
}

/** One message off a camera channel, already decoded from CDR. */
export interface CameraMessage {
    readonly logTimeNs: bigint;
    readonly publishTimeNs: bigint;
    readonly value: unknown;
}

/** A picture, and the id the frame refers to it by. */
export interface CameraImage {
    readonly resourceId: string;
    readonly bitmap: ImageBitmap;
}

export interface CameraReaderOptions {
    /** Reads one channel's messages in a window, oldest first. */
    readonly readWindow: (
        channel: CameraChannel,
        startNs: bigint,
        endNs: bigint
    ) => Promise<readonly CameraMessage[]>;
    readonly recordingId: string;
    readonly logClockId: string;
    readonly publishClockId: string;
    /** Width pictures are handed back at. */
    readonly maxWidth: number;
    /** How far from a moment a still may sit and still belong to it. */
    readonly stillWindowNs: bigint;
    /** How far back a video picture's keyframe is looked for. */
    readonly videoLookbackNs: bigint;
}

/**
 * Reads the picture each camera was showing at a moment.
 *
 * Video decoders are kept per channel rather than per call: a recording is stepped and played
 * through in order, and a decoder that remembers its place turns each step into one picture
 * decoded instead of a whole group replayed. Close the reader to release them.
 *
 * A camera that cannot produce a picture for a moment is left out of the result rather than
 * failing the frame: a still that has not been published yet, a group of pictures whose
 * keyframe is outside the window, and a codec the browser will not decode are all ordinary
 * on a real recording, and none of them is a reason to show no point cloud.
 */
export function createCameraReader(options: CameraReaderOptions) {
    const streams = new Map<number, ReturnType<typeof createVideoStream>>();

    async function read(
        channels: readonly CameraChannel[],
        atLogTimeNs: bigint
    ): Promise<{ cameras: CameraFrame[]; images: CameraImage[] }> {
        const results = await Promise.all(
            channels.map((channel) => readChannel(channel, atLogTimeNs).catch(() => null))
        );
        const found = results.filter((result) => result !== null);
        return {
            cameras: found.map((result) => result.camera),
            images: found.map((result) => result.image)
        };
    }

    async function readChannel(channel: CameraChannel, atLogTimeNs: bigint) {
        const picture =
            channel.encoding === 'compressed-video'
                ? await readVideo(channel, atLogTimeNs)
                : await readStill(channel, atLogTimeNs);
        if (!picture) return null;
        const resourceId = `${channel.channelId}:${picture.message.logTimeNs}`;
        return {
            camera: toCameraFrame(channel, picture.message, picture.bitmap, resourceId),
            image: { resourceId, bitmap: picture.bitmap }
        };
    }

    async function readVideo(channel: CameraChannel, atLogTimeNs: bigint) {
        const messages = await options.readWindow(
            channel,
            atLogTimeNs > options.videoLookbackNs ? atLogTimeNs - options.videoLookbackNs : 0n,
            atLogTimeNs
        );
        if (messages.length === 0) return null;
        const format = (messages[messages.length - 1].value as { format?: string }).format ?? '';
        const chunks: VideoChunk[] = messages.map((message) => ({
            logTimeNs: message.logTimeNs,
            data: (message.value as { data: Uint8Array }).data
        }));
        const slice = chunksForTarget(chunks, atLogTimeNs, format);
        if (slice.length === 0) return null;

        let stream = streams.get(channel.channelId);
        if (!stream) {
            stream = createVideoStream(format, options.maxWidth);
            streams.set(channel.channelId, stream);
        }
        const bitmap = await stream.decode(slice);
        if (!bitmap) return null;
        const shown = slice[slice.length - 1].logTimeNs;
        const message = messages.find((candidate) => candidate.logTimeNs === shown)!;
        return { bitmap, message };
    }

    async function readStill(channel: CameraChannel, atLogTimeNs: bigint) {
        const messages = await options.readWindow(
            channel,
            atLogTimeNs > options.stillWindowNs ? atLogTimeNs - options.stillWindowNs : 0n,
            atLogTimeNs + options.stillWindowNs
        );
        const message = nearest(messages, atLogTimeNs);
        if (!message) return null;
        const bitmap =
            channel.encoding === 'raw-image'
                ? await decodeRawImage(message.value as RawImageMessage, options.maxWidth)
                : await decodeCompressedImage(
                      message.value as CompressedImageMessage,
                      options.maxWidth
                  );
        return { bitmap, message };
    }

    function toCameraFrame(
        channel: CameraChannel,
        message: CameraMessage,
        bitmap: ImageBitmap,
        resourceId: string
    ): CameraFrame {
        return {
            id: channel.topic,
            source: {
                recordingId: options.recordingId,
                streamId: String(channel.channelId),
                messageId: message.logTimeNs.toString(),
                publishedAt: {
                    nanoseconds: message.publishTimeNs.toString(),
                    clockId: options.publishClockId
                }
            },
            timestamp: {
                nanoseconds: message.logTimeNs.toString(),
                clockId: options.logClockId
            },
            // The delivered picture's size, which is the strip's width rather than the
            // sensor's: projecting a cuboid into one has to scale its intrinsics to match.
            width: bitmap.width,
            height: bitmap.height,
            image: { kind: 'decoded', resourceId },
            // Calibration comes from the recording's camera_info, which nothing reads yet.
            calibration: null
        };
    }

    return { read, close: () => streams.forEach((stream) => stream.close()) };
}

function nearest(
    messages: readonly CameraMessage[],
    atLogTimeNs: bigint
): CameraMessage | undefined {
    let best: CameraMessage | undefined;
    let bestDelta = 0n;
    for (const message of messages) {
        const delta =
            message.logTimeNs > atLogTimeNs
                ? message.logTimeNs - atLogTimeNs
                : atLogTimeNs - message.logTimeNs;
        if (best === undefined || delta < bestDelta) {
            best = message;
            bestDelta = delta;
        }
    }
    return best;
}
