import { afterEach, describe, expect, it, vi } from 'vitest';
import { getSlicComputeOptions, loadSuperpixelsForImage, prepareImageForSlic } from './slic';
import { createSlicMaskEditor } from '$lib/components/SampleDetails/SampleSlicRect/createSlicMaskEditor';
import { encodeBinaryMaskToRLE } from '$lib/components/SampleAnnotation/utils';

describe('image preparation', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('recomputes nested levels and erases a coarse cell completely using its fine cells', async () => {
        const width = 128,
            height = 96;
        const data = new Uint8ClampedArray(width * height * 4);
        for (let i = 0; i < width * height; i++)
            data.set([(i % width) * 2, Math.floor(i / width) * 2, 128, 255], i * 4);
        vi.stubGlobal(
            'Image',
            class {
                naturalWidth = width;
                naturalHeight = height;
                onload = () => {};
                set src(_url: string) {
                    this.onload();
                }
            }
        );
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
            drawImage: vi.fn(),
            getImageData: () => ({ data, width, height })
        } as unknown as CanvasRenderingContext2D);
        const results = await Promise.all(
            (['fine', 'medium', 'coarse'] as const).map((level) =>
                loadSuperpixelsForImage({ imageUrl: '/nested.png', level })
            )
        );
        const [fineCells, mediumCells, coarseCells] = results.map((r) => r.segmentation);
        for (const [child, parent] of [
            [fineCells, mediumCells],
            [mediumCells, coarseCells]
        ]) {
            const parents = new Map<number, number>();
            child.labels.forEach((label, i) => {
                expect(parents.get(label) ?? parent.labels[i]).toBe(parent.labels[i]);
                parents.set(label, parent.labels[i]);
            });
        }
        const coarse = createSlicMaskEditor({ segmentation: coarseCells, width, height });
        coarse.beginStroke({ x: 0, y: 0 });
        const mask = coarse.commitStroke()!;
        const fine = createSlicMaskEditor({
            segmentation: fineCells,
            width,
            height,
            segmentationMask: encodeBinaryMaskToRLE(mask)
        });
        mask.forEach((pixel, i) => {
            if (!pixel || !fine.getMask()[i]) return;
            fine.beginStroke({ x: i % width, y: Math.floor(i / width) });
            fine.commitStroke();
        });
        expect(fine.getMask().some(Boolean)).toBe(false);
    });

    it('bounds the compute resolution and preserves aspect ratio and original scale', async () => {
        vi.stubGlobal(
            'Image',
            class {
                naturalWidth = 2048;
                naturalHeight = 1024;
                onload = () => {};
                set src(_url: string) {
                    this.onload();
                }
            }
        );
        const drawImage = vi.fn();
        const getImageData = vi.fn(() => ({ width: 512, height: 256 }));
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
            drawImage,
            getImageData
        } as unknown as CanvasRenderingContext2D);
        const result = await prepareImageForSlic('/image.png');
        expect(result.scaleX).toBe(4);
        expect(result.scaleY).toBe(4);
        expect(getImageData).toHaveBeenCalledWith(0, 0, 512, 256);
    });

    it('rejects image decode failures', async () => {
        vi.stubGlobal(
            'Image',
            class {
                onerror = () => {};
                set src(_url: string) {
                    this.onerror();
                }
            }
        );
        await expect(prepareImageForSlic('/broken.png')).rejects.toThrow('Failed to decode image');
    });
});

it.each([
    ['coarse', 80],
    ['medium', 320],
    ['fine', 640]
] as const)('targets %s granularity', (level, count) => {
    expect(getSlicComputeOptions(level).targetSegments).toBe(count);
});
