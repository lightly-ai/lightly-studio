import type {
    MetadataInfoView,
    MetadataJointAxisBucketView,
    MetadataJointAxisView,
    MetadataJointDistributionView
} from '$lib/api/lightly_studio_local';
import type { HeatmapCellRect, HeatmapSelection } from '$lib/components/MetadataHeatmap';
import type {
    CategoricalMetadataValue,
    CategoricalMetadataValues,
    MetadataBounds,
    MetadataValues
} from '$lib/services/types';
import { formatFloat } from '$lib/utils';

/** The metadata filter stores that a heatmap selection reads and writes. */
interface MetadataFilterState {
    metadataValues: MetadataValues;
    categoricalMetadataValues: CategoricalMetadataValues;
    metadataBounds: MetadataBounds;
}

type AxisFilter =
    | { kind: 'clear' }
    | { kind: 'values'; values: CategoricalMetadataValue[] }
    | { kind: 'range'; range: { min: number; max: number } };

const JOINT_METADATA_TYPES = ['string', 'boolean', 'integer', 'float'];

/** The metadata keys that can be an axis of the joint distribution. */
export const selectJointMetadataKeys = (metadataInfo: MetadataInfoView[]): string[] =>
    metadataInfo.filter(({ type }) => JOINT_METADATA_TYPES.includes(type)).map(({ name }) => name);

/** The axis label of a bucket. */
export function formatBucketLabel(bucket: MetadataJointAxisBucketView, axisType: string): string {
    if (bucket.kind === 'other') return 'Other';
    if (bucket.kind === 'missing') return 'Missing';
    if (bucket.kind === 'value') return bucket.value === '' ? '(empty)' : String(bucket.value);
    const min = bucket.min ?? 0;
    const max = bucket.max ?? 0;
    if (axisType === 'integer') return min === max ? String(min) : `${min}–${max}`;
    return `${formatFloat(min)}–${formatFloat(max)}`;
}

/**
 * The buckets that the metadata filters select, so that a selection made in the
 * sidebar also shows in the heatmap. Returns null when neither axis key is filtered.
 */
export function selectionFromFilters(
    distribution: MetadataJointDistributionView,
    state: MetadataFilterState
): HeatmapSelection | null {
    const x = axisSelection(distribution.x_axis, state);
    const y = axisSelection(distribution.y_axis, state);
    return x === null && y === null ? null : { x, y };
}

/**
 * The next metadata filter values after a rectangle of cells is selected. A rectangle
 * that spans a full axis removes the filter of that axis, and selecting the current
 * selection again removes both filters. Returns null when the rectangle selects only
 * the "other" bucket of an axis, because no filter can express it.
 */
export function filtersFromRect(
    distribution: MetadataJointDistributionView,
    rect: HeatmapCellRect,
    state: MetadataFilterState
): Pick<MetadataFilterState, 'metadataValues' | 'categoricalMetadataValues'> | null {
    const { x_axis: xAxis, y_axis: yAxis } = distribution;
    let xFilter = axisFilter(xAxis, rect.x0, rect.x1, state);
    let yFilter = axisFilter(yAxis, rect.y0, rect.y1, state);
    if (!xFilter || !yFilter) return null;

    const current = selectionFromFilters(distribution, state);
    const requested = {
        x: xFilter.kind === 'clear' ? null : indexRange(rect.x0, rect.x1),
        y: yFilter.kind === 'clear' ? null : indexRange(rect.y0, rect.y1)
    };
    if (current && isSameSelection(current, requested)) {
        xFilter = { kind: 'clear' };
        yFilter = { kind: 'clear' };
    }

    const next = {
        metadataValues: { ...state.metadataValues },
        categoricalMetadataValues: { ...state.categoricalMetadataValues }
    };
    applyAxisFilter(next, xAxis, xFilter, state.metadataBounds);
    applyAxisFilter(next, yAxis, yFilter, state.metadataBounds);
    return next;
}

const isNumericAxis = (axis: MetadataJointAxisView): boolean =>
    axis.type === 'integer' || axis.type === 'float';

