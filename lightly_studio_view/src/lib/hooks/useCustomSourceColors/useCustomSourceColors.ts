import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';

// Shares the class color store until source colors get their own store.
export const useCustomSourceColors = () => {
    const store = useCustomLabelColors();
    return { ...store, customSourceColorsStore: store.customColorsStore };
};
