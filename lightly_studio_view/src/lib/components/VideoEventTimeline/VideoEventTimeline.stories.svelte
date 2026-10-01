<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoEventTimeline from './VideoEventTimeline.svelte';
    import { toVideoEvents } from '$lib/utils';

    const { Story } = defineMeta({
        title: 'Components/VideoEventTimeline',
        component: VideoEventTimeline,
        tags: ['autodocs']
    });

    /** Build events without needing real annotation payloads. */
    function makeEvents(spans: [string, number, number][]) {
        return toVideoEvents(
            spans.map(([label, start, end], index) => ({
                sample_id: `evt-${index}`,
                parent_sample_id: 'video-1',
                annotation_collection_id: 'coll-1',
                annotation_type: 'classification' as const,
                annotation_label: { annotation_label_name: label },
                created_at: new Date(),
                temporal_span_details: { start_time_s: start, end_time_s: end }
            }))
        );
    }

    const DURATION_S = 20;

    const defaultEvents = makeEvents([
        ['Long Jump', 2, 9],
        ['Run-up', 0, 3],
        ['Landing', 8.5, 11],
        ['Celebration', 12, 16]
    ]);

    const overlappingEvents = makeEvents([
        ['A', 0, 10],
        ['B', 1, 4],
        ['C', 2, 6],
        ['D', 5, 9]
    ]);

    const singleEvent = makeEvents([['Sprint', 3, 14]]);
    let playheadTimeS = $state(6);
</script>

<!--
    Click any event bar to seek: the playhead jumps to the bar's start time.
-->
<Story name="Playground" asChild>
    <div class="w-[600px]">
        <VideoEventTimeline
            events={defaultEvents}
            durationS={DURATION_S}
            currentTimeS={playheadTimeS}
            onSeek={(t) => (playheadTimeS = t)}
        />
    </div>
</Story>

<Story name="Default" args={{ events: defaultEvents, durationS: DURATION_S, currentTimeS: 6 }} />

<Story name="Empty" args={{ events: [], durationS: DURATION_S }} />

<Story
    name="OverlappingLanes"
    args={{
        events: overlappingEvents,
        durationS: 12,
        currentTimeS: 3
    }}
/>

<Story
    name="SingleEvent"
    args={{
        events: singleEvent,
        durationS: DURATION_S,
        currentTimeS: 5
    }}
/>
<Story
    name="NoHeader"
    args={{
        events: defaultEvents,
        durationS: DURATION_S,
        currentTimeS: 6,
        showHeader: false
    }}
/>

<Story
    name="CustomTitle"
    args={{
        events: defaultEvents,
        durationS: DURATION_S,
        currentTimeS: 6,
        title: 'Activity annotations'
    }}
/>
