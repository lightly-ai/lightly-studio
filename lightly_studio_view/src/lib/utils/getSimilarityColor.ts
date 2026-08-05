/**
 * Converts a similarity score to an HSL(A) color string.
 *
 * Maps scores from 0 (red) to 1 (green) using a linear hue interpolation.
 * Scores are clamped to the [0, 1] range.
 *
 * @param score - Similarity score between 0 and 1
 * @param alpha - Optional opacity in [0, 1]; when set, returns `hsla(...)`
 * @returns HSL or HSLA color string (e.g., "hsl(60, 80%, 50%)")
 */
export function getSimilarityColor(score: number, alpha?: number): string {
    const clampedScore = Math.max(0, Math.min(1, score));
    const hue = clampedScore * 120;
    if (alpha === undefined) {
        return `hsl(${hue}, 80%, 50%)`;
    }
    const clampedAlpha = Math.max(0, Math.min(1, alpha));
    return `hsla(${hue}, 80%, 50%, ${clampedAlpha})`;
}
