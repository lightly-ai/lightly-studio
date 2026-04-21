import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useImageUpload } from '$lib/hooks';

describe('useImageUpload', () => {
    const onError = vi.fn();
    const onUploadSuccess = vi.fn();

    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        createObjectURL.mockReturnValue('blob:preview-url');

        vi.stubGlobal('fetch', vi.fn());
        vi.stubGlobal('URL', {
            createObjectURL,
            revokeObjectURL
        });
    });

    it('rejects oversized images', async () => {
        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onUploadSuccess,
            maxImageSizeMb: 1
        });
        const largeFile = new File([new Uint8Array(2 * 1024 * 1024)], 'large.png', {
            type: 'image/png'
        });

        await upload.uploadImage(largeFile);

        expect(onError).toHaveBeenCalledWith('Image is too large. Maximum size is 1MB.');
        expect(global.fetch).not.toHaveBeenCalled();
        expect(get(upload.isUploading)).toBe(false);
    });

    it('uploads image and sets preview on success', async () => {
        vi.mocked(global.fetch).mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue([1, 2, 3])
        } as unknown as Response);

        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onUploadSuccess
        });

        const file = new File(['image'], 'image.png', { type: 'image/png' });
        await upload.uploadImage(file);

        expect(global.fetch).toHaveBeenCalledWith(
            '/api/image_embedding/from_file/for_collection/collection-id',
            {
                method: 'POST',
                body: expect.any(FormData)
            }
        );
        expect(get(upload.activeImage)).toBe('image.png');
        expect(get(upload.previewUrl)).toBe('blob:preview-url');
        expect(onUploadSuccess).toHaveBeenCalledWith({
            fileName: 'image.png',
            embedding: [1, 2, 3]
        });
        expect(onError).not.toHaveBeenCalled();
    });

    it('reports upload failures', async () => {
        vi.mocked(global.fetch).mockResolvedValue({
            ok: false,
            statusText: 'Bad Request'
        } as Response);

        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onUploadSuccess
        });

        const file = new File(['image'], 'image.png', { type: 'image/png' });
        await upload.uploadImage(file);

        expect(onError).toHaveBeenCalledWith('Error uploading image: Bad Request');
        expect(onUploadSuccess).not.toHaveBeenCalled();
        expect(get(upload.isUploading)).toBe(false);
    });

    it('revokes preview URL when clearing image', () => {
        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onUploadSuccess
        });

        upload.previewUrl.set('blob:previous-url');

        upload.clearImage();

        expect(revokeObjectURL).toHaveBeenCalledWith('blob:previous-url');
        expect(get(upload.previewUrl)).toBe(null);
        expect(get(upload.activeImage)).toBe(null);
    });
});
