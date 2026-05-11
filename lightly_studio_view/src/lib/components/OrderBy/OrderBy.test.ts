import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { SortFieldExpr } from '$lib/api/lightly_studio_local';
import OrderBy from './OrderBy.svelte';

const mocks = vi.hoisted(() => ({
    imageSortByValue: null as SortFieldExpr[] | null,
    updateSortBy: vi.fn()
}));

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageSortBy: readable(mocks.imageSortByValue),
        updateSortBy: mocks.updateSortBy
    })
}));

describe('OrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.imageSortByValue = null;
    });

    it('shows placeholder text when no field is selected', () => {
        render(OrderBy);
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('Sort by');
    });

    it('shows the selected field label in the trigger', () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ];
        render(OrderBy);
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('File Name');
    });

    it('direction button is disabled when no field is selected', () => {
        render(OrderBy);
        expect(screen.getByTestId('sort-direction-button')).toBeDisabled();
    });

    it('direction button is enabled when a field is selected', () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'width', direction: SortDirection.ASC }
        ];
        render(OrderBy);
        expect(screen.getByTestId('sort-direction-button')).not.toBeDisabled();
    });

    it('selects a field and calls updateSortBy with asc direction by default', async () => {
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ]);
    });

    it('deselects the field when clicking the already selected item', async () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-file_name'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith(null);
    });

    it('switches to a different field while preserving the current direction', async () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.DESC }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-width'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            { source: 'image', field_name: 'width', direction: SortDirection.DESC }
        ]);
    });

    it('toggles direction between asc and desc on each click', async () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-direction-button'));
        expect(mocks.updateSortBy).toHaveBeenLastCalledWith([
            { source: 'image', field_name: 'file_name', direction: SortDirection.DESC }
        ]);

        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.DESC }
        ];
        await fireEvent.click(screen.getByTestId('sort-direction-button'));
        expect(mocks.updateSortBy).toHaveBeenLastCalledWith([
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ]);
    });

    it('does not call updateSortBy when direction button is clicked with no field selected', async () => {
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).not.toHaveBeenCalled();
    });

    it('lists all sort fields in the dropdown', async () => {
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-file_name')).toHaveTextContent('File Name');
        expect(screen.getByTestId('sort-field-file_path_abs')).toHaveTextContent('File Path');
        expect(screen.getByTestId('sort-field-created_at')).toHaveTextContent('Created At');
        expect(screen.getByTestId('sort-field-width')).toHaveTextContent('Width');
        expect(screen.getByTestId('sort-field-height')).toHaveTextContent('Height');
    });
});
