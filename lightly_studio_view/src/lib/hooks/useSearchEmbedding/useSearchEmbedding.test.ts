import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get, writable, type Writable } from 'svelte/store';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
import { useSearchEmbedding } from './useSearchEmbedding';

type Store<T> = {
    subscribe: (run: (value: T) => void) => () => void;
    set: (value: T) => void;
};

const mocks = vi.hoisted(() => {
    const createStore = <T>(initialValue: T): Store<T> => {
        let value = initialValue;
        const subscribers = new Set<(value: T) => void>();
        return {
            subscribe: (run) => {
                run(value);
                subscribers.add(run);
                return () => subscribers.delete(run);
            },
            set: (next) => {
                value = next;
                subscribers.forEach((s) => s(value));
            }
        };
    };

    return {
        toastError: vi.fn(),
        upload: vi.fn(),
        clearImage: vi.fn(),
        setPreview: vi.fn(),
        embedText: vi.fn(),
        imageName: createStore<string | undefined>(undefined),
        previewUrl: createStore<string | undefined>(undefined),
        isUploading: createStore(false),
        isEmbedding: createStore(false),
        useImageUploadOptions: undefined as unknown,
        useTextEmbeddingOptions: undefined as unknown
    };
});

vi.mock('svelte-sonner', () => ({
    toast: { error: mocks.toastError }
}));

vi.mock('$lib/hooks/useImageUpload/useImageUpload', () => ({
    useImageUpload: (options: unknown) => {
        mocks.useImageUploadOptions = options;
        return {
            imageName: mocks.imageName,
            previewUrl: mocks.previewUrl,
            isUploading: mocks.isUploading,
            upload: mocks.upload,
            clear: mocks.clearImage,
            setPreview: mocks.setPreview
        };
    }
}));

vi.mock('$lib/hooks/useTextEmbedding/useTextEmbedding', () => ({
    useTextEmbedding: (options: unknown) => {
        mocks.useTextEmbeddingOptions = options;
        return {
            isEmbedding: mocks.isEmbedding,
            embed: mocks.embedText
        };
    }
}));

type EmbedOptions = {
    onSuccess: (result: { queryText: string; embedding: number[] }) => void;
    onError: (message: string) => void;
};

describe('useSearchEmbedding', () => {
    let embedding: Writable<TextEmbedding | undefined>;

    beforeEach(() => {
        vi.clearAllMocks();
        mocks.imageName.set(undefined);
        mocks.previewUrl.set(undefined);
        mocks.isUploading.set(false);
        mocks.isEmbedding.set(false);
        embedding = writable(undefined);
    });

    it('setText delegates to useTextEmbedding and writes embedding on success', async () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        await search.setText('cat');

        expect(mocks.embedText).toHaveBeenCalledWith('cat');

        const opts = mocks.useTextEmbeddingOptions as EmbedOptions;
        opts.onSuccess({ queryText: 'cat', embedding: [1, 2, 3] });
        expect(get(embedding)).toEqual({ queryText: 'cat', embedding: [1, 2, 3] });
    });

    it('setText clears any active image before embedding', async () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        await search.setText('cat');

        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('setText with empty string clears the embedding store', async () => {
        embedding.set({ queryText: 'old', embedding: [0] });
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        await search.setText('');

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('setText with whitespace clears the embedding store', async () => {
        embedding.set({ queryText: 'old', embedding: [0] });
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        await search.setText('   ');

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('routes onError from useTextEmbedding to toast', () => {
        useSearchEmbedding({ collectionId: 'collection-id', embedding });

        const opts = mocks.useTextEmbeddingOptions as EmbedOptions;
        opts.onError('boom');

        expect(mocks.toastError).toHaveBeenCalledWith(
            'Error',
            expect.objectContaining({ description: 'boom' })
        );
    });

    it('isPending reflects useTextEmbedding.isEmbedding', () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        mocks.isEmbedding.set(true);
        expect(get(search.isPending)).toBe(true);

        mocks.isEmbedding.set(false);
        expect(get(search.isPending)).toBe(false);
    });

    it('isPending reflects useImageUpload.isUploading', () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        mocks.isUploading.set(true);
        expect(get(search.isPending)).toBe(true);

        mocks.isUploading.set(false);
        expect(get(search.isPending)).toBe(false);
    });

    it('setEmbedding writes a precomputed vector and optional preview without uploading', () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        search.setEmbedding({
            queryText: 'person-crop.png',
            embedding: [1, 0, 0],
            imagePreview: { name: 'person-crop.png', previewUrl: 'blob:crop' }
        });

        expect(mocks.clearImage).toHaveBeenCalled();
        expect(mocks.setPreview).toHaveBeenCalledWith('person-crop.png', 'blob:crop', false);
        expect(get(embedding)).toEqual({
            queryText: 'person-crop.png',
            embedding: [1, 0, 0]
        });
        expect(mocks.upload).not.toHaveBeenCalled();
    });

    it('setImage delegates to useImageUpload and writes embedding on success', async () => {
        const file = new File(['x'], 'sample.png', { type: 'image/png' });
        mocks.upload.mockResolvedValue(undefined);

        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        await search.setImage(file);

        expect(mocks.upload).toHaveBeenCalledWith(file);

        const opts = mocks.useImageUploadOptions as {
            onSuccess: (result: { fileName: string; embedding: number[] }) => void;
        };
        opts.onSuccess({ fileName: 'sample.png', embedding: [4, 5, 6] });
        expect(get(embedding)).toEqual({ queryText: 'sample.png', embedding: [4, 5, 6] });
    });

    it('image store mirrors useImageUpload name + preview', () => {
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        expect(get(search.image)).toBeUndefined();

        mocks.imageName.set('sample.png');
        mocks.previewUrl.set('blob:preview');

        expect(get(search.image)).toEqual({ name: 'sample.png', previewUrl: 'blob:preview' });
    });

    it('clear resets embedding and clears image upload state', () => {
        embedding.set({ queryText: 'foo', embedding: [1] });
        const search = useSearchEmbedding({ collectionId: 'collection-id', embedding });

        search.clear();

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });
});
