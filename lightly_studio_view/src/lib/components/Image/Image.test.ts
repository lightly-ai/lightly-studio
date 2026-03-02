import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import ImageTestWrapper from './ImageTestWrapper.test.svelte';

describe('Image', () => {
    it('should render img element with correct src', () => {
        const { container } = render(ImageTestWrapper, { props: { src: 'test-image.jpg' } });
        const img = container.querySelector('img');
        expect(img).toBeTruthy();
        expect(img?.getAttribute('src')).toBe('test-image.jpg');
    });

    it('should render with alt attribute matching src', () => {
        const { container } = render(ImageTestWrapper, { props: { src: 'test-image.jpg' } });
        const img = container.querySelector('img');
        expect(img?.getAttribute('alt')).toBe('test-image.jpg');
    });

    it('should render with lazy loading', () => {
        const { container } = render(ImageTestWrapper, { props: { src: 'test-image.jpg' } });
        const img = container.querySelector('img');
        expect(img?.getAttribute('loading')).toBe('lazy');
    });

    it('should apply custom className', () => {
        const { container } = render(ImageTestWrapper, {
            props: { src: 'test-image.jpg', className: 'custom-class' }
        });
        const img = container.querySelector('img.custom-class');
        expect(img).toBeTruthy();
    });

    it('should have image and rounded-lg classes by default', () => {
        const { container } = render(ImageTestWrapper, { props: { src: 'test-image.jpg' } });
        const img = container.querySelector('img');
        expect(img?.className).toContain('image');
        expect(img?.className).toContain('rounded-lg');
    });

    it('should have bg-black class by default', () => {
        const { container } = render(ImageTestWrapper, { props: { src: 'test-image.jpg' } });
        const img = container.querySelector('img');
        expect(img?.className).toContain('bg-black');
    });

    it('should apply additional imgProps', () => {
        const { container } = render(ImageTestWrapper, {
            props: { src: 'test-image.jpg', imgProps: { 'data-testid': 'custom-image' } }
        });
        const img = container.querySelector('img');
        expect(img?.getAttribute('data-testid')).toBe('custom-image');
    });

    it('should render without src', () => {
        const { container } = render(ImageTestWrapper, { props: {} });
        const img = container.querySelector('img');
        expect(img).toBeTruthy();
        expect(img?.getAttribute('src')).toBe(null);
    });
});
