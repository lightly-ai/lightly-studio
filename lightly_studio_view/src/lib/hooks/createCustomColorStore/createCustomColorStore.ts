import { derived, get, writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

export const createCustomColorStore = () => {
    // Saved layer: colors that are persisted.
    const savedColors = writable<Record<string, CustomColor>>({});

    // Preview layer: one picker session's unsaved color per name. A null color
    // hides the saved entry, so the default color shows.
    const previews = writable<Record<string, { owner: symbol; color: CustomColor | null }>>({});

    // The saved layer overlaid with previews.
    const customColorsStore = derived([savedColors, previews], ([$saved, $previews]) => {
        const merged = { ...$saved };
        for (const [name, { color }] of Object.entries($previews)) {
            if (color) merged[name] = color;
            else delete merged[name];
        }
        return merged;
    });

    // Store for tracking changes to trigger reactivity
    const colorVersion = writable(0);

    // Get a custom color for a name if it exists
    const getCustomColor = (name: string): CustomColor | undefined => {
        return get(customColorsStore)[name];
    };

    // Set a custom color for a name
    const setCustomColor = (name: string, color: string, alpha: number = 1) => {
        savedColors.update((colors) => {
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
        savedColors.update((colors) => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [name]: _, ...rest } = colors;
            return rest;
        });
        // Increment version to trigger reactivity
        colorVersion.update((v) => v + 1);
    };

    // Show a preview color for a name, replacing any earlier preview
    const setPreviewColor = (name: string, color: CustomColor | null, owner: symbol) => {
        previews.update((current) => ({ ...current, [name]: { owner, color } }));
        colorVersion.update((v) => v + 1);
    };

    // Drop a preview, unless a newer owner replaced it
    const clearPreviewColor = (name: string, owner: symbol) => {
        if (get(previews)[name]?.owner !== owner) return;
        previews.update((current) => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [name]: _, ...rest } = current;
            return rest;
        });
        colorVersion.update((v) => v + 1);
    };

    // Check the saved layer only
    const hasSavedColor = (name: string): boolean => !!get(savedColors)[name];

    // Replace the saved layer; previews stay
    const replaceSavedColors = (colors: Record<string, CustomColor>) => {
        savedColors.set({ ...colors });
        colorVersion.update((v) => v + 1);
    };

    // Clear all custom colors
    const clearCustomColors = () => {
        savedColors.set({});
        previews.set({});
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
        clearCustomColors,
        setPreviewColor,
        clearPreviewColor,
        hasSavedColor,
        replaceSavedColors
    };
};
