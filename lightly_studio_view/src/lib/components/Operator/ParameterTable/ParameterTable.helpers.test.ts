import { describe, expect, it } from 'vitest';
import type { OperatorParameterColumn } from '$lib/hooks';
import { buildCellDefault, isCellInvalid } from './ParameterTable.helpers';

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

describe('isCellInvalid', () => {
    // The table is valid overall here, so only the backend contract can flag a cell.
    const submittable = { required: true, isMissing: false };

    it('flags an empty numeric cell even when its column is optional', () => {
        // The backend validates every cell against its column type regardless of `required`, so an
        // empty number cell would be rejected as a string rather than skipped.
        for (const paramType of ['int', 'float']) {
            const numeric = column({ name: 'limit', paramType, required: false });

            expect(isCellInvalid({ limit: '' }, numeric, submittable)).toBe(true);
        }
    });

    it('accepts a numeric cell that holds a number', () => {
        const numeric = column({ name: 'limit', paramType: 'int', required: false });

        expect(isCellInvalid({ limit: 0 }, numeric, submittable)).toBe(false);
    });

    it('leaves an empty optional text cell alone', () => {
        // '' is a valid string, so the backend accepts it and the user need not fill it in.
        const text = column({ name: 'label', required: false });

        expect(isCellInvalid({ label: '' }, text, submittable)).toBe(false);
    });

    it('flags an empty required cell only once the table is missing a value', () => {
        const text = column({ name: 'prompt' });

        expect(isCellInvalid({ prompt: '' }, text, submittable)).toBe(false);
        expect(isCellInvalid({ prompt: '' }, text, { required: true, isMissing: true })).toBe(true);
    });
});
