import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useFileDrop } from '$lib/hooks';

describe('useFileDrop', () => {
    const onFile = vi.fn();
    const onError = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('sets dragOver state during drag events', () => {
        const drop = useFileDrop({ onFile, onError });

        const preventDefault = vi.fn();
        drop.handleDragOver({ preventDefault } as unknown as DragEvent);
        expect(preventDefault).toHaveBeenCalledOnce();
        expect(get(drop.dragOver)).toBe(true);

        drop.handleDragLeave({ preventDefault } as unknown as DragEvent);
        expect(get(drop.dragOver)).toBe(false);
    });

    it('uploads dropped image files', async () => {
        const drop = useFileDrop({ onFile, onError });
        const file = new File(['image'], 'image.png', { type: 'image/png' });

        await drop.handleDrop({
            preventDefault: vi.fn(),
            dataTransfer: { files: [file] }
        } as unknown as DragEvent);

        expect(onFile).toHaveBeenCalledWith(file);
        expect(onError).not.toHaveBeenCalled();
        expect(get(drop.dragOver)).toBe(false);
    });

    it('rejects non-image drops', async () => {
        const drop = useFileDrop({ onFile, onError });
        const file = new File(['text'], 'file.txt', { type: 'text/plain' });

        await drop.handleDrop({
            preventDefault: vi.fn(),
            dataTransfer: { files: [file] }
        } as unknown as DragEvent);

        expect(onError).toHaveBeenCalledWith('Please drop an image file.');
        expect(onFile).not.toHaveBeenCalled();
    });

    it('uploads image from clipboard files', async () => {
        const drop = useFileDrop({ onFile, onError });
        const preventDefault = vi.fn();
        const file = new File(['image'], 'clipboard.png', { type: 'image/png' });

        await drop.handlePaste({
            preventDefault,
            clipboardData: {
                files: [file],
                items: []
            }
        } as unknown as ClipboardEvent);

        expect(preventDefault).toHaveBeenCalledOnce();
        expect(onFile).toHaveBeenCalledWith(file);
    });

    it('resets file input value after file selection', async () => {
        const drop = useFileDrop({ onFile, onError });
        const file = new File(['image'], 'upload.png', { type: 'image/png' });
        const target = {
            files: [file],
            value: 'non-empty'
        };

        await drop.handleFileSelect({ target } as unknown as Event);

        expect(onFile).toHaveBeenCalledWith(file);
        expect(target.value).toBe('');
    });
});
