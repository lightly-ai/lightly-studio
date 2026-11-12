import type { CategoricalMetadataValue } from '$lib/services/types';
import { formatFloat, formatInteger } from '$lib/utils';

export type Range = { min: number; max: number };
export type RangeSource = 'dimension' | 'numeric';

export interface RangeField {
    kind: 'range';
    id: string;
    source: RangeSource;
    key: string;
    title: string;
    unit: string;
    bound: Range;
    value: Range;
}

export interface CategoricalField {
    kind: 'categorical';
    id: string;
    source: 'categorical';
    key: string;
    title: string;
    selected: CategoricalMetadataValue[];
}

export type MetadataField = RangeField | CategoricalField;

export const fieldId = (source: RangeSource | 'categorical', key: string): string =>
    `${source}:${key}`;

export const isFieldActive = (field: MetadataField): boolean =>
    field.kind === 'range'
        ? field.value.min > field.bound.min || field.value.max < field.bound.max
        : field.selected.length > 0;

export const orderByActive = (
    fields: MetadataField[]
): { fields: MetadataField[]; activeCount: number } => {
    const active = fields.filter(isFieldActive);
    const inactive = fields.filter((field) => !isFieldActive(field));
    return { fields: [...active, ...inactive], activeCount: active.length };
};

export const formatRangeSummary = (field: RangeField): string => {
    const isInteger = Number.isInteger(field.bound.min) && Number.isInteger(field.bound.max);
    const format = (num: number): string => (isInteger ? formatInteger(num) : formatFloat(num));
    return `${format(field.value.min)}${field.unit} – ${format(field.value.max)}${field.unit}`;
};
