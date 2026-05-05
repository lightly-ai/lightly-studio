import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { useImageUpload } from '$lib/hooks';
import { createMutation } from '@tanstack/svelte-query';

const { mutateMock, embedImageFromFileMutationMock } = vi.hoisted(() => ({
    mutateMock: vi.fn(),
    embedImageFromFileMutationMock: vi.fn(() => ({}))
}));

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    embedImageFromFileMutation: embedImageFromFileMutationMock
}));

vi.mock('@tanstack/svelte-query', () => ({
    createMutation: vi.fn(() => writable({ mutate: mutateMock }))
}));

describe('useImageUpload', () => {
    const onError = vi.fn();
    const onSuccess = vi.fn();

    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        createObjectURL.mockReturnValue('blob:preview-url');

        vi.stubGlobal('URL', {
            createObjectURL,
            revokeObjectURL
        });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('rejects oversized images', async () => {
        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onSuccess,
            maxSizeMb: 1
        });
        const largeFile = new File([new Uint8Array(2 * 1024 * 1024)], 'large.png', {
            type: 'image/png'
        });

        await upload.upload(largeFile);

        expect(onError).toHaveBeenCalledWith('Image is too large. Maximum size is 1MB.');
        expect(mutateMock).not.toHaveBeenCalled();
        expect(get(upload.isUploading)).toBe(false);
    });

    it('uploads image and sets preview on success', async () => {
        mutateMock.mockImplementation((_variables, callbacks) => {
            callbacks?.onSuccess?.([1, 2, 3], undefined, undefined);
        });

        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onSuccess
        });

        const file = new File(['image'], 'image.png', { type: 'image/png' });
        await upload.upload(file);

        expect(createMutation).toHaveBeenCalledWith(expect.anything());
        expect(mutateMock).toHaveBeenCalledWith(
            {
                path: {
                    collection_id: 'collection-id'
                },
                body: {
                    file
                }
            },
            expect.any(Object)
        );
        expect(get(upload.imageName)).toBe('image.png');
        expect(get(upload.previewUrl)).toBe('blob:preview-url');
        expect(onSuccess).toHaveBeenCalledWith({
            fileName: 'image.png',
            embedding: [1, 2, 3]
        });
        expect(onError).not.toHaveBeenCalled();
    });

    it('reports upload failures', async () => {
        mutateMock.mockImplementation((_variables, callbacks) => {
            callbacks?.onError?.(
                new Error('Error uploading image: Bad Request'),
                undefined,
                undefined
            );
        });

        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onSuccess
        });

        const file = new File(['image'], 'image.png', { type: 'image/png' });
        await upload.upload(file);

        expect(onError).toHaveBeenCalledWith('Error uploading image: Bad Request');
        expect(onSuccess).not.toHaveBeenCalled();
        expect(get(upload.isUploading)).toBe(false);
    });

    it('clears previously uploaded image state when a later upload fails', async () => {
        createObjectURL.mockReturnValueOnce('blob:first-preview-url');

        mutateMock.mockImplementationOnce((_variables, callbacks) => {
            callbacks?.onSuccess?.([1, 2, 3], undefined, undefined);
        });

        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onSuccess
        });

        const firstFile = new File(['image-1'], 'image-1.png', { type: 'image/png' });
        await upload.upload(firstFile);

        expect(get(upload.imageName)).toBe('image-1.png');
        expect(get(upload.previewUrl)).toBe('blob:first-preview-url');

        mutateMock.mockImplementationOnce((_variables, callbacks) => {
            callbacks?.onError?.(
                new Error('Error uploading image: Bad Request'),
                undefined,
                undefined
            );
        });

        const secondFile = new File(['image-2'], 'image-2.png', { type: 'image/png' });
        await upload.upload(secondFile);

        expect(onError).toHaveBeenCalledWith('Error uploading image: Bad Request');
        expect(get(upload.imageName)).toBeUndefined();
        expect(get(upload.previewUrl)).toBeUndefined();
        expect(revokeObjectURL).toHaveBeenCalledWith('blob:first-preview-url');
    });

    it('revokes preview URL when clearing image', () => {
        const upload = useImageUpload({
            collectionId: 'collection-id',
            onError,
            onSuccess
        });

        upload.previewUrl.set('blob:previous-url');

        upload.clear();

        expect(revokeObjectURL).toHaveBeenCalledWith('blob:previous-url');
        expect(get(upload.previewUrl)).toBeUndefined();
        expect(get(upload.imageName)).toBeUndefined();
    });
});
