import { describe, expect, it } from 'vitest';
import type { ParameterView, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';
import { createOperatorFromMetadata, type Operator } from '$lib/hooks';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';
import ParameterTable from './ParameterTable/ParameterTable.svelte';
import { column } from './fixtures';
import {
    buildInitialParameters,
    getCellConfig,
    getParameterConfig,
    isValueFilled,
    isValueSubmittable,
    toParameterType,
    type ParameterTableRow
} from './parameterTypeConfig';

const COLUMNS = [column({ name: 'prompt' }), column({ name: 'label' })];

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

    it('passes columns to the table only, so other controls take no table-only prop', () => {
        expect(getParameterConfig('table', COLUMNS).props).toMatchObject({ columns: COLUMNS });
        expect(getParameterConfig('string', COLUMNS).props).not.toHaveProperty('columns');
        expect(getParameterConfig('bool', COLUMNS).props).not.toHaveProperty('columns');
    });
});

describe('isValueSubmittable', () => {
    const table = (required: boolean) => ({ type: 'table' as const, columns: COLUMNS, required });

    it('requires a required parameter to be filled in', () => {
        expect(isValueSubmittable([], table(true))).toBe(false);
        expect(isValueSubmittable('', { type: 'string', required: true })).toBe(false);
        expect(isValueSubmittable('person', { type: 'string', required: true })).toBe(true);
    });

    it('lets an optional parameter be empty', () => {
        expect(isValueSubmittable([], table(false))).toBe(true);
        expect(isValueSubmittable(null, table(false))).toBe(true);
        expect(isValueSubmittable('', { type: 'string', required: false })).toBe(true);
    });

    it('still validates an optional value the user did enter', () => {
        // Optional means it may be left empty, not that anything goes once it holds something.
        expect(isValueSubmittable('   ', { type: 'string', required: false })).toBe(false);
        expect(isValueSubmittable(Number.NaN, { type: 'int', required: false })).toBe(false);
        expect(isValueSubmittable(3, { type: 'int', required: false })).toBe(true);
        // A table value that is not a row list at all cannot be sent either.
        expect(isValueSubmittable('oops' as never, table(false))).toBe(false);
    });

    it('still rejects incomplete rows in an optional table', () => {
        // The rows are optional as a whole, but each one the user added has to be submittable.
        expect(isValueSubmittable([{ prompt: 'person', label: '' }], table(false))).toBe(false);
        expect(isValueSubmittable([{ prompt: 'person', label: 'pedestrian' }], table(false))).toBe(
            true
        );
    });
});

