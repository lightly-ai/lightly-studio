import { getColorByLabel, oklchHueWheelColor } from '$lib/utils';

const OKLCH_LIGHTNESS = 0.65;
const OKLCH_CHROMA = 0.3;

const RESERVED_CATEGORY_COUNT = 3;

// Index 0 is the Hidden bucket: transparent so its points are not rendered.
export const HIDDEN_COLOR = 'rgba(0, 0, 0, 0)';
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

function getBaseCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    isColorByActive: boolean = false
): string {
    if (category === 0) {
        return HIDDEN_COLOR;
    }

    if (category === 1) {
        return NOT_FILTERED_COLOR;
    }

    if (category === 2) {
        return isColorByActive ? UNASSIGNED_COLOR : FILTERED_COLOR;
    }

    if (label) {
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
    isColorByActive: boolean = false
): string[] {
    const categoryCount = getCategoryCount(colorLegend);
    return Array.from({ length: categoryCount }, (_, category) => {
        const label = useLabelColors ? (colorLegend?.get(category) ?? '') : '';
        return getBaseCategoryColor(category, categoryCount, label, isColorByActive);
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
            color: getBaseCategoryColor(category, categoryCount, useLabelColors ? label : ''),
            hidden: hiddenCategories.has(category)
        }));
}
