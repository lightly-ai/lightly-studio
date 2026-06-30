import { browser } from '$app/environment';
import { CUSTOM_LABEL_COLORS_STORAGE_KEY } from '$lib/constants';
import { get, writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

type CustomLabelColors = Record<string, CustomColor>;

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
        return JSON.parse(storedData) as CustomLabelColors;
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
