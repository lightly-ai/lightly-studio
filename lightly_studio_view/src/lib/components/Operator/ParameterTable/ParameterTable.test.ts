import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ParameterTable from './ParameterTable.svelte';
import type { ParameterTableRow } from '../parameterTypeConfig';
import { column } from '../fixtures';

const defaultProps = {
    name: 'prompts',
    value: [] as ParameterTableRow[],
    required: true,
    isMissing: false,
    columns: [column({ name: 'prompt' }), column({ name: 'label' })],
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

    it('pre-fills a new row with the column defaults of every type', async () => {
        const onUpdate = vi.fn();
        const columns = [
            column({ name: 'prompt' }),
            column({ name: 'label', required: false, default: 'pedestrian' }),
            column({ name: 'limit', paramType: 'int', default: 5 }),
            column({ name: 'threshold', paramType: 'float', default: 0.5 }),
            column({ name: 'enabled', paramType: 'bool', default: true })
        ];

        render(ParameterTable, { props: { ...defaultProps, columns, onUpdate } });

        await fireEvent.click(screen.getByTestId('parameter-table-prompts-add-row'));

        expect(onUpdate).toHaveBeenCalledWith([
            { prompt: '', label: 'pedestrian', limit: 5, threshold: 0.5, enabled: true }
        ]);
    });

    it('falls back to an empty cell when a column has no default', async () => {
        const onUpdate = vi.fn();
        const columns = [
            column({ name: 'limit', paramType: 'int' }),
            column({ name: 'enabled', paramType: 'bool' })
        ];

        render(ParameterTable, { props: { ...defaultProps, columns, onUpdate } });

        await fireEvent.click(screen.getByTestId('parameter-table-prompts-add-row'));

        expect(onUpdate).toHaveBeenCalledWith([{ limit: '', enabled: false }]);
    });

    // How a cell of each column type renders, parses and reports its edits is covered directly in
    // ParameterTableCell.test.ts; these tests only cover wiring that belongs to the table.

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

    it('renders every row when there are more rows than the table can show at once', () => {
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
            screen.getByText('Add at least one row and fill in every required cell.')
        ).toBeInTheDocument();
    });

    it('only flags the empty cells of required columns', () => {
        const columns = [column({ name: 'prompt' }), column({ name: 'label', required: false })];

        render(ParameterTable, {
            props: {
                ...defaultProps,
                columns,
                value: [{ prompt: '', label: '' }],
                isMissing: true,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('parameter-table-prompts-prompt-0')).toBeInvalid();
        expect(screen.getByTestId('parameter-table-prompts-label-0')).toBeValid();
    });

    it('flags an empty optional numeric cell so the row cannot be submitted as text', () => {
        // A new row starts an optional number column at '', which the backend rejects for its type
        // even though the column is optional, so the cell has to be flagged on sight.
        const columns = [column({ name: 'limit', paramType: 'int', required: false })];

        render(ParameterTable, {
            props: { ...defaultProps, columns, value: [{ limit: '' }], onUpdate: vi.fn() }
        });

        expect(screen.getByTestId('parameter-table-prompts-limit-0')).toBeInvalid();
    });

    it('never flags an unchecked boolean cell', () => {
        // A checkbox always has a value, so a boolean column must not block submission.
        const columns = [column({ name: 'enabled', paramType: 'bool' })];

        render(ParameterTable, {
            props: {
                ...defaultProps,
                columns,
                value: [{ enabled: false }],
                isMissing: true,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('parameter-table-prompts-enabled-0')).not.toHaveAttribute(
            'aria-invalid'
        );
    });
});
