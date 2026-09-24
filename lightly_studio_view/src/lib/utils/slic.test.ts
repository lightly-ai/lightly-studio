import { afterEach, describe, expect, it, vi } from 'vitest';
import { prepareImageForSlic } from './slic';

describe('image preparation', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
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
