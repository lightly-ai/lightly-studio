import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadImageBitmap } from './loadImageBitmap';

vi.mock('$lib/utils', () => ({ getImageURLById: (id: string) => `/images/sample/${id}` }));

describe('loadImageBitmap', () => {
    afterEach(() => vi.unstubAllGlobals());

    it('decodes the image file once and resizes the decoded bitmap', async () => {
        const blob = new Blob(['jpeg']);
        const fullSize = { width: 4000, height: 3000, close: vi.fn() };
        const resized = { width: 640, height: 640, close: vi.fn() };
        const createImageBitmap = vi.fn(async (source: unknown) =>
            source === blob ? fullSize : resized
        );
        vi.stubGlobal('createImageBitmap', createImageBitmap);
        vi.stubGlobal(
            'fetch',
            vi.fn(async () => ({ ok: true, blob: async () => blob }))
        );

        const result = await loadImageBitmap('sample-1', { width: 640, height: 640 });

        expect(result).toEqual({ bitmap: resized, original: { width: 4000, height: 3000 } });
        expect(createImageBitmap.mock.calls.filter(([source]) => source === blob)).toHaveLength(1);
        expect(createImageBitmap).toHaveBeenCalledWith(fullSize, {
            resizeWidth: 640,
            resizeHeight: 640,
            resizeQuality: 'high'
        });
        expect(fullSize.close).toHaveBeenCalledOnce();
    });
});
