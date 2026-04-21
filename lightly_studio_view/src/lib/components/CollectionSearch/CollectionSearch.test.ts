import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CollectionSearch from './CollectionSearch.svelte';

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
            set: (nextValue) => {
                value = nextValue;
                subscribers.forEach((subscriber) => subscriber(value));
            }
        };
    };

    return {
        activeImage: createStore<string | null>(null),
        previewUrl: createStore<string | null>(null),
        isUploading: createStore(false),
        dragOver: createStore(false),
        embedTextQuery: createStore({
            isError: false,
            isSuccess: false,
            error: null,
            data: [] as number[]
        }),
        uploadImage: vi.fn(),
        clearImage: vi.fn(),
        handleDragOver: vi.fn(),
        handleDragLeave: vi.fn(),
        handleDrop: vi.fn(),
        handlePaste: vi.fn(),
        handleFileSelect: vi.fn()
    };
});

vi.mock('$lib/hooks/useImageUpload', () => ({
    useImageUpload: () => ({
        activeImage: mocks.activeImage,
        previewUrl: mocks.previewUrl,
        isUploading: mocks.isUploading,
        uploadImage: mocks.uploadImage,
        clearImage: mocks.clearImage
    })
}));

vi.mock('$lib/hooks/useFileDrop', () => ({
    useFileDrop: () => ({
        dragOver: mocks.dragOver,
        handleDragOver: mocks.handleDragOver,
        handleDragLeave: mocks.handleDragLeave,
        handleDrop: mocks.handleDrop,
        handlePaste: mocks.handlePaste,
        handleFileSelect: mocks.handleFileSelect
    })
}));

vi.mock('$lib/hooks/useEmbedText/useEmbedText', () => ({
    useEmbedText: () => mocks.embedTextQuery
}));

describe('CollectionSearch', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.activeImage.set(null);
        mocks.previewUrl.set(null);
        mocks.isUploading.set(false);
        mocks.dragOver.set(false);
        mocks.embedTextQuery.set({
            isError: false,
            isSuccess: false,
            error: null,
            data: []
        });
    });

    it('renders text search input by default', () => {
        render(CollectionSearch, {
            props: {
                collectionId: 'collection-id',
                textEmbedding: undefined,
                setTextEmbedding: vi.fn()
            }
        });

        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });

    it('renders image search display when an image is active', () => {
        mocks.activeImage.set('query.png');

        render(CollectionSearch, {
            props: {
                collectionId: 'collection-id',
                textEmbedding: undefined,
                setTextEmbedding: vi.fn()
            }
        });

        expect(screen.getByText('query.png')).toBeInTheDocument();
        expect(screen.getByTestId('search-clear-button')).toBeInTheDocument();
    });

    it('clears embedding when image clear button is clicked', async () => {
        mocks.activeImage.set('query.png');
        const setTextEmbedding = vi.fn();

        render(CollectionSearch, {
            props: {
                collectionId: 'collection-id',
                textEmbedding: undefined,
                setTextEmbedding
            }
        });

        setTextEmbedding.mockClear();

        await fireEvent.click(screen.getByTestId('search-clear-button'));

        expect(setTextEmbedding).toHaveBeenCalledWith(undefined);
        expect(mocks.clearImage).toHaveBeenCalled();
    });
});
