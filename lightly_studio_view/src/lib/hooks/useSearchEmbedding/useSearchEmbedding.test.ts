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
        embedTextViaService: vi.fn(),
        embedImageViaService: vi.fn(),
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

vi.mock('$lib/api/embeddingService/embeddingServiceClient', () => ({
    embedTextViaService: mocks.embedTextViaService,
    embedImageViaService: mocks.embedImageViaService
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
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        await search.setText('cat');

        expect(mocks.embedText).toHaveBeenCalledWith('cat');

        const opts = mocks.useTextEmbeddingOptions as EmbedOptions;
        opts.onSuccess({ queryText: 'cat', embedding: [1, 2, 3] });
        expect(get(embedding)).toEqual({ queryText: 'cat', embedding: [1, 2, 3] });
    });

    it('setText clears any active image before embedding', async () => {
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        await search.setText('cat');

        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('setText with empty string clears the embedding store', async () => {
        embedding.set({ queryText: 'old', embedding: [0] });
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        await search.setText('');

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('setText with whitespace clears the embedding store', async () => {
        embedding.set({ queryText: 'old', embedding: [0] });
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        await search.setText('   ');

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });

    it('routes onError from useTextEmbedding to toast', () => {
        useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        const opts = mocks.useTextEmbeddingOptions as EmbedOptions;
        opts.onError('boom');

        expect(mocks.toastError).toHaveBeenCalledWith(
            'Error',
            expect.objectContaining({ description: 'boom' })
        );
    });

    it('isPending reflects useTextEmbedding.isEmbedding', () => {
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        mocks.isEmbedding.set(true);
        expect(get(search.isPending)).toBe(true);

        mocks.isEmbedding.set(false);
        expect(get(search.isPending)).toBe(false);
    });

    it('isPending reflects useImageUpload.isUploading', () => {
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        mocks.isUploading.set(true);
        expect(get(search.isPending)).toBe(true);

        mocks.isUploading.set(false);
        expect(get(search.isPending)).toBe(false);
    });

    it('setEmbedding writes a precomputed vector and optional preview without uploading', () => {
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        search.setEmbedding({
            queryText: 'person-crop.png',
            embedding: [1, 0, 0],
            imagePreview: { name: 'person-crop.png', previewUrl: 'blob:crop' }
        });

        expect(mocks.clearImage).toHaveBeenCalled();
        expect(mocks.setPreview).toHaveBeenCalledWith('person-crop.png', 'blob:crop', true);
        expect(get(embedding)).toEqual({
            queryText: 'person-crop.png',
            embedding: [1, 0, 0]
        });
        expect(mocks.upload).not.toHaveBeenCalled();
    });

    it('setImage delegates to useImageUpload and writes embedding on success', async () => {
        const file = new File(['x'], 'sample.png', { type: 'image/png' });
        mocks.upload.mockResolvedValue(undefined);

        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        await search.setImage(file);

        expect(mocks.upload).toHaveBeenCalledWith(file);

        const opts = mocks.useImageUploadOptions as {
            onSuccess: (result: { fileName: string; embedding: number[] }) => void;
        };
        opts.onSuccess({ fileName: 'sample.png', embedding: [4, 5, 6] });
        expect(get(embedding)).toEqual({ queryText: 'sample.png', embedding: [4, 5, 6] });
    });

    it('image store mirrors useImageUpload name + preview', () => {
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        expect(get(search.image)).toBeUndefined();

        mocks.imageName.set('sample.png');
        mocks.previewUrl.set('blob:preview');

        expect(get(search.image)).toEqual({ name: 'sample.png', previewUrl: 'blob:preview' });
    });

    it('clear resets embedding and clears image upload state', () => {
        embedding.set({ queryText: 'foo', embedding: [1] });
        const search = useSearchEmbedding({ getCollectionId: () => 'collection-id', embedding });

        search.clear();

        expect(get(embedding)).toBeUndefined();
        expect(mocks.clearImage).toHaveBeenCalled();
    });

    describe('with a customer-hosted embedding service', () => {
        const readyService = () => ({
            servingUrl: 'https://gpu-box:8123',
            status: 'ready' as const,
            canSearchText: true,
            canSearchImage: true,
            textDisabledReason: undefined,
            imageDisabledReason: undefined,
            reprobe: vi.fn()
        });

        it('embeds text against the service instead of the backend', async () => {
            mocks.embedTextViaService.mockResolvedValue([7, 8, 9]);
            useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service: readyService()
            });

            const opts = mocks.useTextEmbeddingOptions as {
                getEmbed: () => ((p: { text: string }) => Promise<number[]>) | undefined;
            };
            const embed = opts.getEmbed();
            expect(embed).toBeDefined();
            await expect(embed!({ text: 'a red car' })).resolves.toEqual([7, 8, 9]);
            expect(mocks.embedTextViaService).toHaveBeenCalledWith({
                servingUrl: 'https://gpu-box:8123',
                text: 'a red car'
            });
        });

        it('embeds images against the service instead of the backend', async () => {
            mocks.embedImageViaService.mockResolvedValue([1, 1, 1]);
            const file = new File(['x'], 'query.png', { type: 'image/png' });
            useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service: readyService()
            });

            const opts = mocks.useImageUploadOptions as {
                getEmbed: () => ((p: { file: File }) => Promise<number[]>) | undefined;
            };
            await expect(opts.getEmbed()!({ file })).resolves.toEqual([1, 1, 1]);
            expect(mocks.embedImageViaService).toHaveBeenCalledWith({
                servingUrl: 'https://gpu-box:8123',
                file
            });
        });

        it('uses the backend when the collection has no service', () => {
            useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service: { ...readyService(), servingUrl: undefined, status: 'builtin' }
            });

            const textOpts = mocks.useTextEmbeddingOptions as { getEmbed: () => unknown };
            const imageOpts = mocks.useImageUploadOptions as { getEmbed: () => unknown };
            expect(textOpts.getEmbed()).toBeUndefined();
            expect(imageOpts.getEmbed()).toBeUndefined();
        });

        it('refuses a text search instead of falling back to the built-in model', async () => {
            const service = {
                ...readyService(),
                status: 'model-mismatch' as const,
                canSearchText: false,
                textDisabledReason: 'Search is unavailable: wrong model.'
            };
            const search = useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service
            });

            await search.setText('a red car');

            expect(mocks.embedText).not.toHaveBeenCalled();
            expect(mocks.toastError).toHaveBeenCalledWith('Error', {
                description: 'Search is unavailable: wrong model.'
            });
        });

        it('still clears the search when the query is emptied on a disabled service', async () => {
            embedding.set({ queryText: 'foo', embedding: [1] });
            const search = useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service: {
                    ...readyService(),
                    status: 'unreachable' as const,
                    canSearchText: false,
                    textDisabledReason: 'Search is unavailable: no response.'
                }
            });

            await search.setText('   ');

            expect(get(embedding)).toBeUndefined();
            expect(mocks.toastError).not.toHaveBeenCalled();
        });

        it('refuses an image search when the model cannot embed images', async () => {
            const file = new File(['x'], 'query.png', { type: 'image/png' });
            const search = useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service: {
                    ...readyService(),
                    canSearchImage: false,
                    imageDisabledReason: 'This model cannot embed images.'
                }
            });

            await search.setImage(file);

            expect(mocks.upload).not.toHaveBeenCalled();
            expect(mocks.toastError).toHaveBeenCalledWith('Error', {
                description: 'This model cannot embed images.'
            });
        });

        it('re-probes the service when a search fails', () => {
            const service = readyService();
            useSearchEmbedding({
                getCollectionId: () => 'collection-id',
                embedding,
                service
            });

            const opts = mocks.useTextEmbeddingOptions as EmbedOptions;
            opts.onError('boom');

            expect(service.reprobe).toHaveBeenCalled();
        });
    });
});
