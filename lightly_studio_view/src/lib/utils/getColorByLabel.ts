import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';

export const getColorByLabel = (label: string, alpha: number = 1) => {
    // Clamp alpha between 0 and 1
    alpha = Math.max(0, Math.min(alpha, 1));

    // Check if there's a custom color for this label
    const { getCustomColor, hasCustomColor } = useCustomLabelColors();

    if (hasCustomColor(label)) {
        const customColor = getCustomColor(label);
        if (customColor) {
            // Apply the requested alpha to the custom color
            const hexToRgba = (hex: string, alpha: number) => {
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                return {
                    color: `rgba(${r}, ${g}, ${b}, ${alpha})`,
                    contrastColor: `rgba(${255 - r}, ${255 - g}, ${255 - b}, ${alpha})`
                };
            };

            // Apply the requested alpha, but respect the custom alpha
            return hexToRgba(customColor.color, customColor.alpha * alpha);
        }
    }

    // Define a set of colors for common cases
    const colorPalette = [
        'rgba(255, 0, 0, alpha)', // Red
        'rgba(0, 255, 0, alpha)', // Green
        'rgba(0, 0, 255, alpha)', // Blue
        'rgba(255, 255, 0, alpha)', // Yellow
        'rgba(255, 0, 255, alpha)', // Magenta
        'rgba(0, 255, 255, alpha)', // Cyan
        'rgba(128, 0, 0, alpha)', // Maroon
        'rgba(0, 128, 0, alpha)', // Dark Green
        'rgba(0, 0, 128, alpha)', // Navy
        'rgba(128, 128, 0, alpha)', // Olive
        'rgba(128, 0, 128, alpha)', // Purple
        'rgba(0, 128, 128, alpha)', // Teal
        'rgba(192, 192, 192, alpha)', // Silver
        'rgba(128, 128, 128, alpha)', // Gray
        'rgba(255, 165, 0, alpha)', // Orange
        'rgba(255, 20, 147, alpha)', // Deep Pink
        'rgba(75, 0, 130, alpha)', // Indigo
        'rgba(255, 105, 180, alpha)', // Hot Pink
        'rgba(0, 255, 127, alpha)', // Spring Green
        'rgba(255, 215, 0, alpha)', // Gold
        'rgba(255, 69, 0, alpha)' // Red-Orange
    ];

    // Convert input to a number if it's a string
    let index: number;
    const maxColorPaletteIndex = colorPalette.length - 1;

    // Simple hash function to convert string to number
    index = Array.from(label).reduce((hash, char) => (hash << 5) - hash + char.charCodeAt(0), 0);
    // Make sure it's positive and map it to a reasonable range
    index = (Math.abs(index) % maxColorPaletteIndex) + 1;

    if (index >= 1 && index <= maxColorPaletteIndex) {
        return {
            color: colorPalette[index - 1].replace('alpha', alpha.toString()),
            contrastColor: `rgba(${255 - Math.round(parseInt(colorPalette[index - 1].split(',')[0].split('(')[1]) * (alpha / 255))}, ${255 - Math.round(parseInt(colorPalette[index - 1].split(',')[1]))}, ${255 - Math.round(parseInt(colorPalette[index - 1].split(',')[2]))}, ${alpha})`
        };
    }

    // Existing color generation logic for indices greater than 20
    const r = (index * 30 + 20) % 256; // Red component with offset
    const g = (index * 60 + 100) % 256; // Green component with offset
    const b = (index * 90 + 150) % 256; // Blue component with offset

    // Adjust to ensure saturation
    const maxColor = Math.max(r, g, b);
    const minColor = Math.min(r, g, b);
    const delta = maxColor - minColor;

    if (delta === 0) {
        // If all colors are equal, return a bright color
        return {
            color: `rgba(255, 255, 255, ${alpha})`, // White as a fallback
            contrastColor: `rgba(0, 0, 0, ${alpha})` // Black as contrast
        };
    }

    // Scale the colors to increase saturation
    const scale = 255 / maxColor;
    const generatedColor = `rgba(${Math.round(r * scale)}, ${Math.round(g * scale)}, ${Math.round(b * scale)}, ${alpha})`;

    // Calculate contrast color (inverting the RGB values)
    const contrastColor = `rgba(${255 - Math.round(r * scale)}, ${255 - Math.round(g * scale)}, ${255 - Math.round(b * scale)}, ${alpha})`;

    return { color: generatedColor, contrastColor: contrastColor };
};
