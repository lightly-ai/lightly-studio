import { getColorByLabel, oklchHueWheelColor } from '$lib/utils';
import { turboInto } from '$lib/components/PointCloudViewer/colormap';
import type { PlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from './plotCategories';

const OKLCH_LIGHTNESS = 0.65;
const OKLCH_CHROMA = 0.3;

const RESERVED_CATEGORY_COUNT = 3;

export const HIDDEN_COLOR = '#000000';
export const NOT_FILTERED_COLOR = '#606060';
export const FILTERED_COLOR = '#FF7220';
export const UNASSIGNED_COLOR = '#B0B0B0';

const NUMERIC_METADATA_TYPES = new Set(['integer', 'float']);

// How colored categories get their color. `label` colors each category by its legend label,
// `gradient` colors ordered numeric buckets from low to high, `discrete` spreads hues evenly.
export type PlotColorMode = 'discrete' | 'label' | 'gradient';

interface GetPlotColorModeParams {
    colorByType: PlotColorByType | null;
    // Type of the selected metadata field, e.g. 'float'. Undefined when no field is selected.
    metadataFieldType: string | undefined;
}

interface LegendEntry {
    cat: number;
    label: string;
    color: string;
    hidden: boolean;
}

function getMaxCategoryFromLegend(colorLegend?: ReadonlyMap<number, string> | null): number {
    if (!colorLegend || colorLegend.size === 0) {
        return RESERVED_CATEGORY_COUNT - 1;
    }

    return Math.max(...colorLegend.keys());
}

function getDiscreteOklchColor(index: number, total: number): string {
    const { r, g, b } = oklchHueWheelColor({
        index,
        count: total,
        lightness: OKLCH_LIGHTNESS,
        chroma: OKLCH_CHROMA
    });
    return `rgb(${r}, ${g}, ${b})`;
}

function getDiscreteCategoryColor(category: number, categoryCount: number): string {
    const totalColoredCategories = Math.max(1, categoryCount - RESERVED_CATEGORY_COUNT);
    return getDiscreteOklchColor(category - RESERVED_CATEGORY_COUNT, totalColoredCategories);
}

function getGradientCategoryColor(category: number, categoryCount: number): string {
    const lastColoredIndex = Math.max(1, categoryCount - RESERVED_CATEGORY_COUNT - 1);
    const position = (category - RESERVED_CATEGORY_COUNT) / lastColoredIndex;
    const rgb = new Float32Array(3);
    turboInto(position, rgb, 0);
    const [r, g, b] = Array.from(rgb, (channel) => Math.round(channel * 255));
    return `rgb(${r}, ${g}, ${b})`;
}

function getColoredCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    colorMode: PlotColorMode
): string {
    if (colorMode === 'gradient') {
        return getGradientCategoryColor(category, categoryCount);
    }

    if (colorMode === 'label' && label) {
        return getColorByLabel(label).color;
    }

    return getDiscreteCategoryColor(category, categoryCount);
}

function getBaseCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    colorMode: PlotColorMode,
    isColorByActive: boolean = false
): string {
    if (category === HIDDEN_CATEGORY) {
        return HIDDEN_COLOR;
    }

    if (category === EXCLUDED_BY_FILTERS_CATEGORY) {
        return NOT_FILTERED_COLOR;
    }

    if (category === INCLUDED_BY_FILTERS_CATEGORY) {
        return isColorByActive ? UNASSIGNED_COLOR : FILTERED_COLOR;
    }

    return getColoredCategoryColor(category, categoryCount, label, colorMode);
}

export function getPlotColorMode({
    colorByType,
    metadataFieldType
}: GetPlotColorModeParams): PlotColorMode {
    if (colorByType === 'annotation_label') {
        return 'label';
    }

    const isNumericField =
        metadataFieldType !== undefined && NUMERIC_METADATA_TYPES.has(metadataFieldType);
    if (colorByType === 'metadata' && isNumericField) {
        return 'gradient';
    }

    return 'discrete';
}

export function getCategoryCount(colorLegend?: ReadonlyMap<number, string> | null): number {
    return getMaxCategoryFromLegend(colorLegend) + 1;
}

export function getCategoryColors(
    colorLegend?: ReadonlyMap<number, string> | null,
    colorMode: PlotColorMode = 'discrete',
    isColorByActive: boolean = false
): string[] {
    const categoryCount = getCategoryCount(colorLegend);
    return Array.from({ length: categoryCount }, (_, category) => {
        const label = colorLegend?.get(category) ?? '';
        return getBaseCategoryColor(category, categoryCount, label, colorMode, isColorByActive);
    });
}

export function getLegendEntries(
    colorLegend?: ReadonlyMap<number, string> | null,
    hiddenCategories: ReadonlySet<number> = new Set(),
    colorMode: PlotColorMode = 'label'
): LegendEntry[] {
    if (!colorLegend || colorLegend.size === 0) {
        return [];
    }

    const categoryCount = getCategoryCount(colorLegend);

    return [...colorLegend.entries()]
        .filter(([category]) => category >= RESERVED_CATEGORY_COUNT)
        .sort(([leftCategory], [rightCategory]) => leftCategory - rightCategory)
        .map(([category, label]) => ({
            cat: category,
            label,
            color: getBaseCategoryColor(category, categoryCount, label, colorMode),
            hidden: hiddenCategories.has(category)
        }));
}
