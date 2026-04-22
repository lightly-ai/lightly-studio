import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CollectionSearchInput from './CollectionSearchInput.svelte';

describe('CollectionSearchInput', () => {
    it('renders required text search input test id', () => {
        render(CollectionSearchInput, {
            props: {
                value: '',
                inputProps: { disabled: false, onkeydown: vi.fn(), onpaste: vi.fn() },
                showOutline: false,
                onUploadClick: vi.fn()
            }
        });

        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });

    it('renders clear button with required test id when submitted query exists', () => {
        render(CollectionSearchInput, {
            props: {
                value: 'dog',
                inputProps: { disabled: false, onkeydown: vi.fn(), onpaste: vi.fn() },
                showOutline: false,
                onUploadClick: vi.fn()
            }
        });

        const clearButton = screen.getByTestId('search-clear-button');
        expect(clearButton).toBeInTheDocument();
    });

    it('updates value, clears it, and calls upload handler', async () => {
        const onUploadClick = vi.fn();

        render(CollectionSearchInput, {
            props: {
                value: 'cat',
                inputProps: { disabled: false, onkeydown: vi.fn(), onpaste: vi.fn() },
                showOutline: false,
                onUploadClick
            }
        });

        const input = screen.getByTestId('text-embedding-search-input') as HTMLInputElement;

        await fireEvent.input(input, {
            target: { value: 'cats' }
        });
        await fireEvent.click(screen.getByTestId('search-clear-button'));
        await fireEvent.click(screen.getByTitle('Upload image for search'));

        expect(input.value).toBe('');
        expect(onUploadClick).toHaveBeenCalledOnce();
    });

    it('applies disabled state consistently when provided via inputProps', () => {
        render(CollectionSearchInput, {
            props: {
                value: '',
                inputProps: { disabled: true, onkeydown: vi.fn(), onpaste: vi.fn() },
                showOutline: false,
                onUploadClick: vi.fn()
            }
        });

        const input = screen.getByTestId('text-embedding-search-input') as HTMLInputElement;
        const uploadButton = screen.getByTitle('Upload image for search');

        expect(input).toBeDisabled();
        expect(uploadButton).toBeDisabled();
    });
});
