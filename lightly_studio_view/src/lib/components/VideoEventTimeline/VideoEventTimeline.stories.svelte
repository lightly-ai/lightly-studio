<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import VideoEventTimeline from './VideoEventTimeline.svelte';
    import { toVideoEvents } from '$lib/utils';

    const { Story } = defineMeta({
        title: 'Components/VideoEventTimeline',
        component: VideoEventTimeline,
        tags: ['autodocs']
    });

    /** Build events without needing real annotation payloads. */
    function makeEvents(spans) {
        return toVideoEvents(
            spans.map(([label, start, end], index) => ({
                sample_id: `evt-${index}`,
                parent_sample_id: 'video-1',
                annotation_collection_id: 'coll-1',
                annotation_type: 'classification',
                annotation_label: { annotation_label_name: label },
                created_at: new Date(),
                temporal_span_details: { start_time_s: start, end_time_s: end }
            }))
        );
    }

    const events = makeEvents([
        ['Long Jump', 2, 9],
        ['Run-up', 0, 3],
        ['Landing', 8.5, 11],
        ['Celebration', 12, 16]
    ]);
</script>

<Story name="Default" args={{ events, durationS: 20, currentTimeS: 6 }} />

<Story name="Empty" args={{ events: [], durationS: 20 }} />

<Story
    name="OverlappingLanes"
    args={{
        events: makeEvents([
            ['A', 0, 10],
            ['B', 1, 4],
            ['C', 2, 6],
            ['D', 5, 9]
        ]),
        durationS: 12,
        currentTimeS: 3
    }}
/>
