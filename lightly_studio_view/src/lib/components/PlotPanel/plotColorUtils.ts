import { CATEGORICAL_PALETTE, getColorByLabel, hexToRgb, oklchHueWheelColor } from '$lib/utils';
import type { ColorGradient } from './useArrowData/useArrowData';
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
// The backend groups values beyond the palette size into one "Other (…)" category.
export const OTHER_COLOR = '#9a8f80';
const OTHER_LABEL_PREFIX = 'Other (';

// Bright samples of the turbo colormap, blue to red. Turbo's dark ends are left out, so every
// value stays visible on the black plot background.
export const GRADIENT_STOPS = ['#4666ec', '#27d7c3', '#96fa50', '#ffa323', '#c52a0b'];

/** Returns the gradient color at a position in [0, 1]. */
export function getGradientColor(position: number): string {
    const scaled = Math.max(0, Math.min(1, position)) * (GRADIENT_STOPS.length - 1);
    const index = Math.min(Math.floor(scaled), GRADIENT_STOPS.length - 2);
    const fraction = scaled - index;
    const from = hexToRgb(GRADIENT_STOPS[index]);
    const to = hexToRgb(GRADIENT_STOPS[index + 1]);
    const mix = (a: number, b: number) => Math.round(a + (b - a) * fraction);
    return `rgb(${mix(from.r, to.r)}, ${mix(from.g, to.g)}, ${mix(from.b, to.b)})`;
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
    const paletteColor = CATEGORICAL_PALETTE[category - RESERVED_CATEGORY_COUNT];
    if (paletteColor !== undefined) {
        return paletteColor;
    }
    const totalColoredCategories = Math.max(1, categoryCount - RESERVED_CATEGORY_COUNT);
    return getDiscreteOklchColor(category - RESERVED_CATEGORY_COUNT, totalColoredCategories);
}

function getBaseCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    useLabelColor: boolean,
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

    if (label.startsWith(OTHER_LABEL_PREFIX)) {
        return OTHER_COLOR;
    }

    if (useLabelColor) {
        return getColorByLabel(label).color;
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
    colorGradient: ColorGradient | null = null
): string[] {
    const categoryCount = getCategoryCount(colorLegend);
    return Array.from({ length: categoryCount }, (_, category) => {
        if (colorGradient && category >= RESERVED_CATEGORY_COUNT) {
            return getGradientColor(colorGradient.positions.get(category) ?? 0);
        }
        const label = colorLegend?.get(category) ?? '';
        return getBaseCategoryColor(
            category,
            categoryCount,
            label,
            useLabelColors && label !== '',
            isColorByActive
        );
    });
}

export function getLegendEntries(
    colorLegend?: ReadonlyMap<number, string> | null,
    hiddenCategories: ReadonlySet<number> = new Set(),
    useLabelColors: boolean = true
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
            color: getBaseCategoryColor(category, categoryCount, label, useLabelColors),
            hidden: hiddenCategories.has(category)
        }));
}
