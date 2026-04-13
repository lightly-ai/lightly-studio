/**
 * Local type definitions mirroring @svar-ui/filter-store types.
 * Used as a workaround for the package's broken `types` path in its package.json.
 */

export type TGlue = 'and' | 'or';
export type TType = 'number' | 'text' | 'date' | 'tuple';
export type TFilterType =
    | 'greater'
    | 'less'
    | 'greaterOrEqual'
    | 'lessOrEqual'
    | 'equal'
    | 'notEqual'
    | 'contains'
    | 'notContains'
    | 'beginsWith'
    | 'notBeginsWith'
    | 'endsWith'
    | 'notEndsWith'
    | 'between'
    | 'notBetween';

export interface IFilterSet {
    rules?: (IFilter | IFilterSet)[];
    glue?: TGlue;
}

export interface IFilter {
    field: string;
    type?: TType;
    filter?: TFilterType;
    includes?: (number | string | Date)[];
    value?: number | string | Date;
}

export interface IField {
    id: string;
    label: string;
    type: TType;
}

export interface ValidationError {
    code: string;
    field?: string;
    value?: string;
    message?: string;
}

export interface ParseResult {
    config: IFilterSet | IFilter | null;
    isInvalid: boolean | ValidationError;
    naturalText: string | null;
}

export interface FilterQueryEvent {
    text: string;
    parsed?: ParseResult;
    error?: ValidationError | null;
    startProgress: () => void;
    endProgress: () => void;
}
