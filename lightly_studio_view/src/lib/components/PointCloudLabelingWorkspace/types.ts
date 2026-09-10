/**
 * UI-level types for the point-cloud labeling workspace shell.
 *
 * Kept separate from `./domain`, which models point-cloud data rather than chrome: the shell
 * takes its navigation context as plain values so it stays free of collection/transport concerns.
 */

/** One step of the source breadcrumb, e.g. dataset -> collection -> sample. */
export interface WorkspaceCrumb {
    /** Text shown for this step. */
    readonly label: string;
    /** Link target. The final (current) crumb has none. */
    readonly href?: string;
}

/**
 * Frame navigation for the timeline.
 *
 * Frames are discovered as navigation reaches them rather than listed up front, so
 * `frameCount` is what is known so far and `hasMore` says whether the channel continues
 * past it. The timeline reports where the viewer is and asks to move; it does not know how
 * a frame is found or read.
 */
export interface FrameNavigation {
    /** Zero-based position among the frames discovered so far. */
    readonly position: number;
    /** How many frames are known. Grows as navigation moves forward. */
    readonly frameCount: number;
    /** Whether the channel holds frames beyond the ones known. */
    readonly hasMore: boolean;
    /** Whether a frame is being read right now. */
    readonly isLoading: boolean;
    previous(): void;
    next(): void;
}
