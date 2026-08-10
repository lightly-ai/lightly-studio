import type {
    OperatorParameter,
    OperatorParameterColumn,
    OperatorParameterType,
    Operator
} from '$lib/hooks';
import type { Component } from 'svelte';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';
import ParameterTable from './ParameterTable/ParameterTable.svelte';

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
    validate: (value: ParameterValue, columns?: OperatorParameterColumn[]) => boolean;
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
 * Whether a cell holds a value of its column's type. Only reached for a value that is present and a
 * column that is not boolean, so a half-typed number input (which reads `''`) counts as empty.
 */
function isCellFilled(
    value: ParameterTableRow[string],
    column: Pick<OperatorParameterColumn, 'paramType'>
): boolean {
    if (value === '') return false;
    return TYPE_CONFIG[toParameterType(column.paramType)].validate(value);
}

/**
 * Whether a cell holds a value the operator can run with. Required cells must be filled; optional
 * ones may be blank only where the backend accepts blank, which a number reading `''` is not.
 */
export function isCellSubmittable(
    value: ParameterTableRow[string] | undefined,
    column: Pick<OperatorParameterColumn, 'paramType' | 'required'>
): boolean {
    // The backend wants every row to hold exactly the declared columns and fills nothing in for a key
    // that is absent, so a missing cell blocks the row whether or not its column is optional.
    if (value === undefined) return false;
    const type = toParameterType(column.paramType);
    // `false` is an answer rather than a blank, so a boolean cell only has to be a boolean — which a
    // stray value from an operator's declared default is not.
    if (type === 'bool') return typeof value === 'boolean';
    // An optional text cell may be blank; every other cell has to hold a value of its type.
    if (type === 'string' && !column.required) return typeof value === 'string';
    return isCellFilled(value, column);
}

/** Whether every cell of a row can be submitted, including required cells being filled in. */
function isRowSubmittable(row: ParameterTableRow, columns?: OperatorParameterColumn[]): boolean {
    // Without columns, fall back to the stricter reading: every cell required and checked as text.
    if (!columns) {
        return Object.values(row).every(
            (value) => typeof value !== 'string' || value.trim().length > 0
        );
    }
    return columns.every((column) => isCellSubmittable(row[column.name], column));
}

export function isValueFilled(
    value: ParameterValue,
    type: OperatorParameterType | 'default',
    columns?: OperatorParameterColumn[]
): boolean {
    if (value === undefined || value === null) return false;
    const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.default;
    return config.validate(value, columns);
}

/** Whether the user has left a parameter alone, which is the one state an optional one may be in. */
const isEmpty = (value: ParameterValue): boolean =>
    value === undefined ||
    value === null ||
    value === '' ||
    (Array.isArray(value) && !value.length);

/**
 * Whether a value can be sent to the backend, which is weaker than being filled in: an optional
 * parameter may be left empty. A table is the one type where empty and incomplete differ, because it
 * may hold rows the backend would reject even when the parameter itself is optional.
 */
export function isValueSubmittable(
    value: ParameterValue,
    param: Pick<OperatorParameter, 'type' | 'columns' | 'required'>
): boolean {
    const required = param.required ?? true;
    // Only an actually empty optional value is waved through; anything the user did enter still has
    // to hold up, so a half-typed number or an incomplete table row cannot slip past unvalidated.
    return (!required && isEmpty(value)) || isValueFilled(value, param.type, param.columns);
}

export function buildInitialParameters(selectedOperator: Operator): ParameterValues {
    const initial: ParameterValues = {};
    for (const param of selectedOperator.parameters) {
        if (param.type === 'table' && Array.isArray(param.default)) {
            // Clone table rows so the default coming from the API is never mutated or shared.
            initial[param.name] = (param.default as ParameterTableRow[]).map((row) => ({ ...row }));
        } else if (param.default !== null) {
            initial[param.name] = param.default as ParameterValue;
        } else {
            initial[param.name] =
                TYPE_CONFIG[param.type]?.defaultValue ?? TYPE_CONFIG.default.defaultValue;
        }
    }
    return initial;
}

/**
 * The component to render a parameter with, plus the props only that type takes. `columns` goes in
 * here rather than on every control, so a text input or checkbox is never handed a table-only prop.
 */
export function getParameterConfig(
    type: OperatorParameterType,
    columns?: OperatorParameterColumn[]
): {
    component: Component<ParameterComponentProps>;
    props: Record<string, unknown>;
} {
    const config = TYPE_CONFIG[type] ?? TYPE_CONFIG.default;
    return {
        component: config.component,
        props: type === 'table' ? { ...config.props, columns } : config.props
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
    table: {
        component: ParameterTable,
        props: {},
        defaultValue: [],
        validate: (value, columns) =>
            Array.isArray(value) &&
            value.length > 0 &&
            value.every((row) => isRowSubmittable(row, columns))
    },
    default: {
        component: ParameterInput,
        props: { inputType: 'text', parse: identity },
        defaultValue: '',
        validate: (value) => value !== '' && value !== null && value !== undefined
    }
};
