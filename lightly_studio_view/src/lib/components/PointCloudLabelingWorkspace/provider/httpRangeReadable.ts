import { ProviderError } from './providerError';

interface RangeSource {
    url: string;
    sizeBytes: string;
    /** A strong ETag, when supplied by the source endpoint. */
    etag?: string;
}

/** Random access used only in the MCAP worker; rejects full-file fallback responses. */
export class HttpRangeReadable {
    readonly #length: bigint;
    bytesRead = 0;

    constructor(
        private readonly source: RangeSource,
        private readonly signal: AbortSignal,
        /**
         * Wrapped rather than passed as a bare reference: the browser's `fetch` must be
         * called on the global object, and reaching it through a field would hand it this
         * instance as the receiver instead.
         */
        private readonly fetchRange: typeof fetch = (input, init) => fetch(input, init),
        private readonly maxReadBytes = 64 * 1024 * 1024
    ) {
        if (!/^\d+$/.test(source.sizeBytes)) {
            throw new ProviderError('source', 'The recording size is missing or invalid.');
        }
        this.#length = BigInt(source.sizeBytes);
    }

    async size(): Promise<bigint> {
        return this.#length;
    }

    async read(offset: bigint, size: bigint): Promise<Uint8Array> {
        this.signal.throwIfAborted();
        if (offset < 0n || size < 0n || offset + size > this.#length) {
            throw new ProviderError(
                'range',
                'The MCAP index requested bytes outside the recording.'
            );
        }
        if (size > BigInt(this.maxReadBytes)) {
            throw new ProviderError('limit', 'The MCAP read exceeds the configured memory limit.');
        }
        if (size === 0n) return new Uint8Array();
        const headers: Record<string, string> = { Range: `bytes=${offset}-${offset + size - 1n}` };
        if (this.source.etag) headers['If-Match'] = this.source.etag;
        // Called through a local so the receiver is never this instance, whatever was
        // injected: `fetch` throws "Illegal invocation" when it is not called on the global.
        const fetchRange = this.fetchRange;
        const response = await fetchRange(this.source.url, {
            headers,
            signal: this.signal,
            credentials: 'same-origin'
        });
        try {
            this.validateResponse(response, offset, size);
            return await this.readBody(response, Number(size));
        } catch (error) {
            await response.body?.cancel().catch(() => undefined);
            throw error;
        }
    }

    private validateResponse(response: Response, offset: bigint, size: bigint): void {
        if (response.status === 401 || response.status === 403) {
            throw new ProviderError(
                'auth',
                'Recording access was denied. Refresh access and retry.'
            );
        }
        if (response.status === 404 || response.status === 412) {
            throw new ProviderError(
                'source',
                'The recording is missing or changed. Reload its metadata.'
            );
        }
        const expected = `bytes ${offset}-${offset + size - 1n}/${this.#length}`;
        if (response.status !== 206 || response.headers.get('Content-Range') !== expected) {
            throw new ProviderError(
                'range',
                'The recording server must return the requested byte range.'
            );
        }
    }

    private async readBody(response: Response, size: number): Promise<Uint8Array> {
        const reader = response.body?.getReader();
        if (!reader) throw new ProviderError('range', 'The recording response has no content.');
        const bytes = new Uint8Array(size);
        let offset = 0;
        try {
            for (;;) {
                this.signal.throwIfAborted();
                const chunk = await reader.read();
                if (chunk.done) break;
                if (offset + chunk.value.length > size) {
                    throw new ProviderError(
                        'range',
                        'The recording response exceeds the requested range.'
                    );
                }
                bytes.set(chunk.value, offset);
                offset += chunk.value.length;
            }
            if (offset !== size)
                throw new ProviderError('range', 'The recording response is truncated.');
            this.bytesRead += offset;
            return bytes;
        } finally {
            await reader.cancel().catch(() => undefined);
            reader.releaseLock();
        }
    }
}