function axisSelection(axis: MetadataJointAxisView, state: MetadataFilterState): number[] | null {
    return isNumericAxis(axis)
        ? numericAxisSelection(axis, state)
        : categoricalAxisSelection(axis, state.categoricalMetadataValues[axis.key] ?? []);
}

function numericAxisSelection(
    axis: MetadataJointAxisView,
    { metadataValues, metadataBounds }: MetadataFilterState
): number[] | null {
    const range = metadataValues[axis.key];
    const bound = metadataBounds[axis.key];
    if (!range || !bound || (range.min <= bound.min && range.max >= bound.max)) return null;
    // Integer buckets include both bounds. Float buckets cover [min, max).
    const overlaps = (bucket: MetadataJointAxisBucketView) => {
        const min = bucket.min ?? 0;
        const max = bucket.max ?? 0;
        return axis.type === 'integer'
            ? min <= range.max && max >= range.min
            : min < range.max && max > range.min;
    };
    return indicesWhere(axis.buckets, overlaps);
}

function categoricalAxisSelection(
    axis: MetadataJointAxisView,
    selected: CategoricalMetadataValue[]
): number[] | null {
    if (selected.length === 0) return null;
    const includes = (values: unknown[], value: unknown) =>
        values.some((candidate) => Object.is(candidate, value));
    const axisValues = axis.buckets
        .filter(({ kind }) => kind === 'value')
        .map(({ value }) => value);
    // Selected values outside the top values of the axis are in the "other" bucket.
    const selectsOther = selected.some((value) => value !== null && !includes(axisValues, value));
    return indicesWhere(axis.buckets, ({ kind, value }) => {
        if (kind === 'value') return includes(selected, value);
        if (kind === 'missing') return includes(selected, null);
        return kind === 'other' && selectsOther;
    });
}

function axisFilter(
    axis: MetadataJointAxisView,
    first: number,
    last: number,
    { metadataBounds }: MetadataFilterState
): AxisFilter | null {
    if (first === 0 && last === axis.buckets.length - 1) return { kind: 'clear' };
    const buckets = axis.buckets.slice(first, last + 1);
    if (isNumericAxis(axis)) {
        const bound = metadataBounds[axis.key];
        const min = buckets[0].min ?? 0;
        const max = buckets[buckets.length - 1].max ?? 0;
        // The range filter stays inside the bounds, as for the histogram selection.
        return {
            kind: 'range',
            range: {
                min: bound ? Math.max(min, bound.min) : min,
                max: bound ? Math.min(max, bound.max) : max
            }
        };
    }
    const values = buckets.flatMap(({ kind, value }): CategoricalMetadataValue[] => {
        if (kind === 'value') return [value ?? null];
        return kind === 'missing' ? [null] : [];
    });
    return values.length > 0 ? { kind: 'values', values } : null;
}

function applyAxisFilter(
    next: Pick<MetadataFilterState, 'metadataValues' | 'categoricalMetadataValues'>,
    axis: MetadataJointAxisView,
    filter: AxisFilter,
    metadataBounds: MetadataBounds
): void {
    if (filter.kind === 'values') {
        next.categoricalMetadataValues[axis.key] = filter.values;
    } else if (filter.kind === 'range') {
        next.metadataValues[axis.key] = filter.range;
    } else if (!isNumericAxis(axis)) {
        delete next.categoricalMetadataValues[axis.key];
    } else if (metadataBounds[axis.key]) {
        // A range equal to the bounds is no filter.
        next.metadataValues[axis.key] = { ...metadataBounds[axis.key] };
    } else {
        delete next.metadataValues[axis.key];
    }
}

function isSameSelection(first: HeatmapSelection, second: HeatmapSelection): boolean {
    const same = (a: number[] | null, b: number[] | null) =>
        a === null || b === null ? a === b : a.length === b.length && a.every((v, i) => v === b[i]);
    return same(first.x, second.x) && same(first.y, second.y);
}

const indicesWhere = <T>(items: T[], predicate: (item: T) => boolean): number[] =>
    items.flatMap((item, index) => (predicate(item) ? [index] : []));

const indexRange = (first: number, last: number): number[] =>
    Array.from({ length: last - first + 1 }, (_, offset) => first + offset);
