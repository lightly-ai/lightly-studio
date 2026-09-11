import { ProviderError } from './providerError';
import type { VideoChunk } from './videoChunks';

/** WebCodecs names for the formats a CompressedVideo channel declares. */
const CODECS: Record<string, string> = {
    h264: 'avc1.640028',
    h265: 'hvc1.1.6.L150.B0',
    hevc: 'hvc1.1.6.L150.B0',
    vp9: 'vp09.00.10.08',
    av1: 'av01.0.08M.08'
};

const MICROSECONDS_PER_NANOSECOND = 1000n;

/**
 * One camera's video decoder, kept open across frames.
 *
 * Playing a recording asks for one picture after another out of a stream where most pictures
 * cannot be decoded alone. A decoder rebuilt per picture has to replay its whole group of
 * pictures every time, so stepping costs more the deeper into a group it gets. This one
 * remembers what it has fed: moving forward inside the same group feeds only the chunks since
 * the last picture, and only a jump backwards, or a new group, starts it over.
 *
 * @param format - The channel's declared format, e.g. `h264`.
 * @param maxWidth - Width the pictures are handed back at; they are drawn in a strip.
 */
export function createVideoStream(format: string, maxWidth: number) {
    const codec = CODECS[format.toLowerCase()] ?? format;
    let decoder: VideoDecoder | undefined;
    /** Log times already fed to the open decoder, oldest first. */
    let fed: bigint[] = [];
    /** The most recent picture the decoder emitted; replaced as pictures arrive. */
    let latest: VideoFrame | undefined;

    function close(): void {
        latest?.close();
        latest = undefined;
        if (decoder && decoder.state !== 'closed') decoder.close();
        decoder = undefined;
        fed = [];
    }

    function receive(frame: VideoFrame): void {
        latest?.close();
        latest = frame;
    }

    /** Whether the open decoder is already partway through this exact slice. */
    function continues(slice: readonly VideoChunk[]): boolean {
        return (
            decoder?.state === 'configured' &&
            fed.length > 0 &&
            fed.length <= slice.length &&
            fed.every((logTimeNs, index) => slice[index].logTimeNs === logTimeNs)
        );
    }

    async function open(): Promise<VideoDecoder> {
        if (typeof VideoDecoder === 'undefined') {
            throw new ProviderError('schema', 'This browser cannot decode the recording video.');
        }
        const { supported } = await VideoDecoder.isConfigSupported({ codec });
        if (!supported) {
            throw new ProviderError('schema', `This browser cannot decode ${format} video.`);
        }
        const created = new VideoDecoder({ output: receive, error: () => undefined });
        created.configure({ codec, optimizeForLatency: true });
        decoder = created;
        fed = [];
        return created;
    }

    /**
     * Decodes the slice's last picture, feeding only what the open decoder still needs.
     *
     * @param slice - Chunks from a keyframe through the wanted picture, as `chunksForTarget`
     * selects them.
     * @returns The picture, or null when the decoder emitted none for it. Errors from the
     * decoder surface from `flush`, which is also what guarantees every picture fed has been
     * emitted by the time this returns.
     */
    async function decode(slice: readonly VideoChunk[]): Promise<ImageBitmap | null> {
        if (slice.length === 0) return null;
        const continuing = continues(slice);
        if (!continuing) close();
        const pending = continuing ? slice.slice(fed.length) : slice;
        if (pending.length === 0) return null;

        const active = decoder ?? (await open());
        for (const chunk of pending) {
            active.decode(
                new EncodedVideoChunk({
                    type: fed.length === 0 ? 'key' : 'delta',
                    timestamp: Number(chunk.logTimeNs / MICROSECONDS_PER_NANOSECOND),
                    data: chunk.data
                })
            );
            fed.push(chunk.logTimeNs);
        }
        await active.flush();

        const picture = latest;
        latest = undefined;
        if (!picture) return null;
        try {
            return await createImageBitmap(
                picture,
                picture.displayWidth > maxWidth
                    ? { resizeWidth: maxWidth, resizeQuality: 'low' }
                    : undefined
            );
        } finally {
            picture.close();
        }
    }

    return { decode, close };
}