describe('isValueFilled for a table', () => {
    it('requires at least one row where every required cell is filled', () => {
        expect(isValueFilled([], 'table', COLUMNS)).toBe(false);
        expect(isValueFilled([{ prompt: 'person', label: '   ' }], 'table', COLUMNS)).toBe(false);
        expect(isValueFilled([{ prompt: 'person', label: 'pedestrian' }], 'table', COLUMNS)).toBe(
            true
        );
    });

    it('rejects a table where only some rows are complete', () => {
        const rows = [
            { prompt: 'person', label: 'pedestrian' },
            { prompt: 'car', label: '' }
        ];

        expect(isValueFilled(rows, 'table', COLUMNS)).toBe(false);
    });

    it('lets a cell of an optional column stay blank, but only where blank is a value', () => {
        const text = [column({ name: 'prompt' }), column({ name: 'label', required: false })];
        const numeric = [column({ name: 'threshold', paramType: 'float', required: false })];

        expect(isValueFilled([{ prompt: 'person', label: '' }], 'table', text)).toBe(true);
        expect(isValueFilled([{ prompt: '', label: 'pedestrian' }], 'table', text)).toBe(false);
        // A number input reads as `''` while empty or mid-edit, which the backend rejects.
        expect(isValueFilled([{ threshold: '' }], 'table', numeric)).toBe(false);
        expect(isValueFilled([{ threshold: 0.5 }], 'table', numeric)).toBe(true);
    });

    it('treats every cell as required when no columns are known', () => {
        expect(isValueFilled([{ prompt: 'person', label: '' }], 'table')).toBe(false);
        expect(isValueFilled([{ prompt: 'person', label: 'pedestrian' }], 'table')).toBe(true);
    });

    it('accepts an unchecked boolean cell but not a missing one', () => {
        const columns = [column({ name: 'enabled', paramType: 'bool' })];

        // `false` is an answer rather than a blank, so an unchecked box is submittable.
        expect(isValueFilled([{ enabled: false }], 'table', columns)).toBe(true);
        // An API default can omit the key altogether, which would submit a row without it.
        expect(isValueFilled([{}], 'table', columns)).toBe(false);
    });

    it('rejects a boolean cell holding something other than a boolean', () => {
        // A checkbox only ever emits a boolean, but an operator's declared default is free to put
        // anything in the row, and the backend would refuse it.
        for (const required of [true, false]) {
            const columns = [column({ name: 'enabled', paramType: 'bool', required })];

            expect(isValueFilled([{ enabled: 'false' }], 'table', columns)).toBe(false);
            expect(isValueFilled([{ enabled: 1 }], 'table', columns)).toBe(false);
            expect(isValueFilled([{ enabled: true }], 'table', columns)).toBe(true);
        }
    });

    it('lets an API default omit a cell of an optional column, whatever its type', () => {
        // The backend applies the column's own default for a key that is absent, so the row is
        // submittable as it stands. Every type is treated alike here.
        for (const paramType of ['str', 'int', 'float', 'bool']) {
            const columns = [column({ name: 'extra', paramType, required: false })];

            expect(isValueFilled([{}], 'table', columns)).toBe(true);
        }
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
            { name: 'enabled', type: 'bool', default: null, required: true },
            { name: 'prompts', type: 'table', default: null, required: true }
        ]);

        expect(buildInitialParameters(operator)).toEqual({
            prompt: '',
            limit: '',
            enabled: false,
            prompts: []
        });
    });

    it('falls back to an empty string for a parameter of an unknown type', () => {
        const operator = operatorWith([
            { name: 'when', type: 'datetime' as never, default: null, required: true }
        ]);

        expect(buildInitialParameters(operator)).toEqual({ when: '' });
    });

    it('clones table rows so the default from the API is not shared', () => {
        const defaultRows = [{ prompt: 'person', label: 'pedestrian' }];
        const operator = operatorWith([
            { name: 'prompts', type: 'table', default: defaultRows, required: true }
        ]);

        const initial = buildInitialParameters(operator);

        expect(initial.prompts).toEqual(defaultRows);
        expect(initial.prompts).not.toBe(defaultRows);
        expect((initial.prompts as ParameterTableRow[])[0]).not.toBe(defaultRows[0]);
    });

    it('maps a table parameter straight from the API payload to a rendered table', () => {
        // Literal response of GET /operators/{id}/parameters, pinned by the backend test
        // `test_get_operator_parameters__table_parameter`. Guards the backend/frontend seam.
        const apiParameters: ParameterView[] = [
            {
                name: 'prompts',
                description: 'Prompts and labels.',
                default: [{ prompt: 'person', threshold: 0.5 }],
                required: true,
                param_type: 'table',
                columns: [
                    {
                        name: 'prompt',
                        description: 'What to segment.',
                        default: null,
                        required: true,
                        param_type: 'str'
                    },
                    {
                        name: 'threshold',
                        description: '',
                        default: 0.5,
                        required: false,
                        param_type: 'float'
                    }
                ]
            }
        ];
        const metadata = {
            operator_id: 'op-1',
            name: 'SAM3 Segmentation',
            supported_scopes: []
        } as RegisteredOperatorMetadata;

        const operator = createOperatorFromMetadata(metadata, apiParameters);

        expect(operator.parameters[0].type).toBe('table');
        // `param_type` becomes `paramType`; the rest of each column carries over unchanged.
        expect(
            operator.parameters[0].columns?.map((c) => [c.name, c.paramType, c.required])
        ).toEqual([
            ['prompt', 'str', true],
            ['threshold', 'float', false]
        ]);
        expect(getParameterConfig('table').component).toBe(ParameterTable);
        expect(buildInitialParameters(operator).prompts).toEqual([
            { prompt: 'person', threshold: 0.5 }
        ]);
    });
});
