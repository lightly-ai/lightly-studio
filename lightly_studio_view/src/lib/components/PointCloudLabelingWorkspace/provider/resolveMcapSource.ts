import { canonicalCoordinateFrame } from '../domain';
import { ProviderError } from './providerError';
import type { McapSource } from './source';

interface ResolveOptions {
    /** MCAP sample whose recording is read. Identifies the recording for cache keys. */
    sampleId: string;
    /** URL that serves the recording as byte ranges. */
    url: string;
    /**
     * Confirmed sensor coordinate convention. Never inferred from a schema or topic
     * name; the caller states it, and the reader rejects a mismatch.
     */
    coordinateFrameId: string;
    fetchRange?: typeof fetch;
}

const contentRangePattern = /^bytes 0-0\/(\d+)$/;

/**
 * Builds an `McapSource` by asking the recording endpoint for its first byte.
 *
 * A range response has to state the total length in `Content-Range`, so one one-byte
 * read yields the recording's size, and its `ETag` yields a revision to pin the rest of
 * the reads to. That is why no separate metadata endpoint is needed: everything else the
 * provider needs is inside the recording itself.
 *
 * @param options - The sample, its recording URL, and the confirmed sensor frame.
 * @returns A source ready to hand to `createMcapFrameProvider`.
 * @throws ProviderError - Access was denied, the recording is missing, or the server
 * does not honour range requests.
 */
export async function resolveMcapSource(options: ResolveOptions): Promise<McapSource> {
    const request = options.fetchRange ?? fetch;
    const response = await request(options.url, {
        headers: { Range: 'bytes=0-0' },
        credentials: 'same-origin'
    });
    await response.body?.cancel().catch(() => undefined);

    if (response.status === 401 || response.status === 403) {
        throw new ProviderError('auth', 'Recording access was denied. Refresh access and retry.');
    }
    if (response.status === 404) {
        throw new ProviderError('source', 'The recording for this sample is not available.');
    }

    if (!options.coordinateFrameId) {
        throw new ProviderError('source', 'The sensor coordinate frame must be confirmed.');
    }

    const sizeBytes = readTotalLength(response);
    const etag = response.headers.get('ETag')?.replace(/^W\//, '').replaceAll('"', '');
    return {
        recordingId: options.sampleId,
        version: etag || sizeBytes,
        url: options.url,
        sizeBytes,
        ...(etag ? { etag: `"${etag}"` } : {}),
        coordinateFrame: canonicalCoordinateFrame(options.coordinateFrameId),
        logClockId: `${options.sampleId}:log`,
        publishClockId: `${options.sampleId}:publish`
    };
}

function readTotalLength(response: Response): string {
    const contentRange = response.headers.get('Content-Range') ?? '';
    const total = contentRangePattern.exec(contentRange)?.[1];
    if (response.status !== 206 || !total) {
        throw new ProviderError(
            'range',
            'The recording server must return the requested byte range.'
        );
    }
    return total;
}
