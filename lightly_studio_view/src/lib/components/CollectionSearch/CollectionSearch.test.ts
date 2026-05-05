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
        dragOver: createStore(false),
        handleDragOver: vi.fn(),
        handleDragLeave: vi.fn(),
        handleDrop: vi.fn(),
        handlePaste: vi.fn(),
        handleFileSelect: vi.fn()
    };
});

vi.mock('$lib/hooks/useFileDrop/useFileDrop', () => ({
    useFileDrop: () => ({
        dragOver: mocks.dragOver,
        handleDragOver: mocks.handleDragOver,
        handleDragLeave: mocks.handleDragLeave,
        handleDrop: mocks.handleDrop,
        handlePaste: mocks.handlePaste,
        handleFileSelect: mocks.handleFileSelect
    })
}));

const baseProps = () => ({
    image: undefined,
    onSubmitText: vi.fn(),
    onSubmitFile: vi.fn(),
    onClear: vi.fn(),
    onError: vi.fn()
});

describe('CollectionSearch', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.dragOver.set(false);
    });

    it('renders text search input by default', () => {
        render(CollectionSearch, { props: baseProps() });

        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });

    it('renders image chip when image is set', () => {
        render(CollectionSearch, {
            props: {
                ...baseProps(),
                image: { name: 'query.png', previewUrl: 'blob:preview' }
            }
        });

        expect(screen.getByText('query.png')).toBeInTheDocument();
        expect(screen.getByTestId('search-clear-button')).toBeInTheDocument();
    });

    it('calls onClear when image clear button is clicked', async () => {
        const props = {
            ...baseProps(),
            image: { name: 'query.png', previewUrl: 'blob:preview' }
        };

        render(CollectionSearch, { props });

        await fireEvent.click(screen.getByTestId('search-clear-button'));

        expect(props.onClear).toHaveBeenCalledTimes(1);
    });
});
