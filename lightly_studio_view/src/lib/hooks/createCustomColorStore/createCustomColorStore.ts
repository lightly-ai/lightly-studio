import { get, writable, type Writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

interface CustomColorStore {
    customColorsStore: Writable<Record<string, CustomColor>>;
    colorVersion: Writable<number>;
    getCustomColor: (name: string) => CustomColor | undefined;
    setCustomColor: (name: string, color: string, alpha?: number) => void;
    hasCustomColor: (name: string) => boolean;
    deleteCustomColor: (name: string) => void;
    clearCustomColors: () => void;
}

export const createCustomColorStore = (): CustomColorStore => {
    // Initialize the store with an empty object
    const customColorsStore = writable<Record<string, CustomColor>>({});

    // Store for tracking changes to trigger reactivity
    const colorVersion = writable(0);

    // Get a custom color for a name if it exists
    const getCustomColor = (name: string): CustomColor | undefined => {
        return get(customColorsStore)[name];
    };

    // Set a custom color for a name
    const setCustomColor = (name: string, color: string, alpha: number = 1) => {
        customColorsStore.update((colors) => {
            return { ...colors, [name]: { color, alpha } };
        });

        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    // Check if a name has a custom color
    const hasCustomColor = (name: string): boolean => {
        return !!get(customColorsStore)[name];
    };

    // Delete a custom color for a name
    const deleteCustomColor = (name: string) => {
        customColorsStore.update((colors) => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [name]: _, ...rest } = colors;
            return rest;
        });
        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    // Clear all custom colors
    const clearCustomColors = () => {
        customColorsStore.set({});
        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    return {
        customColorsStore,
        colorVersion,
        getCustomColor,
        setCustomColor,
        hasCustomColor,
        deleteCustomColor,
        clearCustomColors
    };
};
