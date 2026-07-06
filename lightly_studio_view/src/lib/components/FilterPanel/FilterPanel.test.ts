import { fireEvent, render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import FilterPanel from './FilterPanel.svelte';
import { useGlobalStorage } from '$lib/hooks';

const STORAGE_KEY = 'lightlyStudio_filterPanelCollapsed';

// Filter body rendered as the panel's children so we can assert it is hidden when collapsed.
const children = createRawSnippet(() => ({
    render: () => `<div data-testid="filter-content">Filter body</div>`
}));

const renderPanel = () => render(FilterPanel, { props: { children } });

describe('FilterPanel', () => {
    beforeEach(() => {
        sessionStorage.clear();
        // Reset the shared (module-singleton) store to the default expanded state.
        useGlobalStorage().filterPanelCollapsed.set(false);
    });

    afterEach(() => {
        useGlobalStorage().filterPanelCollapsed.set(false);
    });

    it('renders expanded by default with the filter content and a collapse control', () => {
        renderPanel();

        expect(screen.getByTestId('filter-content')).toBeInTheDocument();
        expect(screen.getByText('Filters')).toBeInTheDocument();
        expect(screen.getByTestId('filter-panel-collapse')).toBeInTheDocument();
        expect(screen.queryByTestId('filter-panel-expand')).not.toBeInTheDocument();
    });

    it('collapses to the rail (hiding content) and expands again from the rail', async () => {
        renderPanel();

        await fireEvent.click(screen.getByTestId('filter-panel-collapse'));

        expect(screen.queryByTestId('filter-content')).not.toBeInTheDocument();
        const expandButton = screen.getByTestId('filter-panel-expand');
        expect(expandButton).toBeInTheDocument();

        await fireEvent.click(expandButton);

        expect(screen.getByTestId('filter-content')).toBeInTheDocument();
        expect(screen.queryByTestId('filter-panel-expand')).not.toBeInTheDocument();
    });

    it('persists the collapsed state to sessionStorage', async () => {
        renderPanel();

        await fireEvent.click(screen.getByTestId('filter-panel-collapse'));

        expect(sessionStorage.getItem(STORAGE_KEY)).toBe('true');
    });

    it('restores the collapsed state from sessionStorage on a fresh mount', async () => {
        // A fresh module graph re-reads sessionStorage when the store is created,
        // mirroring a full page (re)load with a previously collapsed panel.
        vi.resetModules();
        sessionStorage.setItem(STORAGE_KEY, 'true');

        const { render: freshRender } = await import('@testing-library/svelte');
        const { createRawSnippet: freshSnippet } = await import('svelte');
        const { default: FreshFilterPanel } = await import('./FilterPanel.svelte');

        freshRender(FreshFilterPanel, {
            props: {
                children: freshSnippet(() => ({
                    render: () => `<div data-testid="filter-content">Filter body</div>`
                }))
            }
        });

        expect(screen.getByTestId('filter-panel-expand')).toBeInTheDocument();
        expect(screen.queryByTestId('filter-content')).not.toBeInTheDocument();
    });
});
