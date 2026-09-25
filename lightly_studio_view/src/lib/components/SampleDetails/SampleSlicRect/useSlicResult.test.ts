import { render, waitFor } from '@testing-library/svelte';
import { beforeEach, expect, it, vi } from 'vitest';
import { loadSuperpixelsForImage } from '$lib/utils/slic';
import { maskToDataUrl } from '$lib/components/SampleAnnotation/utils';
import SlicResultHarness from './SlicResultHarness.svelte';

vi.mock('$lib/utils/slic', () => ({ loadSuperpixelsForImage: vi.fn() }));
vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    maskToDataUrl: vi.fn(() => 'data:image/png;base64,boundaries')
}));
vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor',
    () => ({ default: () => ({ r: 0, g: 0, b: 255, a: 255 }) })
);
const result = {
    segmentation: {
        width: 1,
        height: 1,
        labels: new Int32Array([0]),
        boundaries: new Uint8Array([1]),
        segmentCount: 1,
        labelPixelIndexes: [[0]],
        pixelIndexes: new Uint32Array([0]),
        segmentOffsets: new Uint32Array([0, 1])
    },
    scaleX: 1,
    scaleY: 1
};
const load = vi.mocked(loadSuperpixelsForImage);
beforeEach(() => vi.clearAllMocks());

it('loads boundaries, clears them on size changes, and reports failures', async () => {
    load.mockResolvedValueOnce(result);
    const view = render(SlicResultHarness, { imageUrl: 'a', level: 'medium', color: 'blue' });
    await waitFor(() => expect(view.getByRole('status')).toHaveTextContent('ready'));
    expect(view.getByRole('img')).toHaveAttribute('src', 'data:image/png;base64,boundaries');
    expect(maskToDataUrl).toHaveBeenCalledWith(result.segmentation.boundaries, 1, 1, {
        r: 0,
        g: 0,
        b: 255,
        a: 170
    });
    await view.rerender({ color: 'red' });
    expect(load).toHaveBeenCalledOnce();
    const pending = Promise.withResolvers<typeof result>();
    load.mockReturnValueOnce(pending.promise);
    await view.rerender({ level: 'fine' });
    expect(load).toHaveBeenLastCalledWith({ imageUrl: 'a', level: 'fine' });
    expect(view.getByRole('status')).toHaveTextContent('computing');
    expect(view.queryByRole('img')).not.toBeInTheDocument();
    pending.reject(new Error('load failed'));
    await waitFor(() => expect(view.getByRole('status')).toHaveTextContent('error'));
});

it.each(['resolve', 'reject'] as const)(
    'ignores stale %s after revisiting an image',
    async (settle) => {
        const old = Promise.withResolvers<typeof result>();
        load.mockReturnValueOnce(old.promise).mockResolvedValue(result);
        const view = render(SlicResultHarness, { imageUrl: 'a', level: 'medium', color: 'blue' });
        await view.rerender({ imageUrl: 'b' });
        await view.rerender({ imageUrl: 'a' });
        await waitFor(() => expect(view.getByRole('status')).toHaveTextContent('ready'));
        if (settle === 'resolve')
            old.resolve({ ...result, segmentation: { ...result.segmentation, width: 2 } });
        else old.reject(new Error('stale failure'));
        await old.promise.catch(() => {});
        expect(view.getByRole('status')).toHaveTextContent('ready');
        expect(maskToDataUrl).not.toHaveBeenCalledWith(expect.anything(), 2, 1, expect.anything());
    }
);
