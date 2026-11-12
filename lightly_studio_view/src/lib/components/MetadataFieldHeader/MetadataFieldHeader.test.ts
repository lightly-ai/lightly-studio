import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import MetadataFieldHeader from './MetadataFieldHeader.svelte';

describe('MetadataFieldHeader', () => {
    it('calls onToggleExpanded when the title is clicked', async () => {
        const onToggleExpanded = vi.fn();
        render(MetadataFieldHeader, {
            props: { title: 'score', expanded: true, onToggleExpanded }
        });

        const button = screen.getByRole('button', { name: 'score' });
        expect(button).toHaveAttribute('aria-expanded', 'true');
        await fireEvent.click(button);

        expect(onToggleExpanded).toHaveBeenCalledOnce();
    });

    it('shows status text next to a collapsed field', () => {
        render(MetadataFieldHeader, {
            props: {
                title: 'score',
                expanded: false,
                onToggleExpanded: vi.fn(),
                status: '0.2 - 0.8'
            }
        });

        expect(screen.getByRole('button', { name: 'score' })).toHaveAttribute(
            'aria-expanded',
            'false'
        );
        expect(screen.getByRole('status')).toHaveTextContent('0.2 - 0.8');
    });

    it('renders a plain title without toggle or remove controls by default', () => {
        render(MetadataFieldHeader, { props: { title: 'score' } });

        expect(screen.getByRole('heading', { name: 'score' })).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('calls onRemove from the remove button', async () => {
        const onRemove = vi.fn();
        render(MetadataFieldHeader, { props: { title: 'score', onRemove } });

        await fireEvent.click(screen.getByRole('button', { name: 'Remove metadata field score' }));

        expect(onRemove).toHaveBeenCalledOnce();
    });

    it('shows checkbox and summary for an active field', () => {
        render(MetadataFieldHeader, {
            props: {
                title: 'width',
                checked: true,
                summary: '200px – 640px',
                onClear: vi.fn(),
                expanded: false,
                onToggleExpanded: vi.fn()
            }
        });

        expect(screen.getByRole('checkbox', { name: 'width filter' })).toBeChecked();
        expect(screen.getByText('200px – 640px')).toBeInTheDocument();
    });

    it('hides the summary for an inactive field', () => {
        render(MetadataFieldHeader, {
            props: { title: 'width', checked: false, summary: 'x', onClear: vi.fn() }
        });

        expect(screen.getByRole('checkbox', { name: 'width filter' })).not.toBeChecked();
        expect(screen.queryByText('x')).toBeNull();
    });

    it('hides the summary of an active field while it is expanded', () => {
        render(MetadataFieldHeader, {
            props: { title: 'width', checked: true, summary: 'x', expanded: true, onClear: vi.fn() }
        });

        expect(screen.queryByText('x')).toBeNull();
    });

    it('unchecking calls onClear', async () => {
        const onClear = vi.fn();
        render(MetadataFieldHeader, { props: { title: 'width', checked: true, onClear } });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));

        expect(onClear).toHaveBeenCalledOnce();
    });

    it('checking a collapsed field expands it and does not clear', async () => {
        const onClear = vi.fn();
        const onToggleExpanded = vi.fn();
        render(MetadataFieldHeader, {
            props: { title: 'width', checked: false, expanded: false, onClear, onToggleExpanded }
        });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));

        expect(onToggleExpanded).toHaveBeenCalledOnce();
        expect(onClear).not.toHaveBeenCalled();
        expect(screen.getByRole('checkbox', { name: 'width filter' })).not.toBeChecked();
    });

    it('checking an expanded field does nothing', async () => {
        const onToggleExpanded = vi.fn();
        render(MetadataFieldHeader, {
            props: { title: 'width', checked: false, expanded: true, onToggleExpanded }
        });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'width filter' }));

        expect(onToggleExpanded).not.toHaveBeenCalled();
    });
});
