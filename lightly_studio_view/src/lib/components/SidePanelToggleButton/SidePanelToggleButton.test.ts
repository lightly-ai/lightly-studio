import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import '@testing-library/jest-dom';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import SidePanelToggleButton from './SidePanelToggleButton.svelte';

const STORAGE_KEY = 'lightlyStudio_isSampleDetailsSidePanelCollapsed';

describe('SidePanelToggleButton', () => {
    beforeEach(() => {
        useGlobalStorage().isSampleDetailsSidePanelCollapsed.set(false);
        sessionStorage.clear();
    });

    afterEach(() => {
        useGlobalStorage().isSampleDetailsSidePanelCollapsed.set(false);
        sessionStorage.clear();
    });

    it('renders with aria-expanded true when panel is open', () => {
        render(SidePanelToggleButton);
        const button = screen.getByTestId('side-panel-toggle');
        expect(button).toHaveAttribute('aria-expanded', 'true');
        expect(button).toHaveAccessibleName('Hide side panel');
    });

    it('toggles the collapsed state when clicked', async () => {
        const { isSampleDetailsSidePanelCollapsed } = useGlobalStorage();

        render(SidePanelToggleButton);
        await fireEvent.click(screen.getByTestId('side-panel-toggle'));

        expect(get(isSampleDetailsSidePanelCollapsed)).toBe(true);
        expect(sessionStorage.getItem(STORAGE_KEY)).toBe('true');
    });

    it('toggles back to expanded when clicked twice', async () => {
        const { isSampleDetailsSidePanelCollapsed } = useGlobalStorage();

        render(SidePanelToggleButton);
        const button = screen.getByTestId('side-panel-toggle');

        await fireEvent.click(button);
        expect(get(isSampleDetailsSidePanelCollapsed)).toBe(true);

        await fireEvent.click(button);
        expect(get(isSampleDetailsSidePanelCollapsed)).toBe(false);
    });
});
