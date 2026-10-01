import { describe, it, expect } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { toVideoEvents, assignEventLanes, type VideoEvent } from './videoEvents';

function makeAnnotation(overrides: Partial<AnnotationView>): AnnotationView {
    return {
        sample_id: 'a1',
        parent_sample_id: 'video-1',
        annotation_collection_id: 'coll-1',
        annotation_type: 'classification',
        annotation_label: { annotation_label_name: 'Jump' },
        created_at: new Date(),
        temporal_span_details: { start_time_s: 1, end_time_s: 4 },
        ...overrides
    } as AnnotationView;
}

function makeEvent(overrides: Partial<VideoEvent>): VideoEvent {
    return {
        id: 'e',
        annotationCollectionId: 'coll-1',
        label: 'x',
        startTimeS: 0,
        endTimeS: 1,
        color: 'rgba(0,0,0,1)',
        contrastColor: 'rgba(255,255,255,1)',
        ...overrides
    };
}

describe('toVideoEvents', () => {
    it('keeps only classification annotations with a temporal span', () => {
        const events = toVideoEvents([
            makeAnnotation({ sample_id: 'with-span' }),
            makeAnnotation({ sample_id: 'no-span', temporal_span_details: null }),
            makeAnnotation({ sample_id: 'not-classification', annotation_type: 'object_detection' })
        ]);

        expect(events.map((event) => event.id)).toEqual(['with-span']);
    });

    it('maps span times and label onto the event', () => {
        const [event] = toVideoEvents([
            makeAnnotation({
                sample_id: 'e1',
                annotation_label: { annotation_label_name: 'Run' },
                temporal_span_details: { start_time_s: 2.5, end_time_s: 7 }
            })
        ]);

        expect(event).toMatchObject({ id: 'e1', label: 'Run', startTimeS: 2.5, endTimeS: 7 });
        expect(event.color).toBeTruthy();
        expect(event.contrastColor).toBeTruthy();
    });

    it('sorts events by start time', () => {
        const events = toVideoEvents([
            makeAnnotation({
                sample_id: 'late',
                temporal_span_details: { start_time_s: 9, end_time_s: 10 }
            }),
            makeAnnotation({
                sample_id: 'early',
                temporal_span_details: { start_time_s: 1, end_time_s: 2 }
            })
        ]);

        expect(events.map((event) => event.id)).toEqual(['early', 'late']);
    });

    it('returns an empty array when annotations are undefined', () => {
        expect(toVideoEvents()).toEqual([]);
    });
});

describe('assignEventLanes', () => {
    it('places non-overlapping events on the same lane', () => {
        const { events, laneCount } = assignEventLanes([
            makeEvent({ id: 'a', startTimeS: 0, endTimeS: 2 }),
            makeEvent({ id: 'b', startTimeS: 2, endTimeS: 4 })
        ]);

        expect(laneCount).toBe(1);
        expect(events.every((event) => event.lane === 0)).toBe(true);
    });

    it('stacks overlapping events onto separate lanes', () => {
        const { events, laneCount } = assignEventLanes([
            makeEvent({ id: 'a', startTimeS: 0, endTimeS: 5 }),
            makeEvent({ id: 'b', startTimeS: 1, endTimeS: 3 }),
            makeEvent({ id: 'c', startTimeS: 2, endTimeS: 4 })
        ]);

        expect(laneCount).toBe(3);
        expect(events.find((event) => event.id === 'a')?.lane).toBe(0);
        expect(events.find((event) => event.id === 'b')?.lane).toBe(1);
        expect(events.find((event) => event.id === 'c')?.lane).toBe(2);
    });

    it('reuses a freed lane once an earlier event has ended', () => {
        const { laneCount } = assignEventLanes([
            makeEvent({ id: 'a', startTimeS: 0, endTimeS: 2 }),
            makeEvent({ id: 'b', startTimeS: 1, endTimeS: 3 }),
            makeEvent({ id: 'c', startTimeS: 2, endTimeS: 4 })
        ]);

        // 'c' can reuse 'a's lane, so only two lanes are needed.
        expect(laneCount).toBe(2);
    });
});
