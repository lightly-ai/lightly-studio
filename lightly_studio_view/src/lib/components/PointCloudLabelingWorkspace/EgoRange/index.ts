export { formatDistance, getFlatDistance, isBeyondRange, type EgoRange } from './egoRange';
export {
    clampEgoRangeRadius,
    DEFAULT_EGO_RANGE_SETTINGS,
    MAX_EGO_RANGE_RADIUS,
    MIN_EGO_RANGE_RADIUS,
    resolveEgoFrame,
    sanitizeEgoRangeSettings,
    type EgoRangeSettings
} from './egoRangeSettings';
export { getUnavailableReason } from './getUnavailableReason';
export { useEgoRange } from './useEgoRange.svelte';
