import { QueryClient } from '@tanstack/svelte-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { GridType } from '$lib/types';
import SelectionPillHarness from './SelectionPillHarness.svelte';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return Object.fromEntries(
        Object.entries(actual).map(([key, value]) => [
            key,
            typeof value === 'function' ? vi.fn().mockResolvedValue({ data: [] }) : value
        ])
    );
});
vi.mock('$app/state', () => ({ page: { params: { dataset_id: 'root' } } }));
vi.mock('$lib/hooks/useSelectionTarget/useSelectionTarget', () => ({
    getSelectionTarget: () => ({ kind: 'ids', ids: ['s1', 's2', 's3'] })
}));

const defaultProps = {
    selectedCount: 3,
    onClear: vi.fn(),
    gridType: 'images' as GridType
};

function renderPill(props: Partial<typeof defaultProps> = {}) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(SelectionPillHarness, { client, ...defaultProps, ...props });
}

describe('SelectionPill', () => {
    it('does not render when selectedCount is 0', () => {
        renderPill({ selectedCount: 0 });

        expect(screen.queryByTestId('clear-selection-button')).toBeNull();
        expect(screen.queryByText(/selected/)).toBeNull();
    });

    it('shows the count, Tag, Annotate and clear with a selection', async () => {
        const onClear = vi.fn();
        renderPill({ onClear });

        expect(screen.getByText('3 selected')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Tag' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Annotate' })).toBeInTheDocument();
        expect(screen.queryByTestId('selection-hint')).toBeNull();
        await fireEvent.click(screen.getByTestId('clear-selection-button'));
        expect(onClear).toHaveBeenCalledOnce();
    });

    it('hides when selectedCount changes to 0', async () => {
        const { rerender } = renderPill();
        expect(screen.getByText('3 selected')).toBeInTheDocument();

        await rerender({ selectedCount: 0 });

        await waitFor(() => expect(screen.queryByText('3 selected')).not.toBeInTheDocument());
    });

    it('Annotate opens the classification popover on the images grid', async () => {
        renderPill();

        await fireEvent.click(screen.getByRole('button', { name: 'Annotate' }));

        expect(await screen.findByPlaceholderText('Search or create a class…')).toBeInTheDocument();
        expect(screen.queryByText('All 3 selected')).toBeNull();
    });

    it('Annotate opens the annotation popover on the annotations grid', async () => {
        renderPill({ gridType: 'annotations' });

        await fireEvent.click(screen.getByRole('button', { name: 'Annotate' }));

        expect(await screen.findByText('All 3 selected')).toBeInTheDocument();
    });

    it('has no Annotate on other grids', () => {
        renderPill({ gridType: 'videos' });

        expect(screen.getByRole('button', { name: 'Tag' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Annotate' })).toBeNull();
    });

    describe('shortcuts', () => {
        beforeEach(() => {
            vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => {} });
        });
        afterEach(() => {
            vi.unstubAllGlobals();
            document.body.innerHTML = '';
        });

        const tagMenu = () => screen.queryByPlaceholderText('Search or create a tag…');

        it('T opens the tag popover with a selection', async () => {
            renderPill();
            await fireEvent.keyDown(window, { key: 't' });
            expect(await screen.findByPlaceholderText('Search or create a tag…')).toBeVisible();
        });

        it('L opens the annotate popover', async () => {
            renderPill();
            await fireEvent.keyDown(window, { key: 'l' });
            expect(await screen.findByPlaceholderText('Search or create a class…')).toBeVisible();
        });

        it('ignores T while an input has focus', async () => {
            renderPill();
            const input = document.createElement('input');
            document.body.appendChild(input);
            input.focus();
            await fireEvent.keyDown(input, { key: 't' });
            expect(tagMenu()).toBeNull();
        });

        it('ignores T with an empty selection', async () => {
            renderPill({ selectedCount: 0 });
            await fireEvent.keyDown(window, { key: 't' });
            expect(tagMenu()).toBeNull();
        });
    });

    // Kept last: dismissing sets a module-wide flag that later renders would see.
    describe('hint', () => {
        it('names the keys when nothing is selected', () => {
            renderPill({ selectedCount: 0 });

            expect(screen.getByTestId('selection-hint')).toHaveTextContent(
                'Select images to tag t or annotate l'
            );
        });

        it('leaves out annotate on grids without an Annotate menu', () => {
            renderPill({ selectedCount: 0, gridType: 'videos' });

            const hint = screen.getByTestId('selection-hint');
            expect(hint).toHaveTextContent('Select videos to tag t');
            expect(hint).not.toHaveTextContent('annotate');
        });

        it('hides after a dismiss', async () => {
            renderPill({ selectedCount: 0 });

            await fireEvent.click(screen.getByRole('button', { name: 'Dismiss hint' }));

            await waitFor(() => expect(screen.queryByTestId('selection-hint')).toBeNull());
        });
    });
});
