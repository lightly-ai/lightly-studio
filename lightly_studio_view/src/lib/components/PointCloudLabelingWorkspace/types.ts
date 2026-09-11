/**
 * UI-level types for the point-cloud labeling workspace shell.
 *
 * Kept separate from `./domain`, which models point-cloud data rather than chrome: the shell
 * takes its navigation context as plain values so it stays free of collection/transport concerns.
 * Timeline tracks and keyframes are likewise expressed by frame *position* (an index into the
 * frames `FrameNavigation` has discovered so far) rather than by domain frame ID, so this file
 * never needs to know how a track or annotation maps to a frame; that mapping is the concern of
 * whoever adapts `AnnotationTrack`/`CuboidAnnotation` data into these shapes.
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
    /**
     * Jumps directly to an already-discovered frame, for scrubbing.
     *
     * Optional so existing navigation sources (and their tests/mocks) keep working; the
     * timeline disables scrubbing when it is absent. Positions beyond what is known are not
     * reachable this way — advance with `next()` first to discover them.
     */
    seek?(position: number): void;
}

/**
 * An authored or interpolated anchor for one track at a known frame position.
 *
 * Positions outside `[0, frameCount)` of the active `FrameNavigation` are not renderable and
 * should be omitted by whoever builds this list.
 */
export interface TimelineKeyframe {
    /** Stable keyframe identity, e.g. `AnnotationKeyframe.id`. */
    readonly id: string;
    /** Frame position (index) this keyframe anchors. */
    readonly framePosition: number;
}

/**
 * One object track as the timeline draws it: a label, its authored keyframes, and every frame
 * position where the track has geometry at all (authored or interpolated).
 *
 * `presentFramePositions` need not be contiguous: a position missing from it, between two
 * others that are present, is a gap in an otherwise sparse track. Positions outside it are
 * simply not drawn, distinguishing "no geometry here" from "not authored here".
 */
export interface TimelineTrack {
    /** Stable track identity, e.g. `AnnotationTrack.id`. */
    readonly id: string;
    /** Label shown in the lane gutter, e.g. the assigned annotation class name. */
    readonly label: string;
    /** Lane and keyframe-marker color; defaults to the theme's muted foreground when absent. */
    readonly color?: string;
    /** Ordered authored anchors. */
    readonly keyframes: readonly TimelineKeyframe[];
    /** Every frame position with geometry for this track, authored or interpolated. */
    readonly presentFramePositions: readonly number[];
}
