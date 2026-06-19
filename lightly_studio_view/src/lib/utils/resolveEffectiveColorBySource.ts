/**
 * Resolves whether annotations should be colored by source.
 *
 * When enforceColoringByClass is true, class colors always win regardless of how many
 * sources are visible.
 */
export const resolveEffectiveColorBySource = ({
    multipleSourcesVisible,
    enforceColoringByClass
}: {
    multipleSourcesVisible: boolean;
    enforceColoringByClass: boolean;
}): boolean => {
    if (enforceColoringByClass) return false;
    return multipleSourcesVisible;
};
