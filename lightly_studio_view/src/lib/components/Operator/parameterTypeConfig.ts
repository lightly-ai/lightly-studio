import type { OperatorParameterType, Operator } from '$lib/hooks/useOperators/useOperators';
import type { Component } from 'svelte';
import ParameterCheckbox from './ParameterCheckbox.svelte';
import ParameterInput from './ParameterInput.svelte';

export type ParameterValue = string | number | boolean | null;
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
        if (param.default !== undefined) {
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
