import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import ActiveSearchDisplay from './ActiveSearchDisplay.svelte';

describe('ActiveSearchDisplay', () => {
    const defaultProps = {
        activeImage: null,
        submittedQueryText: '',
        previewUrl: null,
        dragOver: false,
        onClearImage: vi.fn(),
        onClearText: vi.fn()
    };

    it('renders with text query', () => {
        render(ActiveSearchDisplay, {
            props: { ...defaultProps, submittedQueryText: 'test search query' }
        });
        expect(screen.getByText('test search query')).toBeInTheDocument();
    });

    it('renders with active image and filename', () => {
        render(ActiveSearchDisplay, { props: { ...defaultProps, activeImage: 'test-image.jpg' } });
        expect(screen.getByText('test-image.jpg')).toBeInTheDocument();
    });

    it('renders image preview when previewUrl is provided', () => {
        render(ActiveSearchDisplay, {
            props: {
                ...defaultProps,
                activeImage: 'test-image.jpg',
                previewUrl: 'data:image/png;base64,test'
            }
        });

        const img = screen.getByAltText('Search preview');
        expect(img).toBeInTheDocument();
        expect(img).toHaveAttribute('src', 'data:image/png;base64,test');
    });

    it('renders image icon when no preview is available', () => {
        const { container } = render(ActiveSearchDisplay, {
            props: { ...defaultProps, activeImage: 'test-image.jpg' }
        });
        expect(container.querySelector('svg')).toBeInTheDocument();
    });

    it('applies ring style when dragOver is true', () => {
        const { container } = render(ActiveSearchDisplay, {
            props: { ...defaultProps, submittedQueryText: 'test', dragOver: true }
        });
        expect(container.querySelector('.ring-2.ring-primary')).toBeInTheDocument();
    });

    it('calls onClearImage when clear button is clicked with image', async () => {
        const onClearImage = vi.fn();
        render(ActiveSearchDisplay, {
            props: { ...defaultProps, activeImage: 'test-image.jpg', onClearImage }
        });

        await fireEvent.click(screen.getByTestId('search-clear-button'));
        expect(onClearImage).toHaveBeenCalledOnce();
    });

    it('calls onClearText when text button is clicked', async () => {
        const onClearText = vi.fn();
        render(ActiveSearchDisplay, {
            props: { ...defaultProps, submittedQueryText: 'test search', onClearText }
        });

        await fireEvent.click(screen.getByText('test search'));
        expect(onClearText).toHaveBeenCalledOnce();
    });

    it('calls onClearImage when clear button is clicked with text query', async () => {
        const onClearImage = vi.fn();
        render(ActiveSearchDisplay, {
            props: { ...defaultProps, submittedQueryText: 'test search', onClearImage }
        });

        await fireEvent.click(screen.getByTestId('search-clear-button'));
        expect(onClearImage).toHaveBeenCalledOnce();
    });

    it('has correct accessibility attributes on clear button', () => {
        render(ActiveSearchDisplay, { props: { ...defaultProps, activeImage: 'test-image.jpg' } });
        expect(screen.getByTestId('search-clear-button')).toHaveAttribute('title', 'Clear search');
    });
});
