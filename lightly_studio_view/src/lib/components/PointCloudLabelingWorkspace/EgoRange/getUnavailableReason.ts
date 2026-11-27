import type { Vector3 } from '../domain';

interface UnavailableReasonInput {
    enabled: boolean;
    egoFrame: string | null;
    referenceFrameId: string;
    isShowingSensorFrames: boolean;
    /** Ego position; `null` if the backend cannot resolve it, `undefined` while it loads. */
    position: Vector3 | null | undefined;
}

/** Explains why the ego range cannot be shown, or returns null if nothing blocks it. */
export function getUnavailableReason({
    enabled,
    egoFrame,
    referenceFrameId,
    isShowingSensorFrames,
    position
}: UnavailableReasonInput): string | null {
    if (!enabled) return null;
    if (!egoFrame) return 'Pick the ego frame in the scene settings.';
    // Points in their sensor frames do not share the frame of the ego position.
    if (isShowingSensorFrames) {
        return 'Ego range unavailable: point clouds are shown in their sensor frames.';
    }
    if (position === null) return `Ego position unavailable in frame ${referenceFrameId}.`;
    return null;
}
