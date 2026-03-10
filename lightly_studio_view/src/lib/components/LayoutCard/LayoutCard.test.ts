import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import LayoutCardTestWrapper from './LayoutCardTestWrapper.test.svelte';
import '@testing-library/jest-dom';

describe('LayoutCard', () => {
    it('renders children content', () => {
        const { container } = render(LayoutCardTestWrapper, {
            props: {
                content: 'Test content'
            }
        });

        expect(container.textContent).toContain('Test content');
    });

    it('applies default classes', () => {
        const { container } = render(LayoutCardTestWrapper, {
            props: {
                content: 'Content'
            }
        });

        const card = container.querySelector('div > div');
        expect(card).toHaveClass('h-full');
        expect(card).toHaveClass('w-full');
        expect(card).toHaveClass('space-y-6');
        expect(card).toHaveClass('rounded-[1vw]');
        expect(card).toHaveClass('bg-card');
        expect(card).toHaveClass('p-4');
    });

    it('applies custom className', () => {
        const { container } = render(LayoutCardTestWrapper, {
            props: {
                content: 'Content',
                className: 'custom-class'
            }
        });

        const card = container.querySelector('div > div');
        expect(card).toHaveClass('custom-class');
        expect(card).toHaveClass('h-full');
        expect(card).toHaveClass('bg-card');
    });

    it('applies empty className by default', () => {
        const { container } = render(LayoutCardTestWrapper, {
            props: {
                content: 'Content'
            }
        });

        const card = container.querySelector('div > div');
        expect(card?.className).not.toContain('undefined');
    });
});
