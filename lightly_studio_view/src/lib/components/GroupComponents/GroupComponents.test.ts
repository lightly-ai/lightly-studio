import { render, screen } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import GroupComponents from './GroupComponents.svelte';

describe('GroupComponents', () => {
	it('renders correct number of items', () => {
		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		expect(items).toHaveLength(3);
	});

	it('applies selected class to selected item', () => {
		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				selectedIndex: 1,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		expect(items[0]).toHaveClass('opacity-50');
		expect(items[0]).not.toHaveClass('selected');
		expect(items[1]).toHaveClass('selected');
		expect(items[1]).not.toHaveClass('opacity-50');
		expect(items[2]).toHaveClass('opacity-50');
		expect(items[2]).not.toHaveClass('selected');
	});

	it('applies opacity-50 to non-selected items', () => {
		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				selectedIndex: 0,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		expect(items[0]).not.toHaveClass('opacity-50');
		expect(items[1]).toHaveClass('opacity-50');
		expect(items[2]).toHaveClass('opacity-50');
	});

	it('calls onclick when item is clicked', async () => {
		const user = userEvent.setup();
		const onclick = vi.fn();

		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				onclick,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		await user.click(items[1] as HTMLElement);

		expect(onclick).toHaveBeenCalledWith(1);
		expect(onclick).toHaveBeenCalledTimes(1);
	});

	it('calls onclick when Enter key is pressed', async () => {
		const user = userEvent.setup();
		const onclick = vi.fn();

		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				onclick,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		(items[2] as HTMLElement).focus();
		await user.keyboard('{Enter}');

		expect(onclick).toHaveBeenCalledWith(2);
		expect(onclick).toHaveBeenCalledTimes(1);
	});

	it('does not call onclick when other keys are pressed', async () => {
		const user = userEvent.setup();
		const onclick = vi.fn();

		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 3,
				onclick,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		(items[0] as HTMLElement).focus();
		await user.keyboard('{Space}');
		await user.keyboard('{Escape}');

		expect(onclick).not.toHaveBeenCalled();
	});

	it('works without onclick handler', async () => {
		const user = userEvent.setup();

		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 2,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');

		// Should not throw
		await user.click(items[0] as HTMLElement);
		(items[1] as HTMLElement).focus();
		await user.keyboard('{Enter}');
	});

	it('defaults selectedIndex to -1 when not provided', () => {
		const { container } = render(GroupComponents, {
			props: {
				itemsCount: 2,
				renderItem: ({ index }: { index: number }) => `Item ${index}`
			}
		});

		const items = container.querySelectorAll('.image-item');
		expect(items[0]).toHaveClass('opacity-50');
		expect(items[1]).toHaveClass('opacity-50');
	});
});
