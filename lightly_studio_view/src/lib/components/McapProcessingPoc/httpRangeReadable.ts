import type { IReadable } from '@mcap/core';

export class HttpRangeReadable implements IReadable {
    bytesRead = 0;
    requestCount = 0;

    constructor(
        private readonly url: string,
        private readonly sizeBytes: bigint
    ) {}

    resetCounts(): void {
        this.bytesRead = 0;
        this.requestCount = 0;
    }

    async size(): Promise<bigint> {
        return this.sizeBytes;
    }

    async read(offset: bigint, size: bigint): Promise<Uint8Array> {
        if (size === 0n) return new Uint8Array();
        const end = offset + size - 1n;
        const response = await fetch(this.url, {
            cache: 'no-store',
            headers: { Range: `bytes=${offset}-${end}` }
        });
        if (response.status !== 206) {
            throw new Error(`MCAP range request returned HTTP ${response.status}, expected 206.`);
        }
        const content = new Uint8Array(await response.arrayBuffer());
        if (content.byteLength > Number(size)) {
            throw new Error('MCAP range response was larger than requested.');
        }
        this.bytesRead += content.byteLength;
        this.requestCount += 1;
        return content;
    }
}
