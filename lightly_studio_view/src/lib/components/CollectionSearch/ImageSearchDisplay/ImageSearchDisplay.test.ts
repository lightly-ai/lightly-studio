import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ImageSearchDisplay from './ImageSearchDisplay.svelte';

describe('ImageSearchDisplay', () => {
    it('renders file name and clear button test id', () => {
        render(ImageSearchDisplay, {
            props: {
                activeImage: 'query.png',
                previewUrl: null,
                dragOver: false,
                onClear: vi.fn()
            }
        });

        expect(screen.getByText('query.png')).toBeInTheDocument();
        expect(screen.getByTestId('search-clear-button')).toBeInTheDocument();
    });

    it('calls clear handler on click', async () => {
        const onClear = vi.fn();
        render(ImageSearchDisplay, {
            props: {
                activeImage: 'query.png',
                previewUrl: null,
                dragOver: false,
                onClear
            }
        });

        await fireEvent.click(screen.getByTestId('search-clear-button'));

        expect(onClear).toHaveBeenCalledOnce();
    });
});
