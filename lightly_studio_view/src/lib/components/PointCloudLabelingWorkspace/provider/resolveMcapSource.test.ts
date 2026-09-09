import { describe, expect, it, vi } from 'vitest';
import { canonicalCoordinateFrame } from '../domain';
import { resolveMcapSource } from './resolveMcapSource';

function respond(status: number, headers: Record<string, string> = {}) {
    return vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status, headers }));
}

const options = { sampleId: 'sample-1', url: '/mcap/media/sample-1', coordinateFrameId: 'lidar' };

describe('resolveMcapSource', () => {
    it('reads the recording length and revision from one range response', async () => {
        const fetchRange = respond(206, {
            'Content-Range': 'bytes 0-0/942817280',
            ETag: '"a1b2c3"'
        });

        expect(await resolveMcapSource({ ...options, fetchRange })).toEqual({
            recordingId: 'sample-1',
            version: 'a1b2c3',
            url: '/mcap/media/sample-1',
            sizeBytes: '942817280',
            etag: '"a1b2c3"',
            coordinateFrame: canonicalCoordinateFrame('lidar'),
            logClockId: 'sample-1:log',
            publishClockId: 'sample-1:publish'
        });
        // Read the record directly: jsdom's `Headers` drops `Range`.
        expect(fetchRange.mock.calls[0][1]?.headers).toEqual({ Range: 'bytes=0-0' });
    });

    it('falls back to the length as a revision when the server sends no entity tag', async () => {
        const source = await resolveMcapSource({
            ...options,
            fetchRange: respond(206, { 'Content-Range': 'bytes 0-0/1024' })
        });

        expect(source.version).toBe('1024');
        expect(source.etag).toBeUndefined();
    });

    it('accepts a weak entity tag', async () => {
        const source = await resolveMcapSource({
            ...options,
            fetchRange: respond(206, { 'Content-Range': 'bytes 0-0/1024', ETag: 'W/"weak"' })
        });

        expect(source.etag).toBe('"weak"');
    });

    it('rejects a server that ignores the range request', async () => {
        await expect(
            resolveMcapSource({ ...options, fetchRange: respond(200) })
        ).rejects.toMatchObject({ code: 'range' });
        await expect(
            resolveMcapSource({ ...options, fetchRange: respond(206) })
        ).rejects.toMatchObject({ code: 'range' });
    });

    it.each([401, 403])('reports denied access on %i', async (status) => {
        await expect(
            resolveMcapSource({ ...options, fetchRange: respond(status) })
        ).rejects.toMatchObject({ code: 'auth' });
    });

    it('reports a missing recording', async () => {
        await expect(
            resolveMcapSource({ ...options, fetchRange: respond(404) })
        ).rejects.toMatchObject({ code: 'source' });
    });

    it('requires a confirmed sensor frame', async () => {
        await expect(
            resolveMcapSource({
                ...options,
                coordinateFrameId: '',
                fetchRange: respond(206, { 'Content-Range': 'bytes 0-0/1024' })
            })
        ).rejects.toMatchObject({ code: 'source' });
    });
});
