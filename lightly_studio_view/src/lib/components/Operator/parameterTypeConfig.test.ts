import { describe, expect, it } from 'vitest';
import type { Operator } from '$lib/hooks';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';
import {
    buildInitialParameters,
    getCellConfig,
    getParameterConfig,
    isCellFilled,
    isValueFilled,
    toParameterType
} from './parameterTypeConfig';

describe('toParameterType', () => {
    it('maps the Python type names of the backend onto parameter types', () => {
        expect(toParameterType('str')).toBe('string');
        expect(toParameterType('int')).toBe('int');
        expect(toParameterType('float')).toBe('float');
        expect(toParameterType('bool')).toBe('bool');
    });

    it('falls back to string for a missing or unknown type name', () => {
        // A column type the GUI does not know yet degrades to a text cell instead of breaking.
        expect(toParameterType(undefined)).toBe('string');
        expect(toParameterType('datetime')).toBe('string');
    });
});

describe('getCellConfig', () => {
    it('renders a str column as a text input that keeps the typed value verbatim', () => {
        const config = getCellConfig({ paramType: 'str' });

        expect(config.type).toBe('string');
        expect(config.inputType).toBe('text');
        expect(config.step).toBeUndefined();
        expect(config.parse('person')).toBe('person');
    });

    it('renders an int column as a number input that parses integers', () => {
        const config = getCellConfig({ paramType: 'int' });

        expect(config.type).toBe('int');
        expect(config.inputType).toBe('number');
        expect(config.parse('42')).toBe(42);
        // A number input reads as `''` while it is being cleared or typed.
        expect(config.parse('')).toBe('');
    });

    it('renders a float column as a number input that steps in hundredths', () => {
        const config = getCellConfig({ paramType: 'float' });

        expect(config.type).toBe('float');
        expect(config.inputType).toBe('number');
        expect(config.step).toBe('0.01');
        expect(config.parse('0.5')).toBe(0.5);
    });

    it('reports a bool column as a boolean cell', () => {
        expect(getCellConfig({ paramType: 'bool' }).type).toBe('bool');
    });

    it('falls back to a text cell for an unknown column type', () => {
        const config = getCellConfig({ paramType: 'datetime' });

        expect(config.type).toBe('string');
        expect(config.inputType).toBe('text');
        expect(config.parse('2026-08-03')).toBe('2026-08-03');
    });
});

describe('isCellFilled', () => {
    it('treats a boolean cell as filled whether or not it is checked', () => {
        // `false` is an answer rather than a blank, so a boolean column never blocks submission.
        expect(isCellFilled(false, { paramType: 'bool' })).toBe(true);
        expect(isCellFilled(true, { paramType: 'bool' })).toBe(true);
        expect(isCellFilled(undefined, { paramType: 'bool' })).toBe(true);
    });

    it('rejects a missing or blank string cell', () => {
        expect(isCellFilled(undefined, { paramType: 'str' })).toBe(false);
        expect(isCellFilled('', { paramType: 'str' })).toBe(false);
        expect(isCellFilled('   ', { paramType: 'str' })).toBe(false);
    });

    it('accepts a string cell with content', () => {
        expect(isCellFilled('person', { paramType: 'str' })).toBe(true);
    });

    it('judges a numeric cell by its value rather than as text', () => {
        expect(isCellFilled(3, { paramType: 'int' })).toBe(true);
        expect(isCellFilled(0, { paramType: 'int' })).toBe(true);
        expect(isCellFilled(0.5, { paramType: 'float' })).toBe(true);
        // A half-typed number input reads as `''`.
        expect(isCellFilled('', { paramType: 'int' })).toBe(false);
    });
});

describe('isValueFilled', () => {
    it('rejects a value that is absent altogether', () => {
        expect(isValueFilled(null, 'string')).toBe(false);
        expect(isValueFilled(undefined as never, 'string')).toBe(false);
    });

    it('requires a string to hold more than whitespace', () => {
        expect(isValueFilled('person', 'string')).toBe(true);
        expect(isValueFilled('', 'string')).toBe(false);
        expect(isValueFilled('   ', 'string')).toBe(false);
    });

    it('accepts either state of a boolean', () => {
        expect(isValueFilled(false, 'bool')).toBe(true);
        expect(isValueFilled(true, 'bool')).toBe(true);
    });

    it('requires a finite number for the numeric types', () => {
        expect(isValueFilled(3, 'int')).toBe(true);
        expect(isValueFilled(0.5, 'float')).toBe(true);
        expect(isValueFilled('', 'int')).toBe(false);
        expect(isValueFilled(Number.NaN, 'float')).toBe(false);
    });

    it('falls back to a plain emptiness check for an unknown type', () => {
        expect(isValueFilled('person', 'unknown' as never)).toBe(true);
        expect(isValueFilled('', 'unknown' as never)).toBe(false);
    });
});

describe('getParameterConfig', () => {
    it('renders bool as a checkbox and the remaining types as inputs', () => {
        expect(getParameterConfig('bool').component).toBe(ParameterCheckbox);
        expect(getParameterConfig('string').component).toBe(ParameterInput);
        expect(getParameterConfig('int').component).toBe(ParameterInput);
        expect(getParameterConfig('float').component).toBe(ParameterInput);
    });

    it('falls back to a text input for an unknown type', () => {
        const config = getParameterConfig('unknown' as never);

        expect(config.component).toBe(ParameterInput);
        expect(config.props).toMatchObject({ inputType: 'text' });
    });
});

describe('buildInitialParameters', () => {
    const operatorWith = (parameters: Operator['parameters']): Operator => ({
        id: 'op-1',
        name: 'SAM3',
        parameters
    });

    it('keeps the default coming from the API', () => {
        const operator = operatorWith([
            { name: 'prompt', type: 'string', default: 'person', required: true },
            { name: 'limit', type: 'int', default: 3, required: true },
            { name: 'enabled', type: 'bool', default: false, required: true }
        ]);

        expect(buildInitialParameters(operator)).toEqual({
            prompt: 'person',
            limit: 3,
            enabled: false
        });
    });

    it('falls back to the empty value of the type when there is no default', () => {
        const operator = operatorWith([
            { name: 'prompt', type: 'string', default: null, required: true },
            { name: 'limit', type: 'int', default: null, required: true },
            { name: 'enabled', type: 'bool', default: null, required: true }
        ]);

        expect(buildInitialParameters(operator)).toEqual({
            prompt: '',
            limit: '',
            enabled: false
        });
    });

    it('falls back to an empty string for a parameter of an unknown type', () => {
        const operator = operatorWith([
            { name: 'when', type: 'datetime' as never, default: null, required: true }
        ]);

        expect(buildInitialParameters(operator)).toEqual({ when: '' });
    });
});
