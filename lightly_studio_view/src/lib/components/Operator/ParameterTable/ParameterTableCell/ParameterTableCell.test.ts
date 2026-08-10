import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ParameterTableCell from './ParameterTableCell.svelte';
import { column } from '../../fixtures';

const defaultProps = {
    column: column(),
    value: '' as string | number | boolean | undefined,
    isInvalid: false,
    label: 'prompts prompt row 1',
    testId: 'cell',
    onUpdate: vi.fn()
};

describe('ParameterTableCell', () => {
    it('renders a str column as a text input holding the cell value', () => {
        render(ParameterTableCell, {
            props: { ...defaultProps, value: 'person', onUpdate: vi.fn() }
        });

        const input = screen.getByTestId('cell');
        expect(input).toHaveAttribute('type', 'text');
        expect(input).toHaveValue('person');
        expect(input).toHaveAttribute('aria-label', 'prompts prompt row 1');
    });

    it('renders an int column as a number input', () => {
        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'int' }),
                value: 3,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('cell')).toHaveAttribute('type', 'number');
    });

    it('renders a float column as a number input stepping in hundredths', () => {
        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'float' }),
                value: 0.5,
                onUpdate: vi.fn()
            }
        });

        const input = screen.getByTestId('cell');
        expect(input).toHaveAttribute('type', 'number');
        expect(input).toHaveAttribute('step', '0.01');
    });

    it('falls back to a text input for an unknown column type', () => {
        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'datetime' }),
                value: '2026-08-03',
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('cell')).toHaveAttribute('type', 'text');
    });

    it('shows an empty input when the cell has no value yet', () => {
        render(ParameterTableCell, {
            props: { ...defaultProps, value: undefined, onUpdate: vi.fn() }
        });

        expect(screen.getByTestId('cell')).toHaveValue('');
    });

    it('reports a text edit as a string', async () => {
        const onUpdate = vi.fn();

        render(ParameterTableCell, { props: { ...defaultProps, onUpdate } });

        await fireEvent.input(screen.getByTestId('cell'), { target: { value: 'person' } });

        expect(onUpdate).toHaveBeenCalledWith('person');
    });

    it('reports a numeric edit as a number', async () => {
        const onUpdate = vi.fn();

        render(ParameterTableCell, {
            props: { ...defaultProps, column: column({ paramType: 'int' }), onUpdate }
        });

        await fireEvent.input(screen.getByTestId('cell'), { target: { value: '42' } });

        expect(onUpdate).toHaveBeenCalledWith(42);
    });

    it('marks the input invalid only when told to', () => {
        const { unmount } = render(ParameterTableCell, {
            props: { ...defaultProps, onUpdate: vi.fn() }
        });

        expect(screen.getByTestId('cell')).toHaveAttribute('aria-invalid', 'false');

        unmount();
        render(ParameterTableCell, {
            props: { ...defaultProps, isInvalid: true, onUpdate: vi.fn() }
        });

        expect(screen.getByTestId('cell')).toHaveAttribute('aria-invalid', 'true');
    });

    it('renders a bool column as a checkbox reflecting the cell value', () => {
        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'bool' }),
                value: true,
                onUpdate: vi.fn()
            }
        });

        const checkbox = screen.getByTestId('cell');
        expect(checkbox).toHaveAttribute('aria-label', 'prompts prompt row 1');
        expect(checkbox).toHaveAttribute('data-state', 'checked');
    });

    it('leaves a boolean cell unchecked when it holds no value', () => {
        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'bool' }),
                value: undefined,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('cell')).toHaveAttribute('data-state', 'unchecked');
    });

    it('reports a checkbox toggle as a boolean', async () => {
        const onUpdate = vi.fn();

        render(ParameterTableCell, {
            props: {
                ...defaultProps,
                column: column({ paramType: 'bool' }),
                value: false,
                onUpdate
            }
        });

        await fireEvent.click(screen.getByTestId('cell'));

        expect(onUpdate).toHaveBeenCalledWith(true);
    });
});
