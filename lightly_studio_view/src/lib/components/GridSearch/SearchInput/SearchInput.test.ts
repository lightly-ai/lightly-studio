import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import SearchInput from './SearchInput.svelte';

describe('SearchInput', () => {
    const defaultProps = {
        queryText: '',
        isUploading: false,
        dragOver: false,
        onkeydown: vi.fn(),
        onpaste: vi.fn(),
        triggerFileInput: vi.fn()
    };

    it('renders with correct placeholder when not uploading', () => {
        render(SearchInput, { props: defaultProps });
        expect(
            screen.getByPlaceholderText('Search samples by description or image')
        ).toBeInTheDocument();
    });

    it('renders with uploading placeholder when isUploading is true', () => {
        render(SearchInput, { props: { ...defaultProps, isUploading: true } });
        expect(screen.getByPlaceholderText('Uploading...')).toBeInTheDocument();
    });

    it('displays queryText value in input', () => {
        render(SearchInput, { props: { ...defaultProps, queryText: 'test query' } });
        expect(screen.getByDisplayValue('test query')).toBeInTheDocument();
    });

    it('applies ring style when dragOver is true', () => {
        const { container } = render(SearchInput, { props: { ...defaultProps, dragOver: true } });
        expect(container.querySelector('.ring-2.ring-primary')).toBeInTheDocument();
    });

    it('disables input when isUploading is true', () => {
        render(SearchInput, { props: { ...defaultProps, isUploading: true } });
        expect(screen.getByTestId('text-embedding-search-input')).toBeDisabled();
    });

    it('calls onkeydown when key is pressed', async () => {
        const onkeydown = vi.fn();
        render(SearchInput, { props: { ...defaultProps, onkeydown } });

        await fireEvent.keyDown(screen.getByTestId('text-embedding-search-input'), {
            key: 'Enter'
        });
        expect(onkeydown).toHaveBeenCalledOnce();
    });

    it('calls onpaste when content is pasted', async () => {
        const onpaste = vi.fn();
        render(SearchInput, { props: { ...defaultProps, onpaste } });

        await fireEvent.paste(screen.getByTestId('text-embedding-search-input'));
        expect(onpaste).toHaveBeenCalledOnce();
    });

    it('calls triggerFileInput when image icon button is clicked', async () => {
        const triggerFileInput = vi.fn();
        render(SearchInput, { props: { ...defaultProps, triggerFileInput } });

        await fireEvent.click(screen.getByTitle('Upload image for search'));
        expect(triggerFileInput).toHaveBeenCalledOnce();
    });

    it('disables image upload button when isUploading is true', () => {
        render(SearchInput, { props: { ...defaultProps, isUploading: true } });
        expect(screen.getByTitle('Upload image for search')).toBeDisabled();
    });

    it('renders both search and image icons', () => {
        const { container } = render(SearchInput, { props: defaultProps });
        expect(container.querySelectorAll('svg').length).toBe(2);
    });

    it('has correct testid attribute', () => {
        render(SearchInput, { props: defaultProps });
        expect(screen.getByTestId('text-embedding-search-input')).toBeInTheDocument();
    });
});
