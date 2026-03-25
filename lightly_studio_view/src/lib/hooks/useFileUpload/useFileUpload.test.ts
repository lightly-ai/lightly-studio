import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useFileUpload } from './useFileUpload';

vi.mock('@tanstack/svelte-query', async () => {
    const actual = await vi.importActual('@tanstack/svelte-query');
    return {
        ...actual,
        createMutation: vi.fn()
    };
});

describe('useFileUpload', () => {
    const maxFileSize = 50 * 1024 * 1024; // 50MB
    let mockMutateAsync: ReturnType<typeof vi.fn>;
    let mockMutation: { isPending: boolean; mutateAsync: typeof mockMutateAsync };
    let mockMutationFn: ReturnType<typeof vi.fn>;

    beforeEach(async () => {
        const { createMutation } = await import('@tanstack/svelte-query');

        mockMutateAsync = vi.fn();
        mockMutation = {
            isPending: false,
            mutateAsync: mockMutateAsync
        };

        mockMutationFn = vi.fn(() => ({ mutationFn: vi.fn() }));

        // Mock createMutation to return a store-like object with the mutation
        (createMutation as ReturnType<typeof vi.fn>).mockImplementation(() => {
            return {
                subscribe: vi.fn((callback) => {
                    callback(mockMutation);
                    return { unsubscribe: vi.fn() };
                }),
                mutateAsync: mockMutateAsync,
                isPending: false
            };
        });
    });

    it('should initialize with isUploading set to false', () => {
        const { isUploading } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables: (file) => ({ body: { file } })
        });

        expect(get(isUploading)).toBe(false);
    });

    it('should reject files larger than maxFileSize', async () => {
        const onError = vi.fn();
        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize: 1024, // 1KB
            buildMutationVariables: (file) => ({ body: { file } }),
            onError
        });

        const largeFile = new File(['x'.repeat(2048)], 'large.png', { type: 'image/png' });
        await uploadFile(largeFile);

        expect(onError).toHaveBeenCalledWith('File is too large. Maximum size is 0MB.');
        expect(mockMutateAsync).not.toHaveBeenCalled();
    });

    it('should upload a file successfully', async () => {
        const mockResponse = [0.1, 0.2, 0.3, 0.4];
        const collectionId = 'test-collection-123';
        mockMutateAsync.mockResolvedValue(mockResponse);

        const onSuccess = vi.fn();
        const buildMutationVariables = vi.fn((file) => ({
            body: { file },
            path: { collection_id: collectionId }
        }));

        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables,
            onSuccess
        });

        const file = new File(['content'], 'test.png', { type: 'image/png' });
        await uploadFile(file);

        expect(buildMutationVariables).toHaveBeenCalledWith(file);
        expect(onSuccess).toHaveBeenCalledWith(mockResponse);
        expect(mockMutateAsync).toHaveBeenCalledWith({
            body: { file },
            path: { collection_id: collectionId }
        });
    });

    it('should pass mutation params to mutation function', async () => {
        const mockResponse = [0.5, 0.6];
        const mutationParams = { path: { collection_id: 'abc' } };
        mockMutateAsync.mockResolvedValue(mockResponse);

        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            mutationParams,
            maxFileSize,
            buildMutationVariables: (file) => ({ body: { file } })
        });

        expect(mockMutationFn).toHaveBeenCalledWith(mutationParams);

        const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' });
        await uploadFile(file);

        expect(mockMutateAsync).toHaveBeenCalled();
    });

    it('should handle upload errors', async () => {
        mockMutateAsync.mockRejectedValue(new Error('Upload failed'));

        const onError = vi.fn();
        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables: (file) => ({ body: { file } }),
            onError
        });

        const file = new File(['content'], 'test.png', { type: 'image/png' });
        await uploadFile(file);

        expect(onError).toHaveBeenCalledWith('Upload failed');
    });

    it('should handle unknown errors', async () => {
        mockMutateAsync.mockRejectedValue('Unknown error');

        const onError = vi.fn();
        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables: (file) => ({ body: { file } }),
            onError
        });

        const file = new File(['content'], 'test.png', { type: 'image/png' });
        await uploadFile(file);

        expect(onError).toHaveBeenCalledWith('Failed to upload file');
    });

    it('should work without optional callbacks', async () => {
        mockMutateAsync.mockResolvedValue([0.1, 0.2]);

        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables: (file) => ({ body: { file } })
        });

        const file = new File(['content'], 'test.png', { type: 'image/png' });

        // Should not throw even without callbacks
        await expect(uploadFile(file)).resolves.toBeUndefined();
    });

    it('should work with custom mutation variables builder', async () => {
        const mockResponse = { success: true };
        mockMutateAsync.mockResolvedValue(mockResponse);

        const customBuilder = vi.fn((file) => ({
            customField: file.name,
            anotherField: { data: file }
        }));

        const { uploadFile } = useFileUpload({
            mutationFn: mockMutationFn,
            maxFileSize,
            buildMutationVariables: customBuilder
        });

        const file = new File(['content'], 'custom.png', { type: 'image/png' });
        await uploadFile(file);

        expect(customBuilder).toHaveBeenCalledWith(file);
        expect(mockMutateAsync).toHaveBeenCalledWith({
            customField: 'custom.png',
            anotherField: { data: file }
        });
    });

    describe('acceptedTypes', () => {
        it('should accept all file types when acceptedTypes is not provided', async () => {
            mockMutateAsync.mockResolvedValue([0.1, 0.2]);

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } })
            });

            const pdfFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            await uploadFile(pdfFile);

            expect(mockMutateAsync).toHaveBeenCalled();
        });

        it('should accept files matching MIME type pattern (image/)', async () => {
            mockMutateAsync.mockResolvedValue([0.1, 0.2]);

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['image/']
            });

            const imageFile = new File(['content'], 'test.png', { type: 'image/png' });
            await uploadFile(imageFile);

            expect(mockMutateAsync).toHaveBeenCalled();
        });

        it('should reject files not matching MIME type pattern', async () => {
            const onError = vi.fn();
            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['image/'],
                onError
            });

            const videoFile = new File(['content'], 'test.mp4', { type: 'video/mp4' });
            await uploadFile(videoFile);

            expect(onError).toHaveBeenCalledWith('File type not accepted. Accepted types: image/');
            expect(mockMutateAsync).not.toHaveBeenCalled();
        });

        it('should accept files matching file extension', async () => {
            mockMutateAsync.mockResolvedValue({ data: 'success' });

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['.pdf', '.docx']
            });

            const pdfFile = new File(['content'], 'document.pdf', { type: 'application/pdf' });
            await uploadFile(pdfFile);

            expect(mockMutateAsync).toHaveBeenCalled();
        });

        it('should reject files not matching file extension', async () => {
            const onError = vi.fn();
            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['.pdf', '.docx'],
                onError
            });

            const imageFile = new File(['content'], 'image.png', { type: 'image/png' });
            await uploadFile(imageFile);

            expect(onError).toHaveBeenCalledWith(
                'File type not accepted. Accepted types: .pdf, .docx'
            );
            expect(mockMutateAsync).not.toHaveBeenCalled();
        });

        it('should accept files matching exact MIME type', async () => {
            mockMutateAsync.mockResolvedValue([0.1]);

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['image/jpeg', 'image/png']
            });

            const jpegFile = new File(['content'], 'photo.jpg', { type: 'image/jpeg' });
            await uploadFile(jpegFile);

            expect(mockMutateAsync).toHaveBeenCalled();
        });

        it('should reject files not matching exact MIME type', async () => {
            const onError = vi.fn();
            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['image/jpeg', 'image/png'],
                onError
            });

            const gifFile = new File(['content'], 'animation.gif', { type: 'image/gif' });
            await uploadFile(gifFile);

            expect(onError).toHaveBeenCalledWith(
                'File type not accepted. Accepted types: image/jpeg, image/png'
            );
            expect(mockMutateAsync).not.toHaveBeenCalled();
        });

        it('should handle mixed acceptedTypes (MIME patterns, extensions, exact types)', async () => {
            mockMutateAsync.mockResolvedValue({ success: true });

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['image/', '.pdf', 'application/json']
            });

            const imageFile = new File(['content'], 'photo.png', { type: 'image/png' });
            const pdfFile = new File(['content'], 'doc.pdf', { type: 'application/pdf' });
            const jsonFile = new File(['{}'], 'data.json', { type: 'application/json' });

            await uploadFile(imageFile);
            await uploadFile(pdfFile);
            await uploadFile(jsonFile);

            expect(mockMutateAsync).toHaveBeenCalledTimes(3);
        });

        it('should be case-insensitive for file extensions', async () => {
            mockMutateAsync.mockResolvedValue({ success: true });

            const { uploadFile } = useFileUpload({
                mutationFn: mockMutationFn,
                maxFileSize,
                buildMutationVariables: (file) => ({ body: { file } }),
                acceptedTypes: ['.PDF']
            });

            const pdfFile = new File(['content'], 'document.pdf', { type: 'application/pdf' });
            await uploadFile(pdfFile);

            expect(mockMutateAsync).toHaveBeenCalled();
        });
    });
});
