/**
 * Resolves whether annotations should be colored by source.
 *
 * When colorMode is set, it decides alone. Otherwise, when enforceColoringByClass is true, class
 * colors always win regardless of how many sources are visible.
 */
export const resolveEffectiveColorBySource = ({
    multipleSourcesVisible,
    enforceColoringByClass,
    colorMode
}: {
    multipleSourcesVisible: boolean;
    enforceColoringByClass: boolean;
    colorMode?: 'class' | 'source';
}): boolean => {
    if (colorMode) return colorMode === 'source';
    if (enforceColoringByClass) return false;
    return multipleSourcesVisible;
};
