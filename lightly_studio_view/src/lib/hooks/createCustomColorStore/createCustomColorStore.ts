import { derived, get, writable, type Readable, type Writable } from 'svelte/store';

// Type for storing custom colors
export type CustomColor = {
    color: string;
    alpha: number;
};

// Identifies one save request. A newer save, or a reset, makes older tickets stale.
type SaveTicket = { seq: number; generation: number };

interface CustomColorStore {
    customColorsStore: Readable<Record<string, CustomColor>>;
    colorVersion: Writable<number>;
    getCustomColor: (name: string) => CustomColor | undefined;
    setCustomColor: (name: string, color: string, alpha?: number) => void;
    hasCustomColor: (name: string) => boolean;
    deleteCustomColor: (name: string) => void;
    clearCustomColors: () => void;
    setPreviewColor: (name: string, color: CustomColor | null, owner: symbol) => void;
    clearPreviewColor: (name: string, owner: symbol) => void;
    getSavedColor: (name: string) => CustomColor | undefined;
    hasSavedColor: (name: string) => boolean;
    replaceSavedColors: (colors: Record<string, CustomColor>) => void;
    beginSave: (name: string) => SaveTicket;
    setSavedColor: (name: string, color: CustomColor | undefined, ticket: SaveTicket) => void;
    reset: () => void;
    getGeneration: () => number;
}

export const createCustomColorStore = (): CustomColorStore => {
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

    // Get a color from the saved layer only
    const getSavedColor = (name: string): CustomColor | undefined => get(savedColors)[name];

    // Check the saved layer only
    const hasSavedColor = (name: string): boolean => !!getSavedColor(name);

    // Replace the saved layer; previews stay
    const replaceSavedColors = (colors: Record<string, CustomColor>) => {
        savedColors.set({ ...colors });
        colorVersion.update((v) => v + 1);
    };

    // Save bookkeeping. A reset bumps the generation, so saves begun before it never apply.
    let generation = 0;
    let lastBegun: Record<string, number> = {};
    let lastApplied: Record<string, number> = {};

    // Start a save for a name. Later saves of the same name get a higher seq.
    const beginSave = (name: string): SaveTicket => {
        const seq = (lastBegun[name] ?? 0) + 1;
        lastBegun[name] = seq;
        return { seq, generation };
    };

    // Apply a finished save to the saved layer, unless a newer save or a reset came first.
    // An undefined color deletes the saved entry.
    const setSavedColor = (name: string, color: CustomColor | undefined, ticket: SaveTicket) => {
        if (ticket.generation !== generation) return;
        if (ticket.seq <= (lastApplied[name] ?? 0)) return;
        lastApplied[name] = ticket.seq;
        if (color) {
            savedColors.update((colors) => ({ ...colors, [name]: color }));
        } else {
            savedColors.update((colors) => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const { [name]: _, ...rest } = colors;
                return rest;
            });
        }
        colorVersion.update((v) => v + 1);
    };

    // Clear the saved layer, previews and counters, and drop saves still in flight
    const reset = () => {
        generation += 1;
        lastBegun = {};
        lastApplied = {};
        savedColors.set({});
        previews.set({});
        colorVersion.update((v) => v + 1);
    };

    const getGeneration = (): number => generation;

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
        getSavedColor,
        hasSavedColor,
        replaceSavedColors,
        beginSave,
        setSavedColor,
        reset,
        getGeneration
    };
};
