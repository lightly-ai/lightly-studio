import { createCustomColorStore } from '$lib/hooks/createCustomColorStore/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

export const useCustomSourceColors = () => ({
    ...store,
    customSourceColorsStore: store.customColorsStore
});
