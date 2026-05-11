import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SortDirection } from '$lib/api/lightly_studio_local';
import type { MetadataInfoView, SortFieldExpr } from '$lib/api/lightly_studio_local';
import OrderBy from './OrderBy.svelte';

const mocks = vi.hoisted(() => ({
    imageSortByValue: null as SortFieldExpr[] | null,
    updateSortBy: vi.fn(),
    metadataInfoValue: [] as MetadataInfoView[]
}));

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        imageSortBy: readable(mocks.imageSortByValue),
        updateSortBy: mocks.updateSortBy
    })
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataInfo: readable(mocks.metadataInfoValue)
    })
}));

describe('OrderBy', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.imageSortByValue = null;
        mocks.metadataInfoValue = [];
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
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('file name');
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
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: undefined
            }
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
            {
                source: 'image',
                field_name: 'width',
                direction: SortDirection.DESC,
                is_numeric: undefined
            }
        ]);
    });

    it('toggles direction from asc to desc', async () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.ASC }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.DESC,
                is_numeric: undefined
            }
        ]);
    });

    it('toggles direction from desc to asc', async () => {
        mocks.imageSortByValue = [
            { source: 'image', field_name: 'file_name', direction: SortDirection.DESC }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: undefined
            }
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

        expect(screen.getByTestId('sort-field-file_name')).toHaveTextContent('file name');
        expect(screen.getByTestId('sort-field-file_path_abs')).toHaveTextContent('file path');
        expect(screen.getByTestId('sort-field-created_at')).toHaveTextContent('created at');
        expect(screen.getByTestId('sort-field-width')).toHaveTextContent('width');
        expect(screen.getByTestId('sort-field-height')).toHaveTextContent('height');
    });

    it('lists metadata fields in the dropdown as metadata.[field]', async () => {
        mocks.metadataInfoValue = [
            { name: 'brightness', type: 'float' },
            { name: 'count', type: 'integer' },
            { name: 'label', type: 'string' },
            { name: 'active', type: 'boolean' }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.getByTestId('sort-field-brightness')).toHaveTextContent(
            'metadata.brightness'
        );
        expect(screen.getByTestId('sort-field-count')).toHaveTextContent('metadata.count');
        expect(screen.getByTestId('sort-field-label')).toHaveTextContent('metadata.label');
        expect(screen.getByTestId('sort-field-active')).toHaveTextContent('metadata.active');
    });

    it('excludes list and dict metadata fields from the dropdown', async () => {
        mocks.metadataInfoValue = [
            { name: 'tags', type: 'list' },
            { name: 'nested', type: 'dict' },
            { name: 'score', type: 'float' }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));

        expect(screen.queryByTestId('sort-field-tags')).toBeNull();
        expect(screen.queryByTestId('sort-field-nested')).toBeNull();
        expect(screen.getByTestId('sort-field-score')).toHaveTextContent('metadata.score');
    });

    it('selects a numeric metadata field with is_numeric true', async () => {
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-score'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        ]);
    });

    it('selects a string metadata field with is_numeric false', async () => {
        mocks.metadataInfoValue = [{ name: 'category', type: 'string' }];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-by-trigger'));
        await fireEvent.click(screen.getByTestId('sort-field-category'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'category',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        ]);
    });

    it('shows metadata.[field] label in the trigger when a metadata field is selected', () => {
        mocks.metadataInfoValue = [{ name: 'brightness', type: 'float' }];
        mocks.imageSortByValue = [
            { source: 'metadata', field_name: 'brightness', direction: SortDirection.ASC }
        ];
        render(OrderBy);
        expect(screen.getByTestId('sort-by-trigger')).toHaveTextContent('metadata.brightness');
    });

    it('preserves is_numeric when toggling direction on a metadata field', async () => {
        mocks.metadataInfoValue = [{ name: 'score', type: 'float' }];
        mocks.imageSortByValue = [
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        ];
        render(OrderBy);

        await fireEvent.click(screen.getByTestId('sort-direction-button'));

        expect(mocks.updateSortBy).toHaveBeenCalledWith([
            {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.DESC,
                is_numeric: true
            }
        ]);
    });
});
