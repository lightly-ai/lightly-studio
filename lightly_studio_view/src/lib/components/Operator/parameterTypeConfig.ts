import type {
    OperatorParameterColumn,
    OperatorParameterType,
    Operator
} from '$lib/hooks/useOperators/useOperators';
import type { Component } from 'svelte';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';
import ParameterTable from './ParameterTable.svelte';

export type ParameterTableRow = Record<string, string>;
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

function isRowFilled(row: ParameterTableRow, columns?: OperatorParameterColumn[]): boolean {
    // Only required columns have to be filled in. Without column information every cell counts as
    // required, which is the stricter fallback.
    const requiredNames = columns
        ? columns.filter((column) => column.required).map((column) => column.name)
        : Object.keys(row);
    return requiredNames.every((name) => (row[name] ?? '').trim().length > 0);
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

export function buildInitialParameters(selectedOperator: Operator): ParameterValues {
    const initial: ParameterValues = {};
    for (const param of selectedOperator.parameters) {
        if (Array.isArray(param.default)) {
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
    table: {
        component: ParameterTable,
        props: {},
        defaultValue: [],
        validate: (value, columns) =>
            Array.isArray(value) && value.length > 0 && value.every((row) => isRowFilled(row, columns))
    },
    default: {
        component: ParameterInput,
        props: { inputType: 'text', parse: identity },
        defaultValue: '',
        validate: (value) => value !== '' && value !== null && value !== undefined
    }
};
