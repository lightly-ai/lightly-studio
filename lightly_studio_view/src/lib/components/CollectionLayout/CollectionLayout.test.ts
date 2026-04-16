import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import CollectionLayoutTest from './CollectionLayoutTest.test.svelte';
import '@testing-library/jest-dom';

vi.mock('paneforge', () => ({
    PaneGroup: {},
    Pane: {},
    PaneResizer: {}
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        updateSampleSize: vi.fn(),
        sampleSize: writable({ width: 4 })
    })
}));

describe('CollectionLayout', () => {
    it('renders children directly in details mode', () => {
        render(CollectionLayoutTest, { props: { testCase: 'details-mode' } });

        expect(screen.getByTestId('details-children')).toBeInTheDocument();
    });

    it('does not render sidebar in details mode', () => {
        render(CollectionLayoutTest, { props: { testCase: 'details-mode' } });

        expect(screen.queryByTestId('sidebar-content')).not.toBeInTheDocument();
    });

    it('renders main children in non-details mode', () => {
        render(CollectionLayoutTest, { props: { testCase: 'no-sidebar' } });

        expect(screen.getByTestId('main-children')).toBeInTheDocument();
    });

    it('renders sidebar when showLeftSidebar is true', () => {
        render(CollectionLayoutTest, { props: { testCase: 'with-sidebar' } });

        expect(screen.getByTestId('sidebar-content')).toBeInTheDocument();
    });

    it('does not render sidebar when showLeftSidebar is false', () => {
        render(CollectionLayoutTest, { props: { testCase: 'no-sidebar' } });

        expect(screen.queryByTestId('sidebar-content')).not.toBeInTheDocument();
    });

    it('renders search bar inside GridHeader when showGridHeader is true', () => {
        render(CollectionLayoutTest, { props: { testCase: 'with-grid-header' } });

        expect(screen.getByTestId('search-bar')).toBeInTheDocument();
    });

    it('does not render search bar when showGridHeader is false', () => {
        render(CollectionLayoutTest, { props: { testCase: 'no-grid-header' } });

        expect(screen.queryByTestId('search-bar')).not.toBeInTheDocument();
    });

    it('renders SelectionPill when showSelectionPill is true and selectedCount > 0', () => {
        render(CollectionLayoutTest, { props: { testCase: 'with-selection-pill' } });

        expect(screen.getByText('3 selected')).toBeInTheDocument();
    });

    it('renders all snippets when provided', () => {
        render(CollectionLayoutTest, { props: { testCase: 'with-all-snippets' } });

        expect(screen.getByTestId('header-content')).toBeInTheDocument();
        expect(screen.getByTestId('sidebar-content')).toBeInTheDocument();
        expect(screen.getByTestId('search-bar')).toBeInTheDocument();
        expect(screen.getByTestId('footer-content')).toBeInTheDocument();
        expect(screen.getByTestId('main-children')).toBeInTheDocument();
    });
});
