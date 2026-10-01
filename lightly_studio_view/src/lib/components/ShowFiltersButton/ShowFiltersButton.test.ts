import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import '@testing-library/jest-dom';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import ShowFiltersButton from './ShowFiltersButton.svelte';

const STORAGE_KEY = 'lightlyStudio_filterPanelCollapsed';

describe('ShowFiltersButton', () => {
    // `filterPanelCollapsed` is a module-level singleton, so reset it around every test.
    beforeEach(() => {
        useGlobalStorage().filterPanelCollapsed.set(false);
        sessionStorage.clear();
    });

    afterEach(() => {
        useGlobalStorage().filterPanelCollapsed.set(false);
        sessionStorage.clear();
    });

    it('renders the "Filters" label', () => {
        render(ShowFiltersButton);
        expect(screen.getByTestId('filter-panel-expand')).toHaveTextContent('Filters');
    });

    it('clears the collapsed state when clicked', async () => {
        const { filterPanelCollapsed } = useGlobalStorage();
        filterPanelCollapsed.set(true);

        render(ShowFiltersButton);
        await fireEvent.click(screen.getByTestId('filter-panel-expand'));

        expect(get(filterPanelCollapsed)).toBe(false);
        expect(sessionStorage.getItem(STORAGE_KEY)).toBe('false');
    });
});
