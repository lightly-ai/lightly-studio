import { describe, expect, it, vi } from 'vitest';
import { HttpRangeReadable } from './httpRangeReadable';

function readable(response: Response) {
    const fetchRange = vi.fn<typeof fetch>().mockResolvedValue(response);
    const controller = new AbortController();
    return {
        reader: new HttpRangeReadable(
            { url: '/recording', sizeBytes: '100', etag: '"version"' },
            controller.signal,
            fetchRange,
            16
        ),
        controller,
        fetchRange
    };
}

describe('HttpRangeReadable', () => {
    it('never calls fetch with itself as the receiver', async () => {
        // A real browser `fetch` throws "Illegal invocation" unless it is called on the
        // global object, which Node's implementation does not enforce.
        function strictFetch(this: unknown): Promise<Response> {
            if (this !== undefined && this !== globalThis) {
                throw new TypeError("Failed to execute 'fetch': Illegal invocation");
            }
            return Promise.resolve(
                new Response(new Uint8Array([7]), {
                    status: 206,
                    headers: { 'Content-Range': 'bytes 0-0/100' }
                })
            );
        }
        const reader = new HttpRangeReadable(
            { url: '/recording', sizeBytes: '100' },
            new AbortController().signal,
            strictFetch as typeof fetch
        );

        expect(await reader.read(0n, 1n)).toEqual(new Uint8Array([7]));
    });

    it('rejects a source without a usable recording size', () => {
        const signal = new AbortController().signal;
        expect(() => new HttpRangeReadable({ url: '/r', sizeBytes: '' }, signal)).toThrow(
            /recording size/
        );
        expect(() => new HttpRangeReadable({ url: '/r', sizeBytes: '1.5' }, signal)).toThrow(
            /recording size/
        );
    });

    it.each([404, 412])('reports a missing or changed recording on %i', async (status) => {
        const { reader } = readable(new Response(null, { status }));
        await expect(reader.read(0n, 3n)).rejects.toMatchObject({
            code: 'source',
            message: expect.stringMatching(/missing or changed/)
        });
    });

    it('reads an exact range and pins the recording version', async () => {
        const { reader, fetchRange } = readable(
            new Response(new Uint8Array([1, 2, 3]), {
                status: 206,
                headers: { 'Content-Range': 'bytes 10-12/100' }
            })
        );
        expect(await reader.read(10n, 3n)).toEqual(new Uint8Array([1, 2, 3]));
        expect(fetchRange.mock.calls[0][1]?.headers).toEqual({
            Range: 'bytes=10-12',
            'If-Match': '"version"'
        });
        expect(reader.bytesRead).toBe(3);
    });

    it.each([200, 416])('rejects an unsupported range response (%i)', async (status) => {
        const { reader } = readable(new Response('abc', { status }));
        await expect(reader.read(0n, 3n)).rejects.toMatchObject({ code: 'range' });
    });

    it.each([401, 403])('reports access failures (%i)', async (status) => {
        const { reader } = readable(new Response(null, { status }));
        await expect(reader.read(0n, 3n)).rejects.toMatchObject({ code: 'auth' });
    });

    it.each(['ab', 'abcd'])('rejects a body of the wrong length: %s', async (body) => {
        const { reader } = readable(
            new Response(body, { status: 206, headers: { 'Content-Range': 'bytes 0-2/100' } })
        );
        await expect(reader.read(0n, 3n)).rejects.toMatchObject({ code: 'range' });
    });

    it('enforces bounds, memory limits, and cancellation before fetching', async () => {
        const { reader, fetchRange, controller } = readable(new Response());
        await expect(reader.read(99n, 2n)).rejects.toMatchObject({ code: 'range' });
        await expect(reader.read(0n, 17n)).rejects.toMatchObject({ code: 'limit' });
        controller.abort();
        await expect(reader.read(0n, 1n)).rejects.toMatchObject({ name: 'AbortError' });
        expect(fetchRange).not.toHaveBeenCalled();
    });
});
