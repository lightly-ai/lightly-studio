import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import GridItemTestWrapper from './GridItemTestWrapper.test.svelte';

describe('GridItem', () => {
    it('renders with default dimensions', () => {
        const { container } = render(GridItemTestWrapper, {
            props: {
                content: 'Test content'
            }
        });

        const gridItem = container.querySelector('.relative.select-none');
        expect(gridItem).toBeInTheDocument();
        expect(gridItem).toHaveAttribute('role', 'button');
        expect(gridItem).toHaveAttribute('tabindex', '0');

        const innerDiv = container.querySelector('.relative.overflow-hidden.rounded-lg');
        expect(innerDiv).toBeInTheDocument();
        expect(innerDiv).toHaveStyle({ width: '300px', height: '300px' });
    });

    it('renders with custom numeric dimensions', () => {
        const { container } = render(GridItemTestWrapper, {
            props: {
                width: 500,
                height: 400,
                content: 'Test content'
            }
        });

        const innerDiv = container.querySelector('.relative.overflow-hidden.rounded-lg');
        expect(innerDiv).toHaveStyle({ width: '500px', height: '400px' });
    });

    it('renders with custom string dimensions', () => {
        const { container } = render(GridItemTestWrapper, {
            props: {
                width: '50%',
                height: '100vh',
                content: 'Test content'
            }
        });

        const innerDiv = container.querySelector('.relative.overflow-hidden.rounded-lg');
        expect(innerDiv).toHaveStyle({ width: '50%', height: '100vh' });
    });

    it('renders children content', () => {
        const { container } = render(GridItemTestWrapper, {
            props: {
                content: 'Custom child content'
            }
        });

        expect(container.textContent).toContain('Custom child content');
    });

    it('applies custom props to outer div', () => {
        const { container } = render(GridItemTestWrapper, {
            props: {
                content: 'Test',
                props: {
                    'data-testid': 'custom-grid-item',
                    'aria-label': 'Custom grid item'
                }
            }
        });

        const gridItem = container.querySelector('[data-testid="custom-grid-item"]');
        expect(gridItem).toBeInTheDocument();
        expect(gridItem).toHaveAttribute('aria-label', 'Custom grid item');
    });
});
