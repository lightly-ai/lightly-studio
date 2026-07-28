import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ParameterTable from './ParameterTable.svelte';

const defaultProps = {
    name: 'prompts',
    value: [] as Record<string, string>[],
    required: true,
    isMissing: false,
    columns: ['prompt', 'label'],
    onUpdate: vi.fn()
};

describe('ParameterTable', () => {
    it('shows an empty state when there are no rows', () => {
        render(ParameterTable, { props: { ...defaultProps, onUpdate: vi.fn() } });

        expect(screen.getByTestId('parameter-table-prompts-empty-state')).toBeInTheDocument();
    });

    it('hides the empty state and renders a cell per column when rows are present', () => {
        render(ParameterTable, {
            props: {
                ...defaultProps,
                value: [{ prompt: 'person', label: 'pedestrian' }],
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('parameter-table-prompts-empty-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('parameter-table-prompts-prompt-0')).toHaveValue('person');
        expect(screen.getByTestId('parameter-table-prompts-label-0')).toHaveValue('pedestrian');
    });

    it('calls onUpdate with a blank row keyed by columns when "Add row" is clicked', async () => {
        const onUpdate = vi.fn();

        render(ParameterTable, { props: { ...defaultProps, onUpdate } });

        await fireEvent.click(screen.getByTestId('parameter-table-prompts-add-row'));

        expect(onUpdate).toHaveBeenCalledWith([{ prompt: '', label: '' }]);
    });

    it('calls onUpdate with the edited cell when a cell input changes', async () => {
        const onUpdate = vi.fn();

        render(ParameterTable, {
            props: { ...defaultProps, value: [{ prompt: '', label: '' }], onUpdate }
        });

        await fireEvent.input(screen.getByTestId('parameter-table-prompts-prompt-0'), {
            target: { value: 'car' }
        });

        expect(onUpdate).toHaveBeenCalledWith([{ prompt: 'car', label: '' }]);
    });

    it('calls onUpdate without the removed row when the remove button is clicked', async () => {
        const onUpdate = vi.fn();

        render(ParameterTable, {
            props: {
                ...defaultProps,
                value: [
                    { prompt: 'person', label: 'pedestrian' },
                    { prompt: 'car', label: 'vehicle' }
                ],
                onUpdate
            }
        });

        await fireEvent.click(screen.getByTestId('parameter-table-prompts-remove-row-0'));

        expect(onUpdate).toHaveBeenCalledWith([{ prompt: 'car', label: 'vehicle' }]);
    });

    it('keeps every row reachable when the row count exceeds the visible limit', () => {
        const value = Array.from({ length: 6 }, (_, index) => ({
            prompt: `prompt ${index}`,
            label: `label ${index}`
        }));

        render(ParameterTable, { props: { ...defaultProps, value, onUpdate: vi.fn() } });

        expect(screen.getByTestId('parameter-table-prompts-prompt-0')).toHaveValue('prompt 0');
        expect(screen.getByTestId('parameter-table-prompts-prompt-5')).toHaveValue('prompt 5');
        expect(screen.getByTestId('parameter-table-prompts-remove-row-5')).toBeInTheDocument();
    });

    it('shows the validation hint when a required table is missing a value', () => {
        render(ParameterTable, {
            props: { ...defaultProps, isMissing: true, onUpdate: vi.fn() }
        });

        expect(
            screen.getByText('Add at least one row and fill in every cell.')
        ).toBeInTheDocument();
    });
});
