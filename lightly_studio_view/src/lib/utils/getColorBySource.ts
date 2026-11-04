import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors/useCustomSourceColors';
import { hexToRgb } from './colorConvert';
import { getDefaultColor } from './getColorByLabel';
import { getColorPair } from './getColorPair';

export const getColorBySource = (sourceName: string, alpha: number = 1) => {
    alpha = Math.max(0, Math.min(alpha, 1));

    const { getCustomColor } = useCustomSourceColors();
    const customColor = getCustomColor(sourceName);
    if (customColor) {
        // Apply the requested alpha, but respect the custom alpha.
        return getColorPair(hexToRgb(customColor.color), customColor.alpha * alpha);
    }

    return getDefaultColor(sourceName, alpha);
};
