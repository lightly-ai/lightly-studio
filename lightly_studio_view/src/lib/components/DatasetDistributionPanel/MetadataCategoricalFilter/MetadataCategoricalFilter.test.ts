import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MetadataCategoricalFilter from './MetadataCategoricalFilter.svelte';
import type { CategoricalBucket } from '../types';

const buckets: CategoricalBucket[] = [
    {
        id: 'literal-missing',
        kind: 'value',
        value: 'Missing',
        label: 'Missing',
        count: 4
    },
    { id: 'missing', kind: 'missing', value: null, label: 'Missing', count: 3 },
    { id: 'other', kind: 'other', label: 'Other', count: 2 }
];

const defaultProps = {
    buckets,
    selectedValues: [] as (string | null)[],
    onToggle: vi.fn(),
    onClear: vi.fn()
};

describe('MetadataCategoricalFilter', () => {
    it('keeps literal Missing and semantic Missing distinct and disables Other', async () => {
        const onToggle = vi.fn();
        render(MetadataCategoricalFilter, {
            props: { ...defaultProps, selectedValues: ['Missing'], onToggle }
        });

        await fireEvent.click(screen.getByTestId('metadata-categorical-filter-trigger'));
        const literal = screen.getByRole('checkbox', {
            name: 'Select value Missing (value), 4 samples'
        });
        const missing = screen.getByRole('checkbox', {
            name: 'Select missing metadata, 3 samples'
        });
        expect(literal).toBeChecked();
        expect(missing).not.toBeChecked();
        expect(screen.getByText('Other is an aggregate and cannot be selected.')).toBeVisible();
        expect(screen.queryByRole('checkbox', { name: /Other/ })).not.toBeInTheDocument();

        await fireEvent.click(missing);
        expect(onToggle).toHaveBeenCalledWith(null);
    });

    it('searches values and clears the controlled selection', async () => {
        const searchableBuckets: CategoricalBucket[] = [
            ...buckets,
            ...Array.from({ length: 5 }, (_, index) => ({
                id: `value-${index}`,
                kind: 'value' as const,
                value: `value-${index}`,
                label: `value-${index}`,
                count: index + 1
            }))
        ];
        const onClear = vi.fn();
        render(MetadataCategoricalFilter, {
            props: { ...defaultProps, buckets: searchableBuckets, selectedValues: [null], onClear }
        });
        await fireEvent.click(screen.getByTestId('metadata-categorical-filter-trigger'));
        await fireEvent.input(screen.getByLabelText('Search values'), {
            target: { value: 'not present' }
        });
        expect(screen.getByText('No values found.')).toBeVisible();
        await fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
        expect(onClear).toHaveBeenCalledOnce();
    });

    it('keeps a selected value removable when it is absent from the latest response', async () => {
        const onToggle = vi.fn();
        render(MetadataCategoricalFilter, {
            props: { ...defaultProps, buckets: [], selectedValues: ['stale'], onToggle }
        });

        await fireEvent.click(screen.getByTestId('metadata-categorical-filter-trigger'));
        expect(screen.queryByLabelText('Search values')).not.toBeInTheDocument();
        expect(screen.getByText('Not in top 20')).toBeVisible();
        await fireEvent.click(
            screen.getByRole('checkbox', {
                name: 'Select value stale, count unavailable'
            })
        );
        expect(onToggle).toHaveBeenCalledWith('stale');
    });

    it('disambiguates a retained literal Other from the aggregate bucket', async () => {
        const onToggle = vi.fn();
        render(MetadataCategoricalFilter, {
            props: { ...defaultProps, selectedValues: ['Other'], onToggle }
        });

        expect(screen.getByTestId('metadata-categorical-filter-trigger')).toHaveTextContent(
            'Other (value)'
        );
        await fireEvent.click(screen.getByTestId('metadata-categorical-filter-trigger'));
        expect(screen.getAllByText('Other (value)')).toHaveLength(2);
        expect(screen.getByText('Other is an aggregate and cannot be selected.')).toBeVisible();
        await fireEvent.click(
            screen.getByRole('checkbox', {
                name: 'Select value Other (value), count unavailable'
            })
        );
        expect(onToggle).toHaveBeenCalledWith('Other');
    });

    it('shows search only above five returned concrete values', async () => {
        const fiveConcrete: CategoricalBucket[] = [
            ...Array.from({ length: 5 }, (_, index) => ({
                id: `value-${index}`,
                kind: 'value' as const,
                value: `value-${index}`,
                label: `value-${index}`,
                count: index + 1
            })),
            { id: 'missing', kind: 'missing', value: null, label: 'Missing', count: 3 },
            { id: 'other', kind: 'other', label: 'Other', count: 2 }
        ];
        render(MetadataCategoricalFilter, {
            props: { ...defaultProps, buckets: fiveConcrete, selectedValues: ['retained'] }
        });

        await fireEvent.click(screen.getByTestId('metadata-categorical-filter-trigger'));
        expect(screen.queryByLabelText('Search values')).not.toBeInTheDocument();
        expect(screen.getByText('Not in top 20')).toBeVisible();
    });
});
