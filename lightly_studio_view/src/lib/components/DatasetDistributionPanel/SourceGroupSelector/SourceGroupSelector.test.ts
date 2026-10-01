import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import SourceGroupSelector from './SourceGroupSelector.svelte';
import type { SelectItem } from '$lib/components/Select';

const sourceItems: SelectItem[] = [
    { value: 'classes', label: 'Annotation classes' },
    { value: 'metadata', label: 'Metadata' }
];

const groupItems: SelectItem[] = [
    { value: 'key1', label: 'Key 1' },
    { value: 'key2', label: 'Key 2' }
];

const defaultProps = {
    sourceItems,
    groupItems: [] as SelectItem[],
    activeSourceId: 'classes',
    activeGroupId: undefined,
    groupLabel: 'Field',
    onSourceChange: vi.fn(),
    onGroupChange: vi.fn()
};

describe('SourceGroupSelector', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    afterEach(() => {
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the distribution label and source select', () => {
        render(SourceGroupSelector, { props: defaultProps });

        expect(screen.getByText('Distribution')).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-source-select')).toBeInTheDocument();
    });

    it('hides the group select when groupItems is empty', () => {
        render(SourceGroupSelector, { props: defaultProps });

        expect(screen.queryByTestId('dataset-distribution-group-select')).not.toBeInTheDocument();
    });

    it('shows the group select with the provided groupLabel when groups exist', () => {
        render(SourceGroupSelector, {
            props: { ...defaultProps, groupItems, activeGroupId: 'key1' }
        });

        expect(screen.getByText('Field')).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-group-select')).toBeInTheDocument();
    });

    it('calls onSourceChange when a new source is selected', async () => {
        const onSourceChange = vi.fn();
        const user = userEvent.setup();
        render(SourceGroupSelector, { props: { ...defaultProps, onSourceChange } });

        await user.click(screen.getByTestId('dataset-distribution-source-select'));
        const option = await waitFor(() => screen.getByRole('option', { name: 'Metadata' }));
        await user.click(option);

        expect(onSourceChange).toHaveBeenCalledWith('metadata');
    });

    it('calls onGroupChange when a new group is selected', async () => {
        const onGroupChange = vi.fn();
        const user = userEvent.setup();
        render(SourceGroupSelector, {
            props: { ...defaultProps, groupItems, activeGroupId: 'key1', onGroupChange }
        });

        await user.click(screen.getByTestId('dataset-distribution-group-select'));
        const option = await waitFor(() => screen.getByRole('option', { name: 'Key 2' }));
        await user.click(option);

        expect(onGroupChange).toHaveBeenCalledWith('key2');
    });
});
