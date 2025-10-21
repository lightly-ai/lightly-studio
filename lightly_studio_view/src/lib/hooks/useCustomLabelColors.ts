import { get, writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

// Initialize the store with an empty object
const customLabelColorsStore = writable<Record<string, CustomColor>>({});

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
