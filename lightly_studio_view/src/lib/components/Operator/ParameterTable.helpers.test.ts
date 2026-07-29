import { describe, expect, it } from 'vitest';
import type { OperatorParameterColumn } from '$lib/hooks/useOperators/useOperators';
import { buildCellDefault } from './ParameterTable.helpers';

const column = (overrides: Partial<OperatorParameterColumn>): OperatorParameterColumn => ({
    name: 'prompt',
    description: 'What to segment',
    default: undefined,
    required: true,
    paramType: 'str',
    ...overrides
});

describe('buildCellDefault', () => {
    it('keeps a default that matches the column type', () => {
        expect(buildCellDefault(column({ default: 'person' }))).toBe('person');
        expect(buildCellDefault(column({ paramType: 'int', default: 5 }))).toBe(5);
        expect(buildCellDefault(column({ paramType: 'bool', default: true }))).toBe(true);
    });

    it('renders a non-string default of a string column as text', () => {
        expect(buildCellDefault(column({ default: 3 }))).toBe('3');
    });

    it('drops a default that does not fit the column type', () => {
        expect(buildCellDefault(column({ paramType: 'int', default: 'abc' }))).toBe('');
        expect(buildCellDefault(column({ paramType: 'float', default: Number.NaN }))).toBe('');
        expect(buildCellDefault(column({ paramType: 'bool', default: 'yes' }))).toBe(false);
    });

    it('falls back to the empty value of the column type when there is no default', () => {
        expect(buildCellDefault(column({ default: null }))).toBe('');
        expect(buildCellDefault(column({ paramType: 'int' }))).toBe('');
        expect(buildCellDefault(column({ paramType: 'bool' }))).toBe(false);
    });

    it('treats a column type it does not know as text', () => {
        expect(buildCellDefault(column({ paramType: 'datetime', default: 'today' }))).toBe('today');
    });
});
