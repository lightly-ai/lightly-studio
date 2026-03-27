import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import { useImageUploadHandlers } from './useImageUploadHandlers';

// Mock DOM APIs not available in vitest environment
class MockDataTransfer {
    private _files: File[] = [];
    items: { type: string; getAsFile: () => File | null }[] = [];

    get files(): File[] {
        return this._files;
    }

    set files(value: File[]) {
        this._files = value;
    }
}

class MockDragEvent extends Event {
    dataTransfer: MockDataTransfer | null = null;

    constructor(type: string, init?: { dataTransfer?: MockDataTransfer }) {
        super(type);
        this.dataTransfer = init?.dataTransfer || null;
    }

    preventDefault() {
        // Mock implementation
    }
}

class MockClipboardEvent extends Event {
    clipboardData: MockDataTransfer | null = null;

    constructor(type: string, init?: { clipboardData?: MockDataTransfer }) {
        super(type);
        this.clipboardData = init?.clipboardData || null;
    }

    preventDefault() {
        // Mock implementation
    }
}

describe('useImageUploadHandlers', () => {
    let mockUploadFile: ReturnType<typeof vi.fn>;
    let mockSetActiveImage: ReturnType<typeof vi.fn>;
    let mockSetPreviewUrl: ReturnType<typeof vi.fn>;
    let mockOnError: ReturnType<typeof vi.fn>;
    let originalCreateObjectURL: typeof URL.createObjectURL;
    let originalRevokeObjectURL: typeof URL.revokeObjectURL;

    beforeEach(() => {
        mockUploadFile = vi.fn().mockResolvedValue(undefined);
        mockSetActiveImage = vi.fn();
        mockSetPreviewUrl = vi.fn();
        mockOnError = vi.fn();

        // Mock URL.createObjectURL and revokeObjectURL
        originalCreateObjectURL = URL.createObjectURL;
        originalRevokeObjectURL = URL.revokeObjectURL;
        URL.createObjectURL = vi.fn(() => 'blob:mock-url');
        URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        URL.createObjectURL = originalCreateObjectURL;
        URL.revokeObjectURL = originalRevokeObjectURL;
    });

    it('should initialize with dragOver set to false', () => {
        const { dragOver } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        expect(get(dragOver)).toBe(false);
    });

    it('should set dragOver to true on handleDragOver', () => {
        const { dragOver, handleDragOver } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const event = new MockDragEvent('dragover');
        const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

        handleDragOver(event as unknown as DragEvent);

        expect(get(dragOver)).toBe(true);
        expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should set dragOver to false on handleDragLeave', () => {
        const { dragOver, handleDragOver, handleDragLeave } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const dragOverEvent = new MockDragEvent('dragover');
        handleDragOver(dragOverEvent as unknown as DragEvent);

        const dragLeaveEvent = new MockDragEvent('dragleave');
        const preventDefaultSpy = vi.spyOn(dragLeaveEvent, 'preventDefault');

        handleDragLeave(dragLeaveEvent as unknown as DragEvent);

        expect(get(dragOver)).toBe(false);
        expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('should handle drop with image file', async () => {
        const { dragOver, handleDrop } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const file = new File(['content'], 'test.png', { type: 'image/png' });
        const dataTransfer = new MockDataTransfer();
        dataTransfer.files = [file];

        const event = new MockDragEvent('drop', { dataTransfer });
        const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

        await handleDrop(event as unknown as DragEvent);

        expect(get(dragOver)).toBe(false);
        expect(preventDefaultSpy).toHaveBeenCalled();
        expect(mockSetActiveImage).toHaveBeenCalledWith('test.png');
        expect(mockSetPreviewUrl).toHaveBeenCalledWith('blob:mock-url');
        expect(mockUploadFile).toHaveBeenCalledWith(file);
        expect(mockOnError).not.toHaveBeenCalled();
    });

    it('should show error when dropping non-image file', async () => {
        const { handleDrop } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
        const dataTransfer = new MockDataTransfer();
        dataTransfer.files = [file];

        const event = new MockDragEvent('drop', { dataTransfer });
        await handleDrop(event as unknown as DragEvent);

        expect(mockOnError).toHaveBeenCalledWith('Please drop an image file.');
        expect(mockUploadFile).not.toHaveBeenCalled();
    });

    it('should handle paste with image from clipboard files', async () => {
        const { handlePaste } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const file = new File(['content'], 'pasted-image.png', { type: 'image/png' });
        const dataTransfer = new MockDataTransfer();
        dataTransfer.files = [file];

        const event = new MockClipboardEvent('paste', {
            clipboardData: dataTransfer
        });
        const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

        await handlePaste(event as unknown as ClipboardEvent);

        expect(preventDefaultSpy).toHaveBeenCalled();
        expect(mockSetActiveImage).toHaveBeenCalledWith('pasted-image.png');
        expect(mockSetPreviewUrl).toHaveBeenCalledWith('blob:mock-url');
        expect(mockUploadFile).toHaveBeenCalledWith(file);
    });

    it('should handle paste with image from clipboard items', async () => {
        const { handlePaste } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const file = new File(['screenshot'], 'screenshot.png', { type: 'image/png' });

        // Mock ClipboardEvent with items but no files
        const mockClipboardData = {
            files: [],
            items: [
                {
                    type: 'image/png',
                    getAsFile: () => file
                }
            ]
        };

        const event = {
            clipboardData: mockClipboardData,
            preventDefault: vi.fn()
        } as unknown as ClipboardEvent;

        await handlePaste(event);

        expect(event.preventDefault).toHaveBeenCalled();
        expect(mockSetActiveImage).toHaveBeenCalledWith('screenshot.png');
        expect(mockUploadFile).toHaveBeenCalledWith(file);
    });

    it('should not process paste event without image data', async () => {
        const { handlePaste } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const dataTransfer = new MockDataTransfer();
        const event = new MockClipboardEvent('paste', {
            clipboardData: dataTransfer
        });

        await handlePaste(event as unknown as ClipboardEvent);

        expect(mockUploadFile).not.toHaveBeenCalled();
        expect(mockSetActiveImage).not.toHaveBeenCalled();
    });

    it('should handle file select from input', async () => {
        const { handleFileSelect } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const file = new File(['content'], 'selected.jpg', { type: 'image/jpeg' });
        const mockFiles = [file] as unknown as FileList;

        const input = {
            value: 'selected.jpg',
            files: mockFiles
        };

        const event = { target: input } as unknown as Event;

        await handleFileSelect(event);

        expect(mockSetActiveImage).toHaveBeenCalledWith('selected.jpg');
        expect(mockUploadFile).toHaveBeenCalledWith(file);
        expect(input.value).toBe('');
    });

    it('should not upload if no file is selected', async () => {
        const { handleFileSelect } = useImageUploadHandlers({
            uploadFile: mockUploadFile,
            setActiveImage: mockSetActiveImage,
            setPreviewUrl: mockSetPreviewUrl,
            onError: mockOnError
        });

        const input = document.createElement('input');
        input.type = 'file';

        const event = { target: input } as unknown as Event;

        await handleFileSelect(event);

        expect(mockUploadFile).not.toHaveBeenCalled();
    });
});
