import type { CategoricalMetadataValue, MetadataBounds } from '$lib/services/types';
import { formatFloat } from '$lib/utils';

export type Range = MetadataBounds[string];
export type RangeSource = 'dimension' | 'video' | 'frame' | 'numeric';

export interface RangeField {
    kind: 'range';
    id: string;
    source: RangeSource;
    key: string;
    title: string;
    unit: string;
    /** Whether the field accepts only whole numbers. */
    integer: boolean;
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

export interface OrderedFields {
    fields: MetadataField[];
    activeCount: number;
}

export const orderByActive = (fields: MetadataField[]): OrderedFields => {
    const active = fields.filter(isFieldActive);
    const inactive = fields.filter((field) => !isFieldActive(field));
    return { fields: [...active, ...inactive], activeCount: active.length };
};

export const formatRangeSummary = (field: RangeField): string => {
    const { value, unit } = field;
    return `${formatFloat(value.min)}${unit} – ${formatFloat(value.max)}${unit}`;
};
