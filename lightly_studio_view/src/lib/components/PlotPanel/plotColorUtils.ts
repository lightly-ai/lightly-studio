import { getColorByLabel } from '$lib/utils';

const HSL_SATURATION = 70;
const HSL_LIGHTNESS = 55;
const RESERVED_CATEGORY_COUNT = 2;

export const NOT_FILTERED_COLOR = '#9CA3AF';
export const FILTERED_COLOR = '#F59E0B';
export const UNASSIGNED_COLOR = '#CAAC78';

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

function getDiscreteHslColor(index: number, total: number): string {
    if (total <= 1) {
        return 'hsl(220, 70%, 55%)';
    }

    const hue = Math.round((index * 360) / total) % 360;
    return `hsl(${hue}, ${HSL_SATURATION}%, ${HSL_LIGHTNESS}%)`;
}

function getDiscreteCategoryColor(category: number, categoryCount: number): string {
    const totalColoredCategories = Math.max(1, categoryCount - RESERVED_CATEGORY_COUNT);
    return getDiscreteHslColor(category - RESERVED_CATEGORY_COUNT, totalColoredCategories);
}

function getBaseCategoryColor(
    category: number,
    categoryCount: number,
    label: string,
    isColorByActive: boolean = false
): string {
    if (category === 0) {
        return NOT_FILTERED_COLOR;
    }

    if (category === 1) {
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
    hiddenCategories: ReadonlySet<number> = new Set(),
    useLabelColors: boolean = false,
    isColorByActive: boolean = false
): string[] {
    const categoryCount = getCategoryCount(colorLegend);
    return Array.from({ length: categoryCount }, (_, category) => {
        if (hiddenCategories.has(category)) {
            return isColorByActive ? UNASSIGNED_COLOR : FILTERED_COLOR;
        }

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
