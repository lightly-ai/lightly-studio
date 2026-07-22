import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { getColorByLabel } from '$lib/utils/getColorByLabel';

/**
 * A time-bounded "event" on a video timeline.
 *
 * Events are derived from classification annotations that carry a temporal
 * span (start/end time in seconds), e.g. ActivityNet-style event annotations
 * imported onto the video sample itself.
 */
export interface VideoEvent {
    /** Unique id of the event (the annotation's sample id). */
    id: string;
    /** Collection the underlying annotation belongs to (needed to persist edits). */
    annotationCollectionId: string;
    /** Human-readable class label. */
    label: string;
    /** Event start time, in seconds. */
    startTimeS: number;
    /** Event end time, in seconds. */
    endTimeS: number;
    /** Fill color derived deterministically from the label. */
    color: string;
    /** Contrast color for text/borders on top of {@link color}. */
    contrastColor: string;
}

/** A {@link VideoEvent} placed on a horizontal lane to avoid visual overlap. */
export interface LaneAssignedEvent extends VideoEvent {
    /** Zero-based lane (row) index the event was placed in. */
    lane: number;
}

const EVENT_FILL_ALPHA = 0.7;

/**
 * Extracts imported events from a sample's annotations.
 *
 * Keeps only classification annotations that carry a temporal span and maps
 * them into {@link VideoEvent}s sorted by start time.
 */
export function toVideoEvents(annotations: AnnotationView[] = []): VideoEvent[] {
    return annotations
        .filter(
            (annotation) =>
                annotation.annotation_type === AnnotationType.CLASSIFICATION &&
                annotation.temporal_span_details != null
        )
        .map((annotation) => {
            const span = annotation.temporal_span_details!;
            const label = annotation.annotation_label.annotation_label_name;
            const { color, contrastColor } = getColorByLabel(label, EVENT_FILL_ALPHA);
            return {
                id: annotation.sample_id,
                annotationCollectionId: annotation.annotation_collection_id,
                label,
                startTimeS: span.start_time_s,
                endTimeS: span.end_time_s,
                color,
                contrastColor
            } satisfies VideoEvent;
        })
        .sort((a, b) => a.startTimeS - b.startTimeS);
}

/**
 * Greedily assigns each event to the first lane whose previous event has
 * already ended, so overlapping events stack into separate rows instead of
 * hiding one another.
 *
 * @returns The events annotated with a `lane` index and the total lane count.
 */
export function assignEventLanes(events: VideoEvent[]): {
    events: LaneAssignedEvent[];
    laneCount: number;
} {
    const sorted = [...events].sort((a, b) => a.startTimeS - b.startTimeS);
    const laneEndTimes: number[] = [];

    const placed = sorted.map((event) => {
        let lane = laneEndTimes.findIndex((endTime) => endTime <= event.startTimeS);
        if (lane === -1) {
            lane = laneEndTimes.length;
        }
        laneEndTimes[lane] = event.endTimeS;
        return { ...event, lane } satisfies LaneAssignedEvent;
    });

    return { events: placed, laneCount: laneEndTimes.length };
}
