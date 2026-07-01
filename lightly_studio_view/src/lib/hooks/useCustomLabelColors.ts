import { browser } from '$app/environment';
import { CUSTOM_LABEL_COLORS_STORAGE_KEY } from '$lib/constants';
import { get, writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

type CustomLabelColors = Record<string, CustomColor>;

// Narrow an unknown value to CustomLabelColors. JSON.parse only guarantees valid
// JSON, so we reject anything that is not a plain record whose values match the
// { color: string; alpha: number } shape (e.g. arrays or malformed entries).
const isCustomColor = (value: unknown): value is CustomColor => {
    return (
        typeof value === 'object' &&
        value !== null &&
        typeof (value as CustomColor).color === 'string' &&
        typeof (value as CustomColor).alpha === 'number'
    );
};

const parseCustomLabelColors = (value: unknown): CustomLabelColors => {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return {};
    }

    const result: CustomLabelColors = {};
    for (const [label, color] of Object.entries(value)) {
        if (isCustomColor(color)) {
            result[label] = color;
        }
    }
    return result;
};

// Load any previously persisted custom colors so they survive page reloads and
// navigation between datasets. Returns an empty map when running on the server,
// when nothing is stored, or when the stored value is corrupt.
const loadPersistedColors = (): CustomLabelColors => {
    if (!browser) {
        return {};
    }

    try {
        const storedData = localStorage.getItem(CUSTOM_LABEL_COLORS_STORAGE_KEY);
        if (!storedData) {
            return {};
        }
        return parseCustomLabelColors(JSON.parse(storedData));
    } catch (error) {
        console.error(
            `Failed to parse ${CUSTOM_LABEL_COLORS_STORAGE_KEY} from localStorage:`,
            error
        );
        return {};
    }
};

// Persist the custom colors so they are restored on the next load.
const persistColors = (colors: CustomLabelColors) => {
    if (!browser) {
        return;
    }

    try {
        localStorage.setItem(CUSTOM_LABEL_COLORS_STORAGE_KEY, JSON.stringify(colors));
    } catch (error) {
        console.error(
            `Failed to persist ${CUSTOM_LABEL_COLORS_STORAGE_KEY} to localStorage:`,
            error
        );
    }
};

// Initialize the store from persisted data, falling back to an empty object.
const customLabelColorsStore = writable<CustomLabelColors>(loadPersistedColors());

// Mirror every change back to localStorage so colors persist across datasets.
customLabelColorsStore.subscribe(persistColors);

// Store for tracking changes to trigger reactivity
const colorVersion = writable(0);

// Export singleton instance
export const useCustomLabelColors = () => {
    // Get a custom color for a label if it exists
    const getCustomColor = (label: string): CustomColor | undefined => {
        return get(customLabelColorsStore)[label];
    };

    // Set a custom color for a label
    const setCustomColor = (label: string, color: string, alpha: number = 1) => {
        customLabelColorsStore.update((colors) => {
            return { ...colors, [label]: { color, alpha } };
        });

        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    // Check if a label has a custom color
    const hasCustomColor = (label: string): boolean => {
        return !!get(customLabelColorsStore)[label];
    };

    // Delete a custom color for a label
    const deleteCustomColor = (label: string) => {
        customLabelColorsStore.update((colors) => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [label]: _, ...rest } = colors;
            return rest;
        });
        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    // Clear all custom colors
    const clearCustomColors = () => {
        customLabelColorsStore.set({});
        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    return {
        customLabelColorsStore,
        colorVersion,
        getCustomColor,
        setCustomColor,
        hasCustomColor,
        deleteCustomColor,
        clearCustomColors
    };
};
