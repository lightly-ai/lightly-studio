import { createCustomColorStore } from './createCustomColorStore/createCustomColorStore';

export type { CustomColor } from './createCustomColorStore/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

export const useCustomLabelColors = () => ({
    ...store,
    customLabelColorsStore: store.customColorsStore
});
