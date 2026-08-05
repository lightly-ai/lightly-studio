import { describe, expect, it } from 'vitest';
import type { CaptionView } from '$lib/api/lightly_studio_local';
import { CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';
import {
    findActiveCaptionAtTime,
    filterCaptionsByMatchBand,
    getCaptionMatchScore,
    getMatchScoreBand,
    getMatchScoreTimelineColors,
    MATCH_SCORE_HIGH_MIN,
    MATCH_SCORE_LOW_MAX,
    sortCaptionsByMatchScore,
    toCaptionVideoEvents,
    triageCaptions
} from './captionMatchScore';

function makeCaption(overrides: Partial<CaptionView> & { score?: number | null }): CaptionView {
    const { score, metadata_dict, ...rest } = overrides;
    const data =
        score === undefined
            ? (metadata_dict?.data ?? {})
            : score === null
              ? {}
              : { [CAPTION_SEGMENT_MATCH_SCORE_KEY]: score };

    return {
        sample_id: 'cap-1',
        parent_sample_id: 'video-1',
        text: 'A caption',
        temporal_span_details: null,
        metadata_dict: { data },
        ...rest
    } as CaptionView;
}

describe('getCaptionMatchScore', () => {
    it('reads the match score from metadata', () => {
        expect(getCaptionMatchScore(makeCaption({ score: 0.42 }).metadata_dict)).toBe(0.42);
    });

    it('returns null when the key is missing', () => {
        expect(getCaptionMatchScore(makeCaption({ score: null }).metadata_dict)).toBeNull();
        expect(getCaptionMatchScore(null)).toBeNull();
    });
});

describe('getMatchScoreBand', () => {
    it('uses the configured Low / Medium / High thresholds', () => {
        expect(getMatchScoreBand(MATCH_SCORE_LOW_MAX - 0.01)).toBe('low');
        expect(getMatchScoreBand(MATCH_SCORE_LOW_MAX)).toBe('medium');
        expect(getMatchScoreBand(MATCH_SCORE_HIGH_MIN - 0.01)).toBe('medium');
        expect(getMatchScoreBand(MATCH_SCORE_HIGH_MIN)).toBe('high');
    });
});

describe('getMatchScoreTimelineColors', () => {
    it('returns a red-tinted fill for low scores', () => {
        expect(getMatchScoreTimelineColors(0).color).toContain('hsla(0,');
    });

    it('returns a green-tinted fill for high scores', () => {
        expect(getMatchScoreTimelineColors(1).color).toContain('hsla(120,');
    });
});

describe('filterCaptionsByMatchBand', () => {
    const captions = [
        makeCaption({ sample_id: 'low', score: 0.2 }),
        makeCaption({ sample_id: 'med', score: 0.4 }),
        makeCaption({ sample_id: 'high', score: 0.8 }),
        makeCaption({ sample_id: 'none', score: null })
    ];

    it('keeps all captions for the all filter', () => {
        expect(filterCaptionsByMatchBand(captions, 'all').map((c) => c.sample_id)).toEqual([
            'low',
            'med',
            'high',
            'none'
        ]);
    });

    it('keeps only captions in the requested band', () => {
        expect(filterCaptionsByMatchBand(captions, 'low').map((c) => c.sample_id)).toEqual([
            'low'
        ]);
        expect(filterCaptionsByMatchBand(captions, 'medium').map((c) => c.sample_id)).toEqual([
            'med'
        ]);
        expect(filterCaptionsByMatchBand(captions, 'high').map((c) => c.sample_id)).toEqual([
            'high'
        ]);
    });
});

describe('sortCaptionsByMatchScore', () => {
    it('sorts lowest scores first and puts missing scores last', () => {
        const sorted = sortCaptionsByMatchScore([
            makeCaption({ sample_id: 'high', score: 0.9 }),
            makeCaption({ sample_id: 'none', score: null }),
            makeCaption({ sample_id: 'low', score: 0.1 }),
            makeCaption({ sample_id: 'med', score: 0.5 })
        ]);

        expect(sorted.map((c) => c.sample_id)).toEqual(['low', 'med', 'high', 'none']);
    });
});

describe('triageCaptions', () => {
    it('filters then sorts by score', () => {
        const result = triageCaptions(
            [
                makeCaption({ sample_id: 'low-b', score: 0.3 }),
                makeCaption({ sample_id: 'high', score: 0.9 }),
                makeCaption({ sample_id: 'low-a', score: 0.1 })
            ],
            'low'
        );

        expect(result.map((c) => c.sample_id)).toEqual(['low-a', 'low-b']);
    });
});

describe('findActiveCaptionAtTime', () => {
    const captions = [
        makeCaption({
            sample_id: 'a',
            temporal_span_details: { start_time_s: 0, end_time_s: 10 }
        }),
        makeCaption({
            sample_id: 'b',
            temporal_span_details: { start_time_s: 2, end_time_s: 4 }
        })
    ];

    it('returns the shortest spanning caption at the playhead', () => {
        expect(findActiveCaptionAtTime(captions, 3)?.sample_id).toBe('b');
    });

    it('returns null outside all spans', () => {
        expect(findActiveCaptionAtTime(captions, 11)).toBeNull();
    });

    it('treats the end time as exclusive', () => {
        expect(findActiveCaptionAtTime(captions, 4)?.sample_id).toBe('a');
        expect(findActiveCaptionAtTime(captions, 10)).toBeNull();
    });
});

describe('toCaptionVideoEvents', () => {
    it('skips captions without a temporal span', () => {
        const events = toCaptionVideoEvents([
            makeCaption({ sample_id: 'timed', temporal_span_details: { start_time_s: 1, end_time_s: 3 }, score: 0.2 }),
            makeCaption({ sample_id: 'untimed', temporal_span_details: null, score: 0.9 })
        ]);

        expect(events.map((e) => e.id)).toEqual(['timed']);
        expect(events[0].startTimeS).toBe(1);
        expect(events[0].endTimeS).toBe(3);
        expect(events[0].label).toContain('0.20');
        expect(events[0].color).toContain('hsla(');
    });

    it('sorts by start time', () => {
        const events = toCaptionVideoEvents([
            makeCaption({
                sample_id: 'late',
                temporal_span_details: { start_time_s: 5, end_time_s: 6 }
            }),
            makeCaption({
                sample_id: 'early',
                temporal_span_details: { start_time_s: 1, end_time_s: 2 }
            })
        ]);

        expect(events.map((e) => e.id)).toEqual(['early', 'late']);
    });
});
