import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import GridItem from './GridItem.svelte';

describe('GridItem', () => {
    it('renders children content', () => {
        const { container } = render(GridItem, {
            props: {
                children: () => 'Test content'
            }
        });

        expect(container.textContent).toContain('Test content');
    });

    it('renders with correct role and tabindex', () => {
        render(GridItem, {
            props: {
                children: () => 'Test content'
            }
        });

        const gridItem = screen.getByRole('button');

        expect(gridItem).toBeInTheDocument();
        expect(gridItem).toHaveAttribute('tabindex', '0');
    });

    it('calls onclick when clicked', async () => {
        const onclick = vi.fn();
        render(GridItem, {
            props: {
                children: () => 'Test content',
                onclick
            }
        });

        const gridItem = screen.getByRole('button');
        await fireEvent.click(gridItem);

        expect(onclick).toHaveBeenCalled();
    });

    it('spreads additional props to the root element', () => {
        render(GridItem, {
            props: {
                children: () => 'Test content',
                'data-testid': 'custom-grid-item'
            }
        });

        const gridItem = screen.getByTestId('custom-grid-item');

        expect(gridItem).toBeInTheDocument();
    });

    it('uses default CSS variables for dimensions', () => {
        const { container } = render(GridItem, {
            props: {
                children: () => 'Test content'
            }
        });

        const content = container.querySelector('.grid-item-content');
        expect(content).toBeInTheDocument();
        expect(content).toHaveAttribute(
            'style',
            'width: var(--sample-width); height: var(--sample-height);'
        );
    });

    it('accepts custom width and height as numbers', () => {
        const { container } = render(GridItem, {
            props: {
                children: () => 'Test content',
                width: 150,
                height: 150
            }
        });

        const content = container.querySelector('.grid-item-content');
        expect(content).toHaveAttribute('style', 'width: 150px; height: 150px;');
    });

    it('accepts custom width and height as strings', () => {
        const { container } = render(GridItem, {
            props: {
                children: () => 'Test content',
                width: '10rem',
                height: '50%'
            }
        });

        const content = container.querySelector('.grid-item-content');
        expect(content).toHaveAttribute('style', 'width: 10rem; height: 50%;');
    });
});
