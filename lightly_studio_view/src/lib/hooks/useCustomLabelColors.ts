import { createCustomColorStore } from '$lib/hooks/createCustomColorStore/createCustomColorStore';

export type { CustomColor } from '$lib/hooks/createCustomColorStore/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

export const useCustomLabelColors = () => ({
    ...store,
    customLabelColorsStore: store.customColorsStore
});
