// A type alias, not an interface, so that it matches the JSON type of `useLocalStorage`.
export type EgoRangeSettings = {
    enabled: boolean;
    /** Radius of the range, in meters. */
    radius: number;
    /** Ego frame picked for each dataset ID, because frame names differ between datasets. */
    egoFrameByDataset: Record<string, string>;
};

export const MIN_EGO_RANGE_RADIUS = 1;
export const MAX_EGO_RANGE_RADIUS = 500;

export const DEFAULT_EGO_RANGE_SETTINGS: EgoRangeSettings = {
    enabled: false,
    radius: 40,
    egoFrameByDataset: {}
};

// Common names of the frame attached to the ego, in order of preference.
const DEFAULT_EGO_FRAMES = ['CABIN', 'base_link'];

export function clampEgoRangeRadius(radius: number): number {
    return Math.min(MAX_EGO_RANGE_RADIUS, Math.max(MIN_EGO_RANGE_RADIUS, radius));
}

/** Returns valid settings from a stored value of unknown shape. */
export function sanitizeEgoRangeSettings(value: unknown): EgoRangeSettings {
    const candidate = isRecord(value) ? value : {};
    const isValidRadius = typeof candidate.radius === 'number' && Number.isFinite(candidate.radius);
    return {
        enabled:
            typeof candidate.enabled === 'boolean'
                ? candidate.enabled
                : DEFAULT_EGO_RANGE_SETTINGS.enabled,
        radius: isValidRadius
            ? clampEgoRangeRadius(candidate.radius as number)
            : DEFAULT_EGO_RANGE_SETTINGS.radius,
        egoFrameByDataset: getStringEntries(candidate.egoFrameByDataset)
    };
}

/** Returns the stored ego frame if the sequence has it, else a common default, else null. */
export function resolveEgoFrame(
    storedFrame: string | undefined,
    referenceFrames: readonly string[]
): string | null {
    if (storedFrame && referenceFrames.includes(storedFrame)) return storedFrame;
    return DEFAULT_EGO_FRAMES.find((frame) => referenceFrames.includes(frame)) ?? null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}

function getStringEntries(value: unknown): Record<string, string> {
    if (!isRecord(value)) return {};
    return Object.fromEntries(
        Object.entries(value).filter((entry): entry is [string, string] => {
            return typeof entry[1] === 'string';
        })
    );
}
