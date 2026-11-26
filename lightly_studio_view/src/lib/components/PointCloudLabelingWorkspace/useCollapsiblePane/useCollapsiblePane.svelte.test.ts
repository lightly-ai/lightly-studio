import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, it } from 'vitest';
import CollapsiblePaneHarness from './CollapsiblePaneHarness.test.svelte';

const storageKey = 'lightlyStudio_pointCloudTestPaneCollapsed';
afterEach(() => sessionStorage.removeItem(storageKey));

it('keeps a stored collapsed preference through the initial pane layout', async () => {
    sessionStorage.setItem(storageKey, 'true');
    render(CollapsiblePaneHarness, { props: { storageKey } });
    await screen.findByText('Details');

    expect(screen.getByTestId('collapsed')).toHaveTextContent('true');
    expect(sessionStorage.getItem(storageKey)).toBe('true');
});

it('persists toggles and restores them in a new pane', async () => {
    const { unmount } = render(CollapsiblePaneHarness, { props: { storageKey } });
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }));
    expect(sessionStorage.getItem(storageKey)).toBe('true');
    unmount();

    render(CollapsiblePaneHarness, { props: { storageKey } });
    await screen.findByText('Details');
    expect(screen.getByTestId('collapsed')).toHaveTextContent('true');
    await fireEvent.click(screen.getByRole('button', { name: 'Toggle' }));
    expect(sessionStorage.getItem(storageKey)).toBe('false');
});
