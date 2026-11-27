<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import FrameTimeline from './FrameTimeline.svelte';

    // Placeholder ruler with no timestamps yet, mirroring the pre-frame-loading state.
    const placeholderTicks: TickView[] = Array.from({ length: 24 }, (_, index) => ({
        seq_number: index,
        timestamp_ns: null
    }));

    // 24 ticks at 10 Hz, anchored at an arbitrary log time; hover a mark to read its timestamp.
    const ticks: TickView[] = Array.from({ length: 24 }, (_, index) => ({
        seq_number: index,
        timestamp_ns: 1_700_000_000_000_000_000 + index * 100_000_000
    }));

    const track = (number: number, label: string, seqNumbers: number[]): SequenceTrackView => ({
        object_track_id: `track-${number}`,
        object_track_number: number,
        annotation_source_id: 'source',
        annotation_source_name: 'ground_truth',
        annotation_label_name: label,
        annotations: seqNumbers.map((seq_number) => ({
            seq_number,
            annotation_id: `annotation-${number}-${seq_number}`,
            annotation_source_id: 'source',
            frame_id: 'odom',
            interpolated: false
        }))
    });
    const range = (start: number, end: number) =>
        Array.from({ length: end - start + 1 }, (_, index) => start + index);

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/FrameTimeline',
        component: FrameTimeline,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' },
        args: {
            ticks: placeholderTicks,
            currentTick: 0,
            isPlaying: false,
            playbackIntervalMs: 100,
            bufferEntireSequence: false,
            onBufferEntireSequenceChange: fn(),
            bufferedRanges: [{ startIndex: 0, endIndex: 8 }],
            onPreviousFrame: fn(),
            onNextFrame: fn(),
            onPlayToggle: fn(),
            onPlaybackIntervalChange: fn(),
            onSelectTick: fn()
        }
    });
</script>

{#snippet frame(args)}
    <div class="h-24 w-full">
        <FrameTimeline {...args} />
    </div>
{/snippet}

{#snippet tall(args)}
    <div class="h-96 w-full">
        <FrameTimeline {...args} />
    </div>
{/snippet}

<Story
    name="Timestamped ruler"
    args={{ ticks, currentTick: 8 }}
    template={frame}
    parameters={{
        docs: {
            description: {
                story: 'Ticks carry an anchor timestamp; each ruler mark shows its time (relative to the first tick) on hover. The active tick is highlighted and reflected in the frame counter.'
            }
        }
    }}
/>

<Story
    name="Playing"
    args={{ ticks, currentTick: 8, isPlaying: true }}
    template={frame}
    parameters={{
        docs: {
            description: {
                story: 'While playing, the transport shows a pause control instead of play.'
            }
        }
    }}
/>

<!-- Zoom in with the buttons or Ctrl/Cmd + wheel to inspect individual frames. -->
<Story
    name="Long sequence (zoomable)"
    args={{
        ticks: Array.from({ length: 600 }, (_, index) => ({
            seq_number: index,
            timestamp_ns: 1_700_000_000_000_000_000 + index * 100_000_000
        })),
        currentTick: 300,
        bufferedRanges: [{ startIndex: 0, endIndex: 400 }]
    }}
    template={frame}
/>

<Story
    name="Object tracks and frame tag tracks"
    args={{
        ticks,
        currentTick: 8,
        tracks: [track(1, 'car', range(0, 16)), track(2, 'pedestrian', range(4, 12))],
        showObjectTracks: true,
        onHideObjectTracks: fn(),
        showFrameTags: true,
        onHideFrameTags: fn(),
        frameTags: [
            { tag_id: 'tag-1', name: 'occluded', seq_numbers: [3, 4, 5, 14] },
            { tag_id: 'tag-2', name: 'night', seq_numbers: range(0, 23) }
        ]
    }}
    template={tall}
    parameters={{
        docs: {
            description: {
                story: 'Object tracks and frame tag tracks are separate panels; each has its own close button.'
            }
        }
    }}
/>
