import { createCustomColorStore } from '$lib/hooks/createCustomColorStore';

export type { CustomColor } from '$lib/hooks/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

export const useCustomLabelColors = () => ({
    ...store,
    customLabelColorsStore: store.customColorsStore
});
