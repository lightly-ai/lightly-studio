import { fireEvent, render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import GridContextMenu from './GridContextMenu.svelte';

const children = createRawSnippet(() => ({
    render: () => '<div data-testid="grid-viewport">grid</div>'
}));

function makeProps(overrides: Record<string, unknown> = {}) {
    return {
        children,
        headerLabel: 'cat.png',
        tags: [{ tag_id: 'tag-train', name: 'train' }],
        tagStates: { 'tag-train': 'unchecked' } as Record<
            string,
            'checked' | 'indeterminate' | 'unchecked'
        >,
        canEditTags: true,
        busy: false,
        hasSelection: false,
        onResolveTarget: vi.fn(() => true),
        onToggleTag: vi.fn(),
        onCreateAndAssign: vi.fn(),
        onOpen: vi.fn(),
        onFindSimilar: vi.fn(),
        onClearSelection: vi.fn(),
        ...overrides
    };
}

/** Right-clicks the wrapped grid to open the menu. */
async function openMenu() {
    await fireEvent.contextMenu(screen.getByTestId('grid-viewport'));
}

describe('GridContextMenu', () => {
    it('renders the wrapped grid and opens the menu on right-click', async () => {
        const onResolveTarget = vi.fn(() => true);
        render(GridContextMenu, { props: makeProps({ onResolveTarget }) });

        expect(screen.getByTestId('grid-viewport')).toBeInTheDocument();
        expect(screen.queryByTestId('grid-context-menu')).not.toBeInTheDocument();

        await openMenu();

        expect(onResolveTarget).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('grid-context-menu-header')).toHaveTextContent('cat.png');
    });

    it('offers the tag submenu and the single-sample actions', async () => {
        render(GridContextMenu, { props: makeProps() });

        await openMenu();

        expect(screen.getByTestId('grid-context-menu-tags')).toBeInTheDocument();
        expect(screen.getByTestId('grid-context-menu-open')).toBeInTheDocument();
        expect(screen.getByTestId('grid-context-menu-find-similar')).toBeInTheDocument();
    });

    it('hides the tag submenu without edit permission', async () => {
        render(GridContextMenu, { props: makeProps({ canEditTags: false }) });

        await openMenu();

        expect(screen.queryByTestId('grid-context-menu-tags')).not.toBeInTheDocument();
        expect(screen.getByTestId('grid-context-menu-open')).toBeInTheDocument();
    });

    it('offers clear selection only while something is selected', async () => {
        const { unmount } = render(GridContextMenu, { props: makeProps() });
        await openMenu();
        expect(screen.queryByTestId('grid-context-menu-clear-selection')).not.toBeInTheDocument();
        unmount();

        render(GridContextMenu, {
            props: makeProps({ hasSelection: true, headerLabel: '3 samples' })
        });
        await openMenu();

        expect(screen.getByTestId('grid-context-menu-clear-selection')).toBeInTheDocument();
        expect(screen.getByTestId('grid-context-menu-header')).toHaveTextContent('3 samples');
    });

    it('invokes the action callbacks', async () => {
        const onOpen = vi.fn();
        const onFindSimilar = vi.fn();
        render(GridContextMenu, { props: makeProps({ onOpen, onFindSimilar }) });

        await openMenu();
        await fireEvent.click(screen.getByTestId('grid-context-menu-open'));
        expect(onOpen).toHaveBeenCalledTimes(1);

        await openMenu();
        await fireEvent.click(screen.getByTestId('grid-context-menu-find-similar'));
        expect(onFindSimilar).toHaveBeenCalledTimes(1);
    });

    it('closes again when no tile was resolved', async () => {
        render(GridContextMenu, { props: makeProps({ onResolveTarget: vi.fn(() => false) }) });

        await openMenu();
        await vi.waitFor(() => {
            expect(screen.queryByTestId('grid-context-menu')).not.toBeInTheDocument();
        });
    });
});
