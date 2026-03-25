import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import GridSearch from './GridSearch.svelte';

// Mock dependencies
vi.mock('$app/state', () => ({
    page: {
        params: { collection_id: 'test-collection-id' }
    }
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn()
    }
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: vi.fn()
}));

vi.mock('$lib/hooks/useEmbedText/useEmbedText', () => ({
    useEmbedText: vi.fn()
}));

vi.mock('$lib/hooks/useFileUpload/useFileUpload', () => ({
    useFileUpload: vi.fn()
}));

vi.mock('./hooks/useImageUploadHandlers/useImageUploadHandlers', () => ({
    useImageUploadHandlers: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    embedImageFromFileMutation: vi.fn()
}));

import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useEmbedText } from '$lib/hooks/useEmbedText/useEmbedText';
import { useFileUpload } from '$lib/hooks/useFileUpload/useFileUpload';
import { useImageUploadHandlers } from './hooks/useImageUploadHandlers/useImageUploadHandlers';

describe('GridSearch', () => {
    let mockSetTextEmbedding: ReturnType<typeof vi.fn>;
    let mockUploadFile: ReturnType<typeof vi.fn>;

    const setupDefaultMocks = () => {
        mockSetTextEmbedding = vi.fn();
        mockUploadFile = vi.fn().mockResolvedValue(undefined);

        (useGlobalStorage as ReturnType<typeof vi.fn>).mockReturnValue({
            textEmbedding: readable(undefined),
            setTextEmbedding: mockSetTextEmbedding
        });

        (useEmbedText as ReturnType<typeof vi.fn>).mockReturnValue(
            readable({
                isError: false,
                isSuccess: false,
                data: undefined,
                error: undefined
            })
        );

        (useFileUpload as ReturnType<typeof vi.fn>).mockReturnValue({
            isUploading: readable(false),
            uploadFile: mockUploadFile
        });

        (useImageUploadHandlers as ReturnType<typeof vi.fn>).mockReturnValue({
            dragOver: readable(false),
            handleDragOver: vi.fn(),
            handleDragLeave: vi.fn(),
            handleDrop: vi.fn(),
            handlePaste: vi.fn(),
            handleFileSelect: vi.fn()
        });
    };

    beforeEach(setupDefaultMocks);
    afterEach(() => vi.clearAllMocks());

    it('renders with correct aria attributes', () => {
        const { container } = render(GridSearch);

        const region = container.querySelector('[role="region"]');
        expect(region).toBeInTheDocument();
        expect(region).toHaveAttribute('aria-label', 'Search by image or text');
    });

    it('shows SearchInput initially', () => {
        render(GridSearch);
        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });

    it('calls drag handlers on drag events', async () => {
        const mockHandleDragOver = vi.fn();
        const mockHandleDragLeave = vi.fn();
        const mockHandleDrop = vi.fn();

        (useImageUploadHandlers as ReturnType<typeof vi.fn>).mockReturnValue({
            dragOver: readable(false),
            handleDragOver: mockHandleDragOver,
            handleDragLeave: mockHandleDragLeave,
            handleDrop: mockHandleDrop,
            handlePaste: vi.fn(),
            handleFileSelect: vi.fn()
        });

        const { container } = render(GridSearch);
        const region = container.querySelector('[role="region"]')!;

        await fireEvent.dragOver(region);
        expect(mockHandleDragOver).toHaveBeenCalled();

        await fireEvent.dragLeave(region);
        expect(mockHandleDragLeave).toHaveBeenCalled();

        await fireEvent.drop(region);
        expect(mockHandleDrop).toHaveBeenCalled();
    });

    it('handles paste event', async () => {
        const mockHandlePaste = vi.fn();

        (useImageUploadHandlers as ReturnType<typeof vi.fn>).mockReturnValue({
            dragOver: readable(false),
            handleDragOver: vi.fn(),
            handleDragLeave: vi.fn(),
            handleDrop: vi.fn(),
            handlePaste: mockHandlePaste,
            handleFileSelect: vi.fn()
        });

        render(GridSearch);
        await fireEvent.paste(screen.getByTestId('text-embedding-search-input'));

        expect(mockHandlePaste).toHaveBeenCalled();
    });

    it('renders hidden file input with correct attributes', () => {
        const { container } = render(GridSearch);

        const fileInput = container.querySelector('input[type="file"]');
        expect(fileInput).toBeInTheDocument();
        expect(fileInput).toHaveClass('hidden');
        expect(fileInput).toHaveAttribute('accept', 'image/*');
    });

    it('disables file input when uploading', () => {
        (useFileUpload as ReturnType<typeof vi.fn>).mockReturnValue({
            isUploading: readable(true),
            uploadFile: mockUploadFile
        });

        const { container } = render(GridSearch);
        expect(container.querySelector('input[type="file"]')).toBeDisabled();
    });

    it('handles file select event', async () => {
        const mockHandleFileSelect = vi.fn();

        (useImageUploadHandlers as ReturnType<typeof vi.fn>).mockReturnValue({
            dragOver: readable(false),
            handleDragOver: vi.fn(),
            handleDragLeave: vi.fn(),
            handleDrop: vi.fn(),
            handlePaste: vi.fn(),
            handleFileSelect: mockHandleFileSelect
        });

        const { container } = render(GridSearch);
        await fireEvent.change(container.querySelector('input[type="file"]')!);

        expect(mockHandleFileSelect).toHaveBeenCalled();
    });

    it('passes drag over state to child components', () => {
        (useImageUploadHandlers as ReturnType<typeof vi.fn>).mockReturnValue({
            dragOver: writable(true),
            handleDragOver: vi.fn(),
            handleDragLeave: vi.fn(),
            handleDrop: vi.fn(),
            handlePaste: vi.fn(),
            handleFileSelect: vi.fn()
        });

        const { container } = render(GridSearch);
        expect(container.querySelector('.ring-2.ring-primary')).toBeInTheDocument();
    });

    it('passes uploading state to SearchInput', () => {
        (useFileUpload as ReturnType<typeof vi.fn>).mockReturnValue({
            isUploading: readable(true),
            uploadFile: mockUploadFile
        });

        render(GridSearch);
        const input = screen.getByPlaceholderText('Uploading...');
        expect(input).toBeInTheDocument();
        expect(input).toBeDisabled();
    });

    it('initializes with textEmbedding from storage', () => {
        (useGlobalStorage as ReturnType<typeof vi.fn>).mockReturnValue({
            textEmbedding: readable({ queryText: 'saved query', embedding: [1, 2, 3] }),
            setTextEmbedding: mockSetTextEmbedding
        });

        render(GridSearch);
        expect(screen.getByDisplayValue('saved query')).toBeInTheDocument();
    });

    it('configures useFileUpload with correct parameters', () => {
        render(GridSearch);

        const config = (useFileUpload as ReturnType<typeof vi.fn>).mock.calls[0][0];
        expect(config.maxFileSize).toBe(50 * 1024 * 1024);
        expect(config.acceptedTypes).toEqual(['image/']);
        expect(config.onSuccess).toBeDefined();
        expect(config.onError).toBeDefined();
    });
});
