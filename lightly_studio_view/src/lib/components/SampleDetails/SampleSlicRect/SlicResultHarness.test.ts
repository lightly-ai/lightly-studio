import { render } from '@testing-library/svelte';
import { expect, it, vi } from 'vitest';
import SlicResultHarness from './SlicResultHarness.svelte';

vi.mock('$lib/utils/slic', () => ({
    loadSuperpixelsForImage: () => new Promise(() => {})
}));

it('shows loading status without boundaries while computation is pending', () => {
    const view = render(SlicResultHarness, { imageUrl: 'image.png' });
    expect(view.getByRole('status')).toHaveTextContent('computing');
    expect(view.queryByRole('img')).not.toBeInTheDocument();
});
