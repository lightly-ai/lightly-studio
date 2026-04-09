import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import SelectionPill from './SelectionPill.svelte';

describe('SelectionPill', () => {
	it('does not render when selectedCount is 0', () => {
		const { container } = render(SelectionPill, {
			props: { selectedCount: 0, onClear: vi.fn() }
		});

		expect(container.querySelector('[data-testid="clear-selection-button"]')).toBeNull();
		expect(container.textContent).not.toContain('selected');
	});

	it('renders the count and clear button when items are selected', () => {
		render(SelectionPill, {
			props: { selectedCount: 5, onClear: vi.fn() }
		});

		expect(screen.getByText('5 selected')).toBeInTheDocument();
		expect(screen.getByTestId('clear-selection-button')).toBeInTheDocument();
	});

	it('calls onClear when the clear button is clicked', async () => {
		const onClear = vi.fn();
		render(SelectionPill, {
			props: { selectedCount: 3, onClear }
		});

		await fireEvent.click(screen.getByTestId('clear-selection-button'));
		expect(onClear).toHaveBeenCalledOnce();
	});
});
