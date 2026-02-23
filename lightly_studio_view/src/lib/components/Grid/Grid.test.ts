import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import Grid from './Grid.svelte';

class MockResizeObserver {
	observe() {}
	unobserve() {}
	disconnect() {}
}

describe('Grid', () => {
	beforeEach(() => {
		global.ResizeObserver = MockResizeObserver as any;

		// Mock scrollTo for the virtual grid
		Element.prototype.scrollTo = vi.fn();
	});

	it('renders viewport container', () => {
		const { container } = render(Grid, {
			props: {
				itemCount: 10,
				itemWidth: 200,
				itemHeight: 200,
				gridItem: () => {}
			}
		});

		const viewport = container.querySelector('.viewport');
		expect(viewport).toBeInTheDocument();
	});

	it('renders with custom columnCount', () => {
		const { container } = render(Grid, {
			props: {
				itemCount: 10,
				columnCount: 4,
				itemWidth: 200,
				itemHeight: 200,
				gridItem: () => {}
			}
		});

		const viewport = container.querySelector('.viewport');
		expect(viewport).toBeInTheDocument();
	});

	it('applies testId attribute', () => {
		const { container } = render(Grid, {
			props: {
				itemCount: 10,
				itemWidth: 200,
				itemHeight: 200,
				testId: 'test-grid',
				gridItem: () => {}
			}
		});

		const grid = container.querySelector('[data-testid="test-grid"]');
		expect(grid).toBeInTheDocument();
	});

	it('accepts gridItem snippet prop', () => {
		const gridItemMock = vi.fn();

		render(Grid, {
			props: {
				itemCount: 5,
				itemWidth: 200,
				itemHeight: 200,
				gridItem: gridItemMock
			}
		});

		// Component should render without errors when gridItem is provided
		expect(gridItemMock).toBeDefined();
	});
});
