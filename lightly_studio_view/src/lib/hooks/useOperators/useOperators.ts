import type {
    ParameterColumnView,
    ParameterView,
    RegisteredOperatorMetadata
} from '$lib/api/lightly_studio_local';

export type OperatorParameterType = 'string' | 'int' | 'float' | 'bool';

const mapColumn = (column: ParameterColumnView) => ({
    name: column.name,
    description: column.description,
    default: column.default as unknown,
    required: column.required,
    /**
     * Python type name of the column, e.g. `'str'`, `'int'`, `'float'` or `'bool'`. Columns accept
     * any built-in parameter type, so this is not an `OperatorParameterType`.
     */
    paramType: column.param_type ?? undefined
});

/**
 * A single column of a table parameter as consumed by the GUI. Derived from `mapColumn` so the
 * shape cannot drift from the mapper.
 */
export type OperatorParameterColumn = ReturnType<typeof mapColumn>;

export type OperatorParameter = {
    name: string;
    description?: string;
    default?: unknown;
    required?: boolean;
    type: OperatorParameterType;
    columns?: OperatorParameterColumn[];
};

export type Operator = {
    id: string;
    name: string;
    parameters: OperatorParameter[];
};

const mapParameter = (parameter: ParameterView): OperatorParameter => ({
    name: parameter.name,
    description: parameter.description,
    default: parameter.default,
    required: parameter.required,
    type: (parameter.param_type as OperatorParameterType) ?? 'string',
    columns: parameter.columns?.map(mapColumn)
});

export const createOperatorFromMetadata = (
    metadata: RegisteredOperatorMetadata,
    parameters: ParameterView[]
): Operator => ({
    id: metadata.operator_id,
    name: metadata.name,
    parameters: parameters.map(mapParameter)
});
