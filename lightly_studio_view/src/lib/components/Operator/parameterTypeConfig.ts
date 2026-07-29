import type {
    OperatorParameterColumn,
    OperatorParameterType,
    Operator
} from '$lib/hooks/useOperators/useOperators';
import type { Component } from 'svelte';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';

/**
 * A single row of a table parameter. Cells are typed after their column: `str` columns hold a
 * string, `int` and `float` columns a number (or `''` while the number input is mid-edit) and
 * `bool` columns a boolean.
 */
export type ParameterTableRow = Record<string, string | number | boolean>;
export type ParameterValue = string | number | boolean | null | ParameterTableRow[];
export type ParameterValues = Record<string, ParameterValue>;

export type ParameterComponentProps = {
    name: string;
    value: ParameterValue;
    required: boolean;
    isMissing: boolean;
    description?: string;
    onUpdate: (value: ParameterValue) => void;
    inputType?: 'text' | 'number';
    step?: string;
    parse?: (value: string) => string | number;
    columns?: OperatorParameterColumn[];
};

export type TypeConfig = {
    component: Component<ParameterComponentProps>;
    props: Record<string, unknown>;
    defaultValue: ParameterValue;
    validate: (value: ParameterValue) => boolean;
};

const parseIntegerValue = (value: string) => (value === '' ? '' : Number.parseInt(value, 10));
const parseFloatValue = (value: string) => (value === '' ? '' : Number.parseFloat(value));
const identity = (value: string) => value;

/**
 * Python type names as emitted by the backend for table columns, mapped onto the frontend parameter
 * types. `BuiltinParameter` reports `str` where `OperatorParameterType` says `string`; every other
 * name already lines up.
 */
const PYTHON_TYPE_ALIASES: Record<string, OperatorParameterType> = {
    str: 'string',
    int: 'int',
    float: 'float',
    bool: 'bool'
};

/**
 * Translates the Python type name of a table column into a parameter type. An unknown or missing
 * name falls back to `string`, so a column type the GUI does not know yet degrades to a text cell
 * instead of breaking the table.
 */
export function toParameterType(paramType: string | undefined): OperatorParameterType {
    return (paramType && PYTHON_TYPE_ALIASES[paramType]) || 'string';
}

/**
 * How a single cell of the given column is rendered and parsed. Delegates to `TYPE_CONFIG`, so a
 * cell behaves like a standalone parameter of the same type.
 */
export function getCellConfig(column: Pick<OperatorParameterColumn, 'paramType'>): {
    type: OperatorParameterType;
    inputType: 'text' | 'number';
    step?: string;
    parse: (value: string) => string | number;
} {
    const type = toParameterType(column.paramType);
    const props = TYPE_CONFIG[type].props as {
        inputType?: 'text' | 'number';
        step?: string;
        parse?: (value: string) => string | number;
    };
    return {
        type,
        inputType: props.inputType ?? 'text',
        step: props.step,
        parse: props.parse ?? identity
    };
}

/**
 * Whether a single cell counts as filled in. Booleans are always filled, because `false` is a real
 * answer rather than a missing one, and a half-typed number input (which reads `''`) counts as
 * empty.
 */
export function isCellFilled(
    value: ParameterTableRow[string] | undefined,
    column: Pick<OperatorParameterColumn, 'paramType'>
): boolean {
    const type = toParameterType(column.paramType);
    if (type === 'bool') return true;
    if (value === undefined || value === '') return false;
    return TYPE_CONFIG[type].validate(value);
}

export function isValueFilled(
    value: ParameterValue,
    type: OperatorParameterType | 'default'
): boolean {
    if (value === undefined || value === null) return false;
    const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.default;
    return config.validate(value);
}

export function buildInitialParameters(selectedOperator: Operator): ParameterValues {
    const initial: ParameterValues = {};
    for (const param of selectedOperator.parameters) {
        if (param.default !== null) {
            initial[param.name] = param.default as ParameterValue;
        } else {
            initial[param.name] =
                TYPE_CONFIG[param.type]?.defaultValue ?? TYPE_CONFIG.default.defaultValue;
        }
    }
    return initial;
}

export function getParameterConfig(type: OperatorParameterType): {
    component: Component<ParameterComponentProps>;
    props: Record<string, unknown>;
} {
    const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.default;
    return {
        component: config.component,
        props: config.props
    };
}

const TYPE_CONFIG: Record<OperatorParameterType | 'default', TypeConfig> = {
    bool: {
        component: ParameterCheckbox,
        props: {},
        defaultValue: false,
        validate: (value) => typeof value === 'boolean'
    },
    int: {
        component: ParameterInput,
        props: { inputType: 'number', parse: parseIntegerValue },
        defaultValue: '',
        validate: (value) => typeof value === 'number' && Number.isFinite(value)
    },
    float: {
        component: ParameterInput,
        props: { inputType: 'number', step: '0.01', parse: parseFloatValue },
        defaultValue: '',
        validate: (value) => typeof value === 'number' && Number.isFinite(value)
    },
    string: {
        component: ParameterInput,
        props: { inputType: 'text', parse: identity },
        defaultValue: '',
        validate: (value) => typeof value === 'string' && value.trim().length > 0
    },
    default: {
        component: ParameterInput,
        props: { inputType: 'text', parse: identity },
        defaultValue: '',
        validate: (value) => value !== '' && value !== null && value !== undefined
    }
};
