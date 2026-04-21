import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SearchInput from './SearchInput.svelte';

describe('SearchInput', () => {
    it('renders required text search input test id', () => {
        render(SearchInput, {
            props: {
                queryText: '',
                submittedQueryText: '',
                isUploading: false,
                dragOver: false,
                onKeyDown: vi.fn(),
                onPaste: vi.fn(),
                onClear: vi.fn(),
                onUploadClick: vi.fn(),
                onQueryTextChange: vi.fn()
            }
        });

        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });

    it('renders clear button with required test id when submitted query exists', () => {
        const onClear = vi.fn();
        render(SearchInput, {
            props: {
                queryText: 'dog',
                submittedQueryText: 'dog',
                isUploading: false,
                dragOver: false,
                onKeyDown: vi.fn(),
                onPaste: vi.fn(),
                onClear,
                onUploadClick: vi.fn(),
                onQueryTextChange: vi.fn()
            }
        });

        const clearButton = screen.getByTestId('search-clear-button');
        expect(clearButton).toBeInTheDocument();
    });

    it('calls handlers for input, clear and upload actions', async () => {
        const onClear = vi.fn();
        const onUploadClick = vi.fn();
        const onQueryTextChange = vi.fn();

        render(SearchInput, {
            props: {
                queryText: 'cat',
                submittedQueryText: 'cat',
                isUploading: false,
                dragOver: false,
                onKeyDown: vi.fn(),
                onPaste: vi.fn(),
                onClear,
                onUploadClick,
                onQueryTextChange
            }
        });

        await fireEvent.input(screen.getByTestId('text-embedding-search-input'), {
            target: { value: 'cats' }
        });
        await fireEvent.click(screen.getByTestId('search-clear-button'));
        await fireEvent.click(screen.getByTitle('Upload image for search'));

        expect(onQueryTextChange).toHaveBeenCalled();
        expect(onClear).toHaveBeenCalledOnce();
        expect(onUploadClick).toHaveBeenCalledOnce();
    });
});
