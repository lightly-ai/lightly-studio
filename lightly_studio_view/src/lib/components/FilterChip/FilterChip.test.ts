import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import FilterChip from './FilterChip.svelte';

const defaultProps = {
    checked: true,
    title: 'Category filter',
    checkboxLabel: 'Toggle category filter',
    onCheckedChange: vi.fn(),
    onClear: vi.fn()
};

describe('FilterChip', () => {
    it('renders the default title and supports clearing and disabling the filter', () => {
        const onClear = vi.fn();
        const onCheckedChange = vi.fn();
        render(FilterChip, { props: { ...defaultProps, onClear, onCheckedChange } });

        expect(screen.getByText('Category filter')).toBeVisible();
        const checkbox = screen.getByRole('checkbox', { name: 'Toggle category filter' });
        expect(checkbox).toBeChecked();
        checkbox.click();
        screen.getByRole('button', { name: 'Clear category filter' }).click();

        expect(onCheckedChange).toHaveBeenCalledWith(false);
        expect(onClear).toHaveBeenCalledOnce();
    });

    it('renders a subtitle and opens the filter when its body is clicked', () => {
        const onclick = vi.fn();
        const subtitle = createRawSnippet(() => ({
            render: () => '<span>Selected 14 categories</span>'
        }));
        render(FilterChip, { props: { ...defaultProps, subtitle, onclick } });

        expect(screen.getByText('Selected 14 categories')).toBeVisible();
        screen.getByRole('button', { name: 'Category filter Selected 14 categories' }).click();

        expect(onclick).toHaveBeenCalledOnce();
    });

    it('uses custom content in place of the title and subtitle', () => {
        const content = createRawSnippet(() => ({
            render: () => '<span>Ground truth: cat, Prediction: dog</span>'
        }));
        const subtitle = createRawSnippet(() => ({
            render: () => '<span>Default subtitle</span>'
        }));
        const onclick = vi.fn();
        render(FilterChip, { props: { ...defaultProps, content, subtitle, onclick } });

        expect(screen.queryByText('Category filter')).not.toBeInTheDocument();
        expect(screen.queryByText('Default subtitle')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear category filter' })).toBeVisible();
        screen.getByRole('button', { name: 'Ground truth: cat, Prediction: dog' }).click();

        expect(onclick).toHaveBeenCalledOnce();
    });
});
