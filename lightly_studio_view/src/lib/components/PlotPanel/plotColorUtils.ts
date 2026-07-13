import { getColorByLabel, oklchHueWheelColor, oklchToRgb } from '$lib/utils';
import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    HIDDEN_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY
} from './plotCategories';

const OKLCH_LIGHTNESS = 0.65;
const OKLCH_CHROMA = 0.3;

// Sequential single-hue ramp for ordered (numeric) color-bys. A fixed hue with a
// monotonic lightness ramp (light -> dark for low -> high bins) reads as an ordered
// gradient ("darker = higher") and stays colorblind-safe, unlike the hue wheel.
const SEQUENTIAL_HUE = 250;
const SEQUENTIAL_CHROMA = 0.13;
const SEQUENTIAL_LIGHTNESS_LOW_BIN = 0.9;
const SEQUENTIAL_LIGHTNESS_HIGH_BIN = 0.35;

const RESERVED_CATEGORY_COUNT = 3;

export const HIDDEN_COLOR = '#000000';
export const NOT_FILTERED_COLOR = '#222222';
export const FILTERED_COLOR = '#FF7220';
export const UNASSIGNED_COLOR = '#666666';

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

// Maps a colored category to a point on the sequential lightness ramp, ordered so the
// first colored category is the lightest bin and the last is the darkest.
function getSequentialCategoryColor(category: number, categoryCount: number): string {
    const totalColoredCategories = Math.max(1, categoryCount - RESERVED_CATEGORY_COUNT);
    const index = category - RESERVED_CATEGORY_COUNT;
    const fraction = totalColoredCategories <= 1 ? 0 : index / (totalColoredCategories - 1);
    const lightness =
        SEQUENTIAL_LIGHTNESS_LOW_BIN +
        fraction * (SEQUENTIAL_LIGHTNESS_HIGH_BIN - SEQUENTIAL_LIGHTNESS_LOW_BIN);
    const { r, g, b } = oklchToRgb(lightness, SEQUENTIAL_CHROMA, SEQUENTIAL_HUE);
    return `rgb(${r}, ${g}, ${b})`;
}

function getBaseCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    isColorByActive: boolean = false,
    ordered: boolean = false
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

    if (label) {
        return getColorByLabel(label).color;
    }

    if (ordered) {
        return getSequentialCategoryColor(category, categoryCount);
    }

    return getDiscreteCategoryColor(category, categoryCount);
}

export function getCategoryCount(colorLegend?: ReadonlyMap<number, string> | null): number {
    return getMaxCategoryFromLegend(colorLegend) + 1;
}

export function getCategoryColors(
    colorLegend?: ReadonlyMap<number, string> | null,
    useLabelColors: boolean = false,
    isColorByActive: boolean = false,
    ordered: boolean = false
): string[] {
    const categoryCount = getCategoryCount(colorLegend);
    return Array.from({ length: categoryCount }, (_, category) => {
        const label = useLabelColors ? (colorLegend?.get(category) ?? '') : '';
        return getBaseCategoryColor(category, categoryCount, label, isColorByActive, ordered);
    });
}

export function getLegendEntries(
    colorLegend?: ReadonlyMap<number, string> | null,
    hiddenCategories: ReadonlySet<number> = new Set(),
    useLabelColors: boolean = true,
    ordered: boolean = false
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
            color: getBaseCategoryColor(
                category,
                categoryCount,
                useLabelColors ? label : '',
                false,
                ordered
            ),
            hidden: hiddenCategories.has(category)
        }));
}
