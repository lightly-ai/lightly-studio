import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    embedImageViaService,
    embedTextViaService,
    fetchServiceInfo
} from './embeddingServiceClient';

const validInfo = {
    contract_version: '1',
    model_id: 'customer-model-v1',
    embedding_dimension: 512,
    supports_text: true,
    supports_image: true,
    normalized: false
};

function mockJsonResponse(body: unknown, ok = true, status = 200) {
    return { ok, status, json: async () => body } as Response;
}

/** A fetch mock whose recorded calls keep the `(url, init)` argument types. */
function mockFetch(body: unknown, ok = true, status = 200) {
    return vi.fn<(url: string, init: RequestInit) => Promise<Response>>(async () =>
        mockJsonResponse(body, ok, status)
    );
}

describe('fetchServiceInfo', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('returns the reported identity and capabilities', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => mockJsonResponse(validInfo))
        );

        const info = await fetchServiceInfo({ servingUrl: 'https://gpu-box:8123' });

        expect(info).toEqual({
            contractVersion: '1',
            modelId: 'customer-model-v1',
            embeddingDimension: 512,
            supportsText: true,
            supportsImage: true,
            normalized: false
        });
    });

    it('requests /info on the given base url without a double slash', async () => {
        const fetchMock = mockFetch(validInfo);
        vi.stubGlobal('fetch', fetchMock);

        await fetchServiceInfo({ servingUrl: 'https://gpu-box:8123/' });

        expect(fetchMock.mock.calls[0][0]).toBe('https://gpu-box:8123/info');
    });

    it('treats missing capability flags as unsupported', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () =>
                mockJsonResponse({ model_id: 'customer-model-v1', embedding_dimension: 512 })
            )
        );

        const info = await fetchServiceInfo({ servingUrl: 'https://gpu-box:8123' });

        expect(info.supportsText).toBe(false);
        expect(info.supportsImage).toBe(false);
    });

    it('rejects a response without a model_id', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => mockJsonResponse({ embedding_dimension: 512 }))
        );

        await expect(fetchServiceInfo({ servingUrl: 'https://gpu-box:8123' })).rejects.toThrow(
            /model_id/
        );
    });

    it('reports a non-ok status', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => mockJsonResponse(null, false, 503))
        );

        await expect(fetchServiceInfo({ servingUrl: 'https://gpu-box:8123' })).rejects.toThrow(
            /503/
        );
    });

    it('explains a blocked request rather than repeating "Failed to fetch"', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => {
                throw new TypeError('Failed to fetch');
            })
        );

        await expect(fetchServiceInfo({ servingUrl: 'http://192.168.1.20:8123' })).rejects.toThrow(
            /blocked the request/
        );
    });

    it('times out an unresponsive service', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn((_url: string, init: RequestInit) => {
                return new Promise((_resolve, reject) => {
                    init.signal?.addEventListener('abort', () => {
                        const error = new Error('aborted');
                        error.name = 'AbortError';
                        reject(error);
                    });
                });
            })
        );

        await expect(
            fetchServiceInfo({ servingUrl: 'https://gpu-box:8123', timeoutMs: 5 })
        ).rejects.toThrow(/did not respond/);
    });
});

describe('embedTextViaService', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('posts the query and returns the vector', async () => {
        const fetchMock = mockFetch([0.1, 0.2, 0.3]);
        vi.stubGlobal('fetch', fetchMock);

        const vector = await embedTextViaService({
            servingUrl: 'https://gpu-box:8123',
            text: 'a red car'
        });

        expect(vector).toEqual([0.1, 0.2, 0.3]);
        expect(fetchMock.mock.calls[0][0]).toBe('https://gpu-box:8123/embed/text');
        expect(fetchMock.mock.calls[0][1].body).toBe(JSON.stringify({ text: 'a red car' }));
    });

    it('rejects a body that is not a vector', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => mockJsonResponse({ embedding: [0.1] }))
        );

        await expect(
            embedTextViaService({ servingUrl: 'https://gpu-box:8123', text: 'a red car' })
        ).rejects.toThrow(/vector of numbers/);
    });

    it('rejects a vector containing non-finite values', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => mockJsonResponse([0.1, null, 0.3]))
        );

        await expect(
            embedTextViaService({ servingUrl: 'https://gpu-box:8123', text: 'a red car' })
        ).rejects.toThrow(/vector of numbers/);
    });
});

describe('embedImageViaService', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('posts the file as multipart under the "image" field', async () => {
        const fetchMock = mockFetch([0.4, 0.5]);
        vi.stubGlobal('fetch', fetchMock);
        const file = new File(['bytes'], 'query.jpg', { type: 'image/jpeg' });

        const vector = await embedImageViaService({ servingUrl: 'https://gpu-box:8123', file });

        expect(vector).toEqual([0.4, 0.5]);
        expect(fetchMock.mock.calls[0][0]).toBe('https://gpu-box:8123/embed/image');
        const form = fetchMock.mock.calls[0][1].body as FormData;
        expect((form.get('image') as File).name).toBe('query.jpg');
    });
});
