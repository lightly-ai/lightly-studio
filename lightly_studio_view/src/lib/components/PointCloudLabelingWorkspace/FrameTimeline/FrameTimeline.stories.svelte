<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
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
