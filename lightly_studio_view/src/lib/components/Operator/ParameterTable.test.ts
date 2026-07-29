import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { OperatorParameterColumn } from '$lib/hooks/useOperators/useOperators';
import ParameterTable from './ParameterTable.svelte';
import type { ParameterTableRow } from './parameterTypeConfig';

// Columns come from the API mapper, where every field is present. The factory fills in the parts a
// test does not care about so the fixtures stay readable.
const column = (overrides: Partial<OperatorParameterColumn>): OperatorParameterColumn => ({
    name: 'prompt',
    description: 'What to segment',
    default: undefined,
    required: true,
    paramType: 'str',
    ...overrides
});

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

    it('parses a numeric cell into a number', async () => {
        const onUpdate = vi.fn();
        const columns = [column({ name: 'limit', paramType: 'int' })];

        render(ParameterTable, {
            props: { ...defaultProps, columns, value: [{ limit: '' }], onUpdate }
        });

        const cell = screen.getByTestId('parameter-table-prompts-limit-0');
        expect(cell).toHaveAttribute('type', 'number');

        await fireEvent.input(cell, { target: { value: '7' } });

        expect(onUpdate).toHaveBeenCalledWith([{ limit: 7 }]);
    });

    it('keeps a cleared numeric cell empty instead of storing NaN', async () => {
        const onUpdate = vi.fn();
        const columns = [column({ name: 'threshold', paramType: 'float' })];

        render(ParameterTable, {
            props: { ...defaultProps, columns, value: [{ threshold: 0.5 }], onUpdate }
        });

        await fireEvent.input(screen.getByTestId('parameter-table-prompts-threshold-0'), {
            target: { value: '' }
        });

        expect(onUpdate).toHaveBeenCalledWith([{ threshold: '' }]);
    });

    it('renders a boolean cell as a checkbox and reports the toggled value', async () => {
        const onUpdate = vi.fn();
        const columns = [column({ name: 'enabled', paramType: 'bool' })];

        render(ParameterTable, {
            props: { ...defaultProps, columns, value: [{ enabled: false }], onUpdate }
        });

        const checkbox = screen.getByTestId('parameter-table-prompts-enabled-0');
        expect(checkbox).not.toBeChecked();

        await fireEvent.click(checkbox);

        expect(onUpdate).toHaveBeenCalledWith([{ enabled: true }]);
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

    it('flags an empty required numeric cell but never an unchecked boolean cell', () => {
        const columns = [
            column({ name: 'limit', paramType: 'int' }),
            column({ name: 'enabled', paramType: 'bool' })
        ];

        render(ParameterTable, {
            props: {
                ...defaultProps,
                columns,
                value: [{ limit: '', enabled: false }],
                isMissing: true,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('parameter-table-prompts-limit-0')).toBeInvalid();
        expect(screen.getByTestId('parameter-table-prompts-enabled-0')).not.toHaveAttribute(
            'aria-invalid'
        );
    });

    it('treats a filled numeric cell as valid', () => {
        const columns = [column({ name: 'limit', paramType: 'int' })];

        render(ParameterTable, {
            props: {
                ...defaultProps,
                columns,
                value: [{ limit: 3 }],
                isMissing: true,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('parameter-table-prompts-limit-0')).toBeValid();
    });
});
