import type {
    ParameterColumnView,
    ParameterView,
    RegisteredOperatorMetadata
} from '$lib/api/lightly_studio_local';

export type OperatorParameterType = 'string' | 'int' | 'float' | 'bool' | 'table';

export type OperatorParameterColumn = {
    name: string;
    description?: string;
    default?: string;
    required: boolean;
};

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

const mapColumn = (column: ParameterColumnView): OperatorParameterColumn => ({
    name: column.name,
    description: column.description,
    // Table cells are strings, so anything else cannot pre-fill a cell.
    default: typeof column.default === 'string' ? column.default : undefined,
    required: column.required
});

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
