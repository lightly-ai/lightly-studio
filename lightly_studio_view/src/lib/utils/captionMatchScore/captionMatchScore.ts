import type { CaptionView } from '$lib/api/lightly_studio_local';
import { CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';
import {
    getCaptionRepeatGroupId,
    getRepeatGroupColors
} from '$lib/utils/captionRepetition/captionRepetition';
import { getSimilarityColor } from '$lib/utils/getSimilarityColor';
import type { VideoEvent } from '$lib/utils/videoEvents/videoEvents';

/** Scores below this are treated as a poor caption–segment match. */
export const MATCH_SCORE_LOW_MAX = 0.35;
/** Scores at or above this are treated as a strong caption–segment match. */
export const MATCH_SCORE_HIGH_MIN = 0.55;

export type MatchScoreBand = 'low' | 'medium' | 'high';
export type MatchScoreFilter = 'all' | MatchScoreBand;

const EVENT_FILL_ALPHA = 0.7;
const MAX_TIMELINE_LABEL_LENGTH = 36;

export interface ToCaptionVideoEventsOptions {
    /** When true, color timed captions by `repeated_caption_group_id` instead of match score. */
    colorByRepeatGroup?: boolean;
}

/**
 * Reads `caption_segment_match_score` from caption metadata, if present.
 */
export function getCaptionMatchScore(
    metadataDict: CaptionView['metadata_dict']
): number | null {
    const value = metadataDict?.data?.[CAPTION_SEGMENT_MATCH_SCORE_KEY];
    return typeof value === 'number' ? value : null;
}

/**
 * Maps a match score into Low / Medium / High triage bands.
 */
export function getMatchScoreBand(score: number): MatchScoreBand {
    if (score < MATCH_SCORE_LOW_MAX) return 'low';
    if (score < MATCH_SCORE_HIGH_MIN) return 'medium';
    return 'high';
}

/**
 * Timeline fill + contrast colors for a match score (red → green).
 */
export function getMatchScoreTimelineColors(score: number): {
    color: string;
    contrastColor: string;
} {
    const clamped = Math.max(0, Math.min(1, score));
    return {
        color: getSimilarityColor(clamped, EVENT_FILL_ALPHA),
        contrastColor: clamped > 0.45 ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)'
    };
}

/**
 * Captions whose match score falls in `filter`, preserving input order.
 * `'all'` keeps every caption (including those without a score).
 */
export function filterCaptionsByMatchBand(
    captions: CaptionView[],
    filter: MatchScoreFilter
): CaptionView[] {
    if (filter === 'all') return captions;

    return captions.filter((caption) => {
        const score = getCaptionMatchScore(caption.metadata_dict);
        return score !== null && getMatchScoreBand(score) === filter;
    });
}

/**
 * Sorts by match score ascending (worst first). Captions without a score go last;
 * ties keep start-time then original order.
 */
export function sortCaptionsByMatchScore(captions: CaptionView[]): CaptionView[] {
    return captions
        .map((caption, index) => ({ caption, index }))
        .sort((a, b) => {
            const scoreA = getCaptionMatchScore(a.caption.metadata_dict);
            const scoreB = getCaptionMatchScore(b.caption.metadata_dict);

            if (scoreA === null && scoreB === null) {
                return compareByStartTime(a.caption, b.caption) || a.index - b.index;
            }
            if (scoreA === null) return 1;
            if (scoreB === null) return -1;
            if (scoreA !== scoreB) return scoreA - scoreB;
            return compareByStartTime(a.caption, b.caption) || a.index - b.index;
        })
        .map(({ caption }) => caption);
}

/** Filter by band, then sort worst match scores first. */
export function triageCaptions(
    captions: CaptionView[],
    filter: MatchScoreFilter
): CaptionView[] {
    return sortCaptionsByMatchScore(filterCaptionsByMatchBand(captions, filter));
}

/**
 * Caption whose temporal span contains `currentTimeS`, preferring the shortest
 * span when several overlap.
 */
export function findActiveCaptionAtTime(
    captions: CaptionView[],
    currentTimeS: number
): CaptionView | null {
    let best: CaptionView | null = null;
    let bestDuration = Number.POSITIVE_INFINITY;

    for (const caption of captions) {
        const span = caption.temporal_span_details;
        if (!span) continue;
        if (currentTimeS < span.start_time_s || currentTimeS >= span.end_time_s) continue;

        const duration = span.end_time_s - span.start_time_s;
        if (duration < bestDuration) {
            best = caption;
            bestDuration = duration;
        }
    }

    return best;
}

/**
 * Maps timed captions to {@link VideoEvent}s for the timeline.
 * Default colors use match score; pass ``colorByRepeatGroup`` to color by
 * repetition group instead (ungrouped captions stay gray / match-colored).
 */
export function toCaptionVideoEvents(
    captions: CaptionView[] = [],
    options: ToCaptionVideoEventsOptions = {}
): VideoEvent[] {
    const colorByRepeatGroup = options.colorByRepeatGroup === true;

    return captions
        .filter((caption) => caption.temporal_span_details != null)
        .map((caption) => {
            const span = caption.temporal_span_details!;
            const score = getCaptionMatchScore(caption.metadata_dict);
            const groupId = getCaptionRepeatGroupId(caption.metadata_dict);
            const colors = resolveTimelineColors({
                colorByRepeatGroup,
                groupId,
                score
            });
            const text = caption.text?.trim() || 'Caption';
            const prefixes: string[] = [];
            if (colorByRepeatGroup && groupId !== null) {
                prefixes.push(`G${groupId}`);
            }
            if (score !== null && !colorByRepeatGroup) {
                prefixes.push(score.toFixed(2));
            }
            const prefix = prefixes.length > 0 ? `${prefixes.join(' · ')} · ` : '';
            const label = truncateLabel(`${prefix}${text}`);

            return {
                id: caption.sample_id,
                annotationCollectionId: '',
                label,
                startTimeS: span.start_time_s,
                endTimeS: span.end_time_s,
                color: colors.color,
                contrastColor: colors.contrastColor
            } satisfies VideoEvent;
        })
        .sort((a, b) => a.startTimeS - b.startTimeS);
}

function resolveTimelineColors({
    colorByRepeatGroup,
    groupId,
    score
}: {
    colorByRepeatGroup: boolean;
    groupId: number | null;
    score: number | null;
}): { color: string; contrastColor: string } {
    if (colorByRepeatGroup && groupId !== null) {
        return getRepeatGroupColors(groupId);
    }
    if (score !== null) {
        return getMatchScoreTimelineColors(score);
    }
    return {
        color: 'rgba(120, 120, 120, 0.7)',
        contrastColor: 'rgba(255, 255, 255, 0.95)'
    };
}

function compareByStartTime(a: CaptionView, b: CaptionView): number {
    const startA = a.temporal_span_details?.start_time_s ?? Number.POSITIVE_INFINITY;
    const startB = b.temporal_span_details?.start_time_s ?? Number.POSITIVE_INFINITY;
    return startA - startB;
}

function truncateLabel(label: string): string {
    if (label.length <= MAX_TIMELINE_LABEL_LENGTH) return label;
    return `${label.slice(0, MAX_TIMELINE_LABEL_LENGTH - 1)}…`;
}
