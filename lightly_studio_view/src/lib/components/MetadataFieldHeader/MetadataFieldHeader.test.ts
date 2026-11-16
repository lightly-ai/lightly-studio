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
});
