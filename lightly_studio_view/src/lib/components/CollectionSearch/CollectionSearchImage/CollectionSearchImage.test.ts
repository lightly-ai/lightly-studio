import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CollectionSearchImage from './CollectionSearchImage.svelte';

describe('CollectionSearchImage', () => {
    const baseProps = {
        name: 'query.png',
        onClear: vi.fn()
    };
    it('renders file name and clear button test id', () => {
        render(CollectionSearchImage, {
            props: baseProps
        });

        expect(screen.getByText('query.png')).toBeInTheDocument();
        expect(screen.getByTestId('search-clear-button')).toBeInTheDocument();
    });

    it('calls clear handler on click', async () => {
        const onClear = vi.fn();
        render(CollectionSearchImage, {
            props: {
                ...baseProps,
                onClear
            }
        });

        await fireEvent.click(screen.getByTestId('search-clear-button'));

        expect(onClear).toHaveBeenCalledOnce();
    });

    it('shows image preview when src is provided', () => {
        const src =
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA' +
            'AAAFCAYAAACNbyblAAAAHElEQVQI12P4' +
            '//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==';
        render(CollectionSearchImage, {
            props: {
                ...baseProps,
                src
            }
        });

        const img = screen.getByAltText('Search preview') as HTMLImageElement;
        expect(img).toBeInTheDocument();
        expect(img.src).toBe(src);
    });
});
