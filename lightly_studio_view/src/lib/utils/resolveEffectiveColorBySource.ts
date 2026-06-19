/**
 * Resolves the effective annotation coloring mode.
 *
 * When enforceColoringByClass is enabled it acts as a global override: the
 * effective result is always false (color by class) regardless of how many
 * annotation sources are visible.  When disabled, the caller-supplied
 * sourceColoringActive value is returned unchanged.
 */
export function resolveEffectiveColorBySource(
    sourceColoringActive: boolean,
    enforceColoringByClass: boolean
): boolean {
    if (enforceColoringByClass) return false;
    return sourceColoringActive;
}
