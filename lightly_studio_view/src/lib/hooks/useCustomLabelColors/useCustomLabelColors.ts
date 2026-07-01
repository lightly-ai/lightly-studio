import { CUSTOM_LABEL_COLORS_STORAGE_KEY } from '$lib/constants';
import { useLocalStorage } from '$lib/hooks/useLocalStorage/useLocalStorage';
import { get } from 'svelte/store';

export type CustomColor = {
    color: string;
    alpha: number;
};

type CustomLabelColors = Record<string, CustomColor>;

// Narrow an unknown value to CustomColor. JSON.parse only guarantees valid JSON,
// so we reject anything that is not a { color: string; alpha: number } shape.
const isCustomColor = (value: unknown): value is CustomColor =>
    typeof value === 'object' &&
    value !== null &&
    typeof (value as CustomColor).color === 'string' &&
    typeof (value as CustomColor).alpha === 'number';

const parseCustomLabelColors = (value: unknown): CustomLabelColors => {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return {};
    }
    return Object.fromEntries(Object.entries(value).filter(([, color]) => isCustomColor(color)));
};

// Module-level singleton store, backed by localStorage so colors persist across
// reloads and datasets. Corrupt or unexpected payloads are dropped by the parser.
const customLabelColorsStore = useLocalStorage<CustomLabelColors>(
    CUSTOM_LABEL_COLORS_STORAGE_KEY,
    {},
    parseCustomLabelColors
);

const getCustomColor = (label: string): CustomColor | undefined =>
    get(customLabelColorsStore)[label];

const hasCustomColor = (label: string): boolean => getCustomColor(label) !== undefined;

const setCustomColor = (label: string, color: string, alpha: number = 1) => {
    customLabelColorsStore.update((colors) => ({ ...colors, [label]: { color, alpha } }));
};

const deleteCustomColor = (label: string) => {
    customLabelColorsStore.update((colors) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [label]: _, ...rest } = colors;
        return rest;
    });
};

const clearCustomColors = () => customLabelColorsStore.set({});

export const useCustomLabelColors = () => ({
    customLabelColorsStore,
    getCustomColor,
    setCustomColor,
    hasCustomColor,
    deleteCustomColor,
    clearCustomColors
});
